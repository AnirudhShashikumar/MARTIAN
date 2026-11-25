"""Durable, per-browser simulation state for the Vercel entrypoint."""

from contextlib import contextmanager
from hashlib import sha256
import logging
import secrets
from threading import Lock

import psycopg
from psycopg.types.json import Jsonb

from prototype import scenario


SESSION_SECONDS = 24 * 60 * 60
log = logging.getLogger(__name__)


class StorageUnavailable(RuntimeError):
    """The hosted simulation store could not be reached."""


def session_key(token):
    # Store the digest so a database read does not reveal a usable cookie.
    return sha256(token.encode("ascii")).hexdigest()


class PostgresStore:
    def __init__(self, database_url):
        self.database_url = database_url
        self.schema_ready = False
        self.schema_lock = Lock()

    @contextmanager
    def connection(self):
        if not self.database_url:
            raise StorageUnavailable("Set DATABASE_URL or POSTGRES_URL to enable the hosted simulation.")
        try:
            with psycopg.connect(self.database_url, connect_timeout=5, prepare_threshold=None) as db:
                db.execute("SET LOCAL statement_timeout = '5s'")
                yield db
        except psycopg.Error as error:
            log.warning("Hosted demo database operation failed (%s)", type(error).__name__)
            raise StorageUnavailable("The hosted simulation database is unavailable. Try again shortly.") from error

    def initialize(self):
        if self.schema_ready:
            return
        with self.schema_lock:
            if self.schema_ready:
                return
            with self.connection() as db:
                # Serialize schema creation across cold instances.
                db.execute("SELECT pg_advisory_xact_lock(1758859432, 1)")
                db.execute("""
                    CREATE TABLE IF NOT EXISTS campusflow_demo_sessions (
                        session_key text PRIMARY KEY,
                        state jsonb NOT NULL,
                        audit jsonb NOT NULL DEFAULT '[]'::jsonb,
                        expires_at timestamptz NOT NULL
                    )
                """)
                # The Supabase Data API must not expose the server's session table.
                db.execute("ALTER TABLE campusflow_demo_sessions ENABLE ROW LEVEL SECURITY")
                db.execute("""
                    CREATE INDEX IF NOT EXISTS campusflow_demo_expiry
                    ON campusflow_demo_sessions (expires_at)
                """)
            self.schema_ready = True

    def ready(self):
        self.initialize()
        with self.connection() as db:
            db.execute("SELECT 1 FROM campusflow_demo_sessions LIMIT 1")

    @staticmethod
    def read(db, key, lock=False):
        query = """
            SELECT state, audit FROM campusflow_demo_sessions
            WHERE session_key = %s AND expires_at > now()
        """
        if lock:
            query += " FOR UPDATE"
        return db.execute(query, (key,)).fetchone()

    def open_session(self, token):
        self.initialize()
        with self.connection() as db:
            if token:
                row = self.read(db, session_key(token))
                if row is not None:
                    state, audit = row
                    return token, {**state, "audit": audit}

            token = secrets.token_urlsafe(32)
            state = scenario.fixture()
            db.execute("""
                DELETE FROM campusflow_demo_sessions
                WHERE session_key IN (
                    SELECT session_key FROM campusflow_demo_sessions
                    WHERE expires_at <= now() ORDER BY expires_at
                    LIMIT 100 FOR UPDATE SKIP LOCKED
                )
            """)
            db.execute("""
                INSERT INTO campusflow_demo_sessions (session_key, state, expires_at)
                VALUES (%s, %s, now() + %s * INTERVAL '1 second')
            """, (session_key(token), Jsonb(state), SESSION_SECONDS))
            return token, {**state, "audit": []}

    def snapshot(self, token):
        self.initialize()
        with self.connection() as db:
            row = self.read(db, session_key(token))
            scenario.require(row is not None, "This demo session expired. Reload to start a new run.")
            state, audit = row
            return {**state, "audit": audit}

    def apply(self, token, command, choice=None):
        self.initialize()
        key = session_key(token)
        with self.connection() as db:
            row = self.read(db, key, lock=True)
            scenario.require(row is not None, "This demo session expired. Reload to start a new run.")
            state, audit = row
            entries = []
            state, branch = scenario.apply_command(state, command, entries, choice)
            persisted, = db.execute("""
                UPDATE campusflow_demo_sessions SET state = %s WHERE session_key = %s RETURNING state
            """, (Jsonb(state), key)).fetchone()
            if branch:
                scenario.verify(persisted, entries, branch)
            if command.action == "reset":
                audit = []
            audit.extend(entries)
            db.execute("""
                UPDATE campusflow_demo_sessions SET audit = %s WHERE session_key = %s
            """, (Jsonb(audit), key))
            return {**persisted, "audit": audit}
