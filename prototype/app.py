"""Local CampusFlow API and transactional synthetic scenario storage."""

from contextlib import asynccontextmanager, closing
from dataclasses import dataclass
import json
import os
from pathlib import Path
import sqlite3
from tempfile import TemporaryDirectory
from typing import Literal, Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict
from starlette.middleware.trustedhost import TrustedHostMiddleware

import agent
import scenario


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
        return {
            **state, "audit": entries, "model_available": agent.model_enabled(),
            "note": scenario.NOTE if state["phase"] != "baseline" else None,
        }

    def apply(self, command, choice=None):
        with closing(self.connection()) as db, db:
            db.execute("BEGIN IMMEDIATE")
            state = self.read(db)
            scenario.require(state["id"] == command.run_id, "This demo was reset. Reload the current scenario.")
            entries = []
            branch = None

            if command.action == "reset":
                db.execute("DELETE FROM audit WHERE run = ?", (state["id"],))
                state = scenario.fixture()
            elif command.action == "trigger":
                scenario.inject_change(state, entries)
            elif command.action in {"run", "confirm"}:
                scenario.run_agent(state, entries, choice)
            elif command.action in {"occupied", "vacant", "stale", "override"}:
                scenario.room_event(state, entries, command.action)
            elif command.action == "expire":
                scenario.expire_overflow(state, entries)
            elif command.action == "exit":
                scenario.exit_vehicle(state, entries, "GATE-EXIT-021", "CAR-021")
            elif command.action == "exit_overflow":
                scenario.exit_vehicle(state, entries, "GATE-EXIT-078", "CAR-078")
            elif command.action in {"checkout_kit", "return_kit"}:
                scenario.update_equipment(state, entries, checkout=command.action == "checkout_kit")
            elif command.action == "review":
                scenario.require(all([command.branch, command.proposal, command.role, command.decision]),
                                 "Select a proposal and a review decision.")
                branch = scenario.review(state, entries, command.branch, command.proposal,
                                         command.role, command.decision)

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


def create_app():
    @asynccontextmanager
    async def lifespan(application):
        with TemporaryDirectory(prefix="campusflow-") as scratch:
            configured = os.environ.get("CAMPUSFLOW_DB")
            path = Path(configured) if configured else Path(scratch) / "demo.sqlite3"
            application.state.store = Store(path)
            application.state.store.initialize()
            yield

    application = FastAPI(title="CampusFlow", lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)
    application.add_middleware(TrustedHostMiddleware, allowed_hosts=["127.0.0.1", "localhost", "testserver"])
    application.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")

    @application.get("/")
    def landing():
        return FileResponse(ROOT / "static" / "landing.html")

    @application.get("/fleet")
    @application.get("/resources")
    def dashboard():
        return FileResponse(ROOT / "static" / "index.html")

    @application.get("/api/state")
    def state():
        return application.state.store.snapshot()

    @application.post("/api/command")
    def command(body: Command):
        store = application.state.store
        try:
            choice = None
            if body.action == "run":
                current = store.snapshot()
                scenario.require(current["id"] == body.run_id and current["phase"] == "detected",
                                 "Trigger a new schedule change before running the model.")
                choice = agent.select_tool()
            elif body.action == "confirm":
                choice = agent.MANUAL
            return store.apply(body, choice)
        except scenario.ScenarioError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error

    return application


app = create_app()
