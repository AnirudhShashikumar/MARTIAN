"""Local HTTP and transactional persistence for College Resource Allocation."""

from contextlib import closing
from datetime import date
import hashlib
import json
import sqlite3
from threading import Lock

from fastapi import HTTPException, Request, Response

from prototype import agent, resource_agent, resources


class ReadbackError(resources.ResourceError):
    """The proposed update could not be verified and was rolled back."""


def data_for(state):
    return state["resources"] if "resources" in state else resources.fixture(state["equipment"])


def save(db, state, data):
    state["resources"] = data
    db.execute("UPDATE demo SET state = ? WHERE singleton = 1", (json.dumps(state),))


def read(store):
    with closing(store.connection()) as db:
        state = store.read(db)
        return state["id"], data_for(state)


def apply_command(store, command):
    with closing(store.connection()) as db, db:
        db.execute("BEGIN IMMEDIATE")
        state = store.read(db)
        resources.require(state["id"] == command.run_id, "The demo was reset. Refresh and start a new request.")
        data = data_for(state)
        fingerprint = hashlib.sha256(command.model_dump_json().encode()).hexdigest()
        previous = data["receipts"].get(command.key)
        if previous:
            resources.require(previous["fingerprint"] == fingerprint, "That retry key already belongs to another command.")
            return public_result(state["id"], data, previous["receipt"])

        data["revision"] += 1
        subject = resources.apply(data, command)
        receipt = {"id": command.key, "subject": subject, "revision": data["revision"], "action": command.action}
        data["receipts"][command.key] = {"fingerprint": fingerprint, "receipt": receipt}
        request = data["requests"].get(subject)
        message = f"Request status: {request['status'].replace('_', ' ')}." if request else "Ledger state confirmed."
        resources.record(data, command.tab, "Verify", "SQLite readback verified", message,
                         subject if request else None, getattr(command, "role", None))
        save(db, state, data)

        persisted = store.read(db)["resources"]
        try:
            resources.require(persisted == data, "SQLite readback differed from the planned change.")
            resources.verify(persisted)
        except resources.ResourceError as error:
            raise ReadbackError(str(error)) from error
        return public_result(state["id"], persisted, receipt)


def record_failed_readback(store, command, message):
    with closing(store.connection()) as db, db:
        db.execute("BEGIN IMMEDIATE")
        state = store.read(db)
        if state["id"] == command.run_id:
            data = data_for(state)
            resources.record(data, command.tab, "Adapt", "Write rolled back", message,
                             getattr(command, "request_id", None), getattr(command, "role", None))
            save(db, state, data)


def public_result(run_id, data, receipt=None):
    return {"state": resources.snapshot(run_id, data, agent.model_enabled()), "receipt": receipt}


def require_own_origin(request):
    origin = request.headers.get("origin")
    fetch_site = request.headers.get("sec-fetch-site")
    if fetch_site not in {None, "same-origin"} or (origin and origin != f"{request.url.scheme}://{request.url.netloc}"):
        raise HTTPException(status_code=403, detail="Open the local CampusFlow dashboard to submit changes.")


def register_resource_routes(application):
    pending_notes = set()
    note_lock = Lock()

    @application.get("/api/resources")
    def resource_state(request: Request, response: Response):
        response.headers["Cache-Control"] = "no-store"
        return public_result(*read(request.app.state.store))

    @application.post("/api/resources/command")
    def resource_command(command: resources.Command, request: Request, response: Response):
        require_own_origin(request)
        response.headers["Cache-Control"] = "no-store"
        store = request.app.state.store
        try:
            return apply_command(store, command)
        except ReadbackError as error:
            try:
                record_failed_readback(store, command, str(error))
            except sqlite3.Error:
                pass
            raise HTTPException(status_code=409, detail=str(error)) from error
        except resources.ResourceError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error

    @application.post("/api/resources/interpret")
    def interpret_note(body: resource_agent.Intake, request: Request, response: Response):
        require_own_origin(request)
        response.headers["Cache-Control"] = "no-store"
        store = request.app.state.store
        run_id, data = read(store)
        if run_id != body.run_id:
            raise HTTPException(status_code=409, detail="The demo was reset. Refresh before interpreting another note.")
        key = (run_id, body.tab, hashlib.sha256(body.note.encode()).digest())
        with note_lock:
            if key in pending_notes:
                return resource_agent.fallback("This note is already being interpreted.")
            pending_notes.add(key)
        try:
            day, _ = resources.clock_parts(data["clock"])
            result = resource_agent.interpret(body.tab, body.note, day)
            with closing(store.connection()) as db, db:
                db.execute("BEGIN IMMEDIATE")
                state = store.read(db)
                if state["id"] != run_id:
                    raise HTTPException(status_code=409, detail="The demo was reset. The previous interpretation expired.")
                data = data_for(state)
                label = result["mode"]
                if label == "Gemini":
                    intake_id = resources.identifier()
                    fields = result["fields"]
                    data["intakes"][intake_id] = fields
                    result["intake_id"] = intake_id
                    day = date.fromisoformat(fields["day"])
                    start = resources.minutes_for(day, fields["start"])
                    end = resources.minutes_for(day, fields["end"])
                    candidate = {**fields, "start": start, "end": end, "protected": False}
                    if data["clock"] <= start < end <= data["clock"] + 14 * 1440:
                        choices, _ = resources.FIND_OPTIONS[body.tab](data, candidate)
                        result["message"] += f" {len(choices)} eligible option{'s' if len(choices) != 1 else ''} found in the local ledger."
                    resources.record(data, body.tab, "Understand", "Gemini selected a read-only lookup",
                                     f"{resource_agent.TOOL_NAMES[body.tab]} · {fields['target']}")
                else:
                    resources.record(data, body.tab, "Adapt", label, result["message"])
                save(db, state, data)
            return result
        finally:
            with note_lock:
                pending_notes.discard(key)
