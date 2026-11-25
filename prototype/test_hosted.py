"""Deployment regressions and opt-in PostgreSQL integration tests."""

from concurrent.futures import ThreadPoolExecutor
import os
from unittest import TestCase, skipUnless
from unittest.mock import patch

from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from prototype import scenario
from prototype.app import create_app


BASE_URL = "https://campusflow.example"
SESSION_COOKIE = "__Host-campusflow-demo"
DATABASE_URL = os.environ.get("CAMPUSFLOW_TEST_DATABASE_URL")


class HostedClients(TestCase):
    def setUp(self):
        env = patch.dict(os.environ, {"VERCEL_ENV": "preview", "CAMPUSFLOW_ENABLE_HOSTED_MODEL": ""})
        env.start()
        self.addCleanup(env.stop)

    def client(self, database_url=""):
        manager = TestClient(
            create_app(hosted=True, database_url=database_url), base_url=BASE_URL,
        )
        client = manager.__enter__()
        self.addCleanup(manager.__exit__, None, None, None)
        return client


class HostedTest(HostedClients):
    def test_hosted_pages_load_without_database_and_hardware_routes_are_local(self):
        client = self.client()
        for url in ("/", "/fleet", "/resources", "/static/landing.css"):
            with self.subTest(url=url):
                self.assertEqual(client.get(url).status_code, 200)
        for url in ("/room-console", "/room-panel", "/static/room_console.html", "/static/room_panel.html", "/api/room/live"):
            self.assertEqual(client.get(url).status_code, 404)
        self.assertEqual(client.post("/api/room/telemetry", json={"person_count": 1}).status_code, 404)
        with self.assertRaises(WebSocketDisconnect):
            with client.websocket_connect("/ws/room-panel"):
                self.fail("The hosted app accepted a hardware socket.")
        for url in ("/api/health", "/api/state"):
            response = client.get(url)
            self.assertEqual(response.status_code, 503)
            self.assertEqual(response.headers["cache-control"], "private, no-store")
            self.assertIn("DATABASE_URL", response.json()["detail"])


@skipUnless(DATABASE_URL, "Set CAMPUSFLOW_TEST_DATABASE_URL to run PostgreSQL integration tests.")
class HostedPostgresTest(HostedClients):
    def command(self, client, run, action, **fields):
        return client.post("/api/command", json={"run_id": run, "action": action, **fields},
                           headers={"Origin": BASE_URL})

    def start(self, client):
        response = client.get("/api/state")
        self.assertEqual(response.status_code, 200, response.text)
        run = response.json()["id"]
        self.assertEqual(self.command(client, run, "trigger").status_code, 200)
        result = self.command(client, run, "confirm")
        self.assertEqual(result.status_code, 200, result.text)
        return result.json()

    def test_supabase_environment_and_row_security(self):
        import psycopg

        with patch.dict(os.environ, {"DATABASE_URL": "", "POSTGRES_URL": DATABASE_URL}):
            response = self.client(database_url=None).get("/api/health")
        self.assertEqual(response.status_code, 200, response.text)
        with psycopg.connect(DATABASE_URL) as db:
            enabled, = db.execute("""
                SELECT relrowsecurity FROM pg_class WHERE oid = 'campusflow_demo_sessions'::regclass
            """).fetchone()
        self.assertTrue(enabled)

    @staticmethod
    def approval(state, branch):
        return {"branch": branch, "role": scenario.ROLES[branch], "decision": "approve",
                "proposal": state["branches"][branch]["id"]}

    def test_sessions_are_private_and_survive_a_new_app_instance(self):
        first = self.client(DATABASE_URL)
        fresh = self.client(DATABASE_URL)
        self.assertEqual(first.get("/api/health").json(), {"status": "ok"})
        initial = first.get("/api/state")
        self.assertIn("HttpOnly", initial.headers["set-cookie"])
        self.assertIn("Secure", initial.headers["set-cookie"])
        self.assertEqual(initial.headers["cache-control"], "private, no-store")
        initial_run = initial.json()["id"]

        self.assertEqual(self.command(fresh, initial_run, "trigger").status_code, 409)
        fresh_run = fresh.get("/api/state").json()["id"]
        self.assertNotEqual(fresh_run, initial_run)
        self.assertEqual(self.command(fresh, initial_run, "trigger").status_code, 409)
        foreign = first.post("/api/command", json={"action": "trigger", "run_id": initial_run},
                             headers={"Origin": "https://another.example"})
        self.assertEqual(foreign.status_code, 403)
        proxied = first.post(
            "/api/command", json={"action": "trigger", "run_id": initial_run},
            headers={"Origin": BASE_URL, "Host": "127.0.0.1:54321",
                     "X-Forwarded-Host": "campusflow.example", "Sec-Fetch-Site": "same-origin"},
        )
        self.assertEqual(proxied.status_code, 200, proxied.text)

        restarted = self.client(DATABASE_URL)
        restarted.cookies.set(SESSION_COOKIE, first.cookies[SESSION_COOKIE])
        self.assertEqual(restarted.get("/api/state").json()["phase"], "detected")
        self.assertEqual(fresh.get("/api/state").json()["phase"], "baseline")

    def test_approval_recovery_and_reset(self):
        client = self.client(DATABASE_URL)
        state = self.start(client)
        run = state["id"]
        parked = self.command(client, run, "review", **self.approval(state, "parking"))
        self.assertEqual(parked.status_code, 200, parked.text)
        self.assertEqual(parked.json()["branches"]["parking"]["status"], "verified")
        self.assertEqual(self.command(client, run, "occupied").status_code, 200)
        self.assertEqual(self.command(client, run, "review", **self.approval(state, "room")).status_code, 409)
        recovered = self.command(client, run, "vacant")
        self.assertEqual(recovered.status_code, 200, recovered.text)
        final = self.command(client, run, "review", **self.approval(recovered.json(), "room"))
        self.assertEqual(final.status_code, 200, final.text)
        self.assertEqual(final.json()["room"]["devices"], scenario.STANDBY)
        self.assertEqual(final.json()["branches"]["parking"]["status"], "verified")
        self.assertIn("C-101 device readback verified", {entry["title"] for entry in final.json()["audit"]})
        reset = self.command(client, run, "reset").json()
        self.assertNotEqual(reset["id"], run)
        self.assertEqual(reset["audit"], [])
        self.assertEqual(self.command(client, run, "trigger").status_code, 409)

    def test_concurrent_approval_and_readback_rollback(self):
        first = self.client(DATABASE_URL)
        second = self.client(DATABASE_URL)
        state = self.start(first)
        run = state["id"]
        second.cookies.set(SESSION_COOKIE, first.cookies[SESSION_COOKIE])
        approval = self.approval(state, "parking")
        with patch.object(scenario, "verify", side_effect=scenario.ScenarioError("Readback failed.")):
            self.assertEqual(self.command(first, run, "review", **approval).status_code, 409)
        self.assertEqual(second.get("/api/state").json(), state)
        with ThreadPoolExecutor(max_workers=2) as workers:
            statuses = list(workers.map(
                lambda client: self.command(client, run, "review", **approval).status_code,
                (first, second),
            ))
        self.assertEqual(sorted(statuses), [200, 409])
        audit = second.get("/api/state").json()["audit"]
        self.assertEqual(sum(item["title"] == "OV-01 readback verified" for item in audit), 1)
