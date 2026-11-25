"""CampusFlow HTTP API."""

from contextlib import asynccontextmanager, closing
from dataclasses import dataclass
import json
import mimetypes
import os
from pathlib import Path
import re
import sqlite3
from tempfile import TemporaryDirectory
from typing import Literal, Optional

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict

from prototype import agent, cctv_stream, scenario


mimetypes.add_type("image/webp", ".webp")


def _allowed_local_host(host: str) -> bool:
    name = host.split(":")[0].lower()
    return name in {"127.0.0.1", "localhost", "testserver"} or name.startswith(("192.168.", "10.", "172."))


class LocalHostMiddleware:
    """Permit localhost (adb reverse) and private LAN hotspot IPs for HTTP and WebSockets."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] in {"http", "websocket"}:
            headers = dict(scope.get("headers") or [])
            host = headers.get(b"host", b"").decode("latin-1")
            if host and not _allowed_local_host(host):
                if scope["type"] == "http":
                    resp = PlainTextResponse("Invalid host header", status_code=400)
                    await resp(scope, receive, send)
                    return
                await send({"type": "websocket.close", "code": 1008})
                return
        await self.app(scope, receive, send)


ROOT = Path(__file__).parent


@dataclass
class Store:
    path: Path

    def connection(self):
        return sqlite3.connect(self.path, timeout=5)

    def initialize(self):
        with closing(self.connection()) as db, db:
            db.execute("CREATE TABLE IF NOT EXISTS demo (singleton INTEGER PRIMARY KEY, state TEXT NOT NULL)")
            db.execute(
                "CREATE TABLE IF NOT EXISTS audit (id INTEGER PRIMARY KEY, run TEXT NOT NULL, entry TEXT NOT NULL)"
            )
            db.execute("INSERT OR IGNORE INTO demo VALUES (1, ?)", (json.dumps(scenario.fixture()),))
            state = self.read(db)
            if "equipment" not in state:
                state["equipment"] = dict(scenario.EQUIPMENT)
                db.execute("UPDATE demo SET state = ? WHERE singleton = 1", (json.dumps(state),))

    @staticmethod
    def read(db):
        return json.loads(db.execute("SELECT state FROM demo WHERE singleton = 1").fetchone()[0])

    def snapshot(self):
        with closing(self.connection()) as db:
            db.execute("BEGIN")
            return self.payload(db, self.read(db))

    @staticmethod
    def payload(db, state):
        entries = [
            json.loads(entry) for (entry,) in db.execute(
                "SELECT entry FROM audit WHERE run = ? ORDER BY id", (state["id"],)
            )
        ]
        return {**state, "audit": entries}

    def apply(self, command, choice=None):
        with closing(self.connection()) as db, db:
            db.execute("BEGIN IMMEDIATE")
            state = self.read(db)
            entries = []
            previous_run = state["id"]
            state, branch = scenario.apply_command(state, command, entries, choice)
            if state["id"] != previous_run:
                db.execute("DELETE FROM audit WHERE run = ?", (previous_run,))

            db.execute("UPDATE demo SET state = ? WHERE singleton = 1", (json.dumps(state),))
            persisted = self.read(db)
            if branch:
                scenario.verify(persisted, entries, branch)
            db.executemany(
                "INSERT INTO audit (run, entry) VALUES (?, ?)",
                [(state["id"], json.dumps(entry)) for entry in entries],
            )
            return self.payload(db, persisted)


class Command(BaseModel):
    model_config = ConfigDict(extra="forbid")
    run_id: str
    action: Literal[
        "trigger", "run", "confirm", "occupied", "vacant", "stale", "override",
        "expire", "exit", "exit_overflow", "checkout_kit", "return_kit", "review", "reset",
    ]
    branch: Optional[Literal["parking", "room"]] = None
    proposal: Optional[str] = None
    role: Optional[Literal["Parking attendant", "Facilities supervisor"]] = None
    decision: Optional[Literal["approve", "reject"]] = None


class CctvStartPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")
    source: str = cctv_stream.DEFAULT_DROIDCAM_URL
    hold_seconds: float = 3.0


class CctvOverridePayload(BaseModel):
    model_config = ConfigDict(extra="forbid")
    mode: Literal["toggle", "on", "off", "auto"] = "toggle"


def create_app(*, hosted=False, database_url=None, cctv_engine=None):
    @asynccontextmanager
    async def lifespan(application):
        if hosted:
            yield
            return
        with TemporaryDirectory(prefix="campusflow-") as scratch:
            configured = os.environ.get("CAMPUSFLOW_DB")
            path = Path(configured) if configured else Path(scratch) / "demo.sqlite3"
            application.state.store = Store(path)
            application.state.store.initialize()
            application.state.cctv = cctv_engine if cctv_engine is not None else cctv_stream.ClassroomCCTVEngine()
            try:
                yield
            finally:
                application.state.cctv.stop()

    application = FastAPI(title="CampusFlow", lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)
    if not hosted:
        application.add_middleware(LocalHostMiddleware)

    secure_cookie = os.environ.get("VERCEL_ENV") != "development"
    session_cookie = "__Host-campusflow-demo" if secure_cookie else "campusflow-demo"
    model_allowed = not hosted or os.environ.get("CAMPUSFLOW_ENABLE_HOSTED_MODEL") == "1"

    if hosted:
        from prototype.hosted_store import PostgresStore, SESSION_SECONDS, StorageUnavailable

        if database_url is None:
            database_url = os.environ.get("DATABASE_URL") or os.environ.get("POSTGRES_URL")
        hosted_store = PostgresStore(database_url)

        @application.exception_handler(StorageUnavailable)
        async def storage_unavailable(_request, error):
            return JSONResponse({"detail": str(error)}, status_code=503)

        @application.middleware("http")
        async def prevent_shared_api_cache(request, call_next):
            response = await call_next(request)
            if request.url.path.startswith("/api/"):
                response.headers["Cache-Control"] = "private, no-store"
            return response

    def demo_payload(state):
        return {
            **{key: value for key, value in state.items() if key != "resources"},
            "model_available": model_allowed and agent.model_enabled(),
            "note": scenario.NOTE if state["phase"] != "baseline" else None,
            **({"local_resource_workflows": True} if not hosted else {}),
        }

    def read_session_cookie(request):
        token = request.cookies.get(session_cookie, "")
        return token if re.fullmatch(r"[A-Za-z0-9_-]{43}", token) else None

    @application.get("/")
    def landing():
        return FileResponse(ROOT / "static" / "landing.html")

    @application.get("/fleet")
    def fleet_dashboard():
        return FileResponse(ROOT / "static" / "fleet.html")

    @application.get("/resources")
    def dashboard():
        return FileResponse(ROOT / "static" / "index.html")

    @application.get("/api/health")
    def health():
        if hosted:
            hosted_store.ready()
        return {"status": "ok"}

    @application.get("/api/state")
    def state(request: Request, response: Response):
        if not hosted:
            return demo_payload(application.state.store.snapshot())
        token = read_session_cookie(request)
        session, snapshot = hosted_store.open_session(token)
        if session != token:
            response.set_cookie(session_cookie, session, max_age=SESSION_SECONDS,
                                secure=secure_cookie, httponly=True, samesite="lax")
        return demo_payload(snapshot)

    @application.post("/api/command")
    def command(body: Command, request: Request):
        token = None
        if hosted:
            origin = request.headers.get("origin")
            # Vercel forwards the browser-facing host even when its dev proxy rewrites Host.
            host = request.headers.get("x-forwarded-host") or request.url.netloc
            scheme = "https" if secure_cookie else "http"
            fetch_site = request.headers.get("sec-fetch-site")
            if fetch_site not in (None, "same-origin") or (origin is not None and origin != f"{scheme}://{host}"):
                raise HTTPException(status_code=403, detail="Use CampusFlow from its own site.")
            token = read_session_cookie(request)
            if token is None:
                raise HTTPException(status_code=409, detail="Open a dashboard to start a demo session.")

        try:
            choice = None
            if body.action == "run":
                current = hosted_store.snapshot(token) if hosted else application.state.store.snapshot()
                scenario.require(current["id"] == body.run_id and current["phase"] == "detected",
                                 "Trigger a new schedule change before running the model.")
                choice = agent.select_tool() if model_allowed else agent.MANUAL
            elif body.action == "confirm":
                choice = agent.MANUAL
            if hosted:
                return demo_payload(hosted_store.apply(token, body, choice))
            return demo_payload(application.state.store.apply(body, choice))
        except scenario.ScenarioError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error

    if not hosted:
        from prototype.resource_api import register_resource_routes

        register_resource_routes(application)
        register_cctv_routes(application)
    application.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")

    return application


def register_cctv_routes(application):
    @application.get("/api/cctv/status")
    def cctv_status():
        return application.state.cctv.status()

    @application.post("/api/cctv/start")
    def cctv_start(body: CctvStartPayload):
        try:
            return application.state.cctv.start(source=body.source, hold_seconds=body.hold_seconds)
        except RuntimeError as error:
            raise HTTPException(status_code=503, detail=str(error)) from error

    @application.post("/api/cctv/stop")
    def cctv_stop():
        return application.state.cctv.stop()

    @application.post("/api/cctv/override")
    def cctv_override(body: Optional[CctvOverridePayload] = None):
        mode = body.mode if body is not None else "toggle"
        return application.state.cctv.set_manual_override(mode)

    @application.post("/api/cctv/events/clear")
    def cctv_clear_events():
        return application.state.cctv.clear_events()

    @application.get("/api/cctv/stream")
    def cctv_stream_endpoint():
        engine = application.state.cctv
        if not engine.status()["active"]:
            raise HTTPException(status_code=409, detail="CCTV is not active. Click Initialize CCTV Cam first.")
        return StreamingResponse(
            engine.mjpeg_frames(),
            media_type="multipart/x-mixed-replace; boundary=frame",
            headers={"Cache-Control": "no-store, no-cache, must-revalidate"},
        )


app = create_app()
