"""End-to-end checks for the local resource workflows and approval guards."""

from concurrent.futures import ThreadPoolExecutor
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch
from uuid import uuid4

from fastapi.testclient import TestClient

from prototype import resource_agent, resources
from prototype.app import create_app


class ResourceTests(TestCase):
    def setUp(self):
        folder = TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        config = patch.dict(os.environ, {
            "CAMPUSFLOW_DB": str(Path(folder.name) / "resources.sqlite3"),
            "GEMINI_API_KEY": "", "CAMPUSFLOW_GEMINI_MODEL": "",
        })
        config.start()
        self.addCleanup(config.stop)
        client = TestClient(create_app())
        self.client = client.__enter__()
        self.addCleanup(client.__exit__, None, None, None)
        self.run_id = self.state()["run_id"]

    def state(self, client=None):
        return (client or self.client).get("/api/resources").json()["state"]

    def command(self, tab, action, status=200, **details):
        body = {"run_id": self.run_id, "key": uuid4().hex, "tab": tab, "action": action, **details}
        response = self.client.post("/api/resources/command", json=body)
        self.assertEqual(response.status_code, status, response.text)
        return response.json()

    def submit(self, tab, **details):
        fields = {
            "requester": "DEMO-01", "day": resources.DAY.isoformat(), "start": "14:00", "end": "15:00",
            "quantity": 1, "target": {"labs": "LAB-2", "library": "Quiet", "equipment": "racket"}[tab],
            **details,
        }
        result = self.command(tab, "submit", **fields)
        return self.row(result["receipt"]["subject"], result["state"])

    def row(self, identifier, state=None):
        return next(row for row in (state or self.state())["requests"] if row["id"] == identifier)

    def approval(self, row, **details):
        proposal = row["proposal"]
        choices = proposal["choices"]
        return {
            "request_id": row["id"], "proposal_id": proposal["id"],
            "choice_id": choices[0]["id"] if choices else None,
            "role": proposal["role"], "decision": "approve", **details,
        }

    def approve(self, row, status=200, **details):
        result = self.command(row["tab"], "review", status=status, **self.approval(row, **details))
        return self.row(row["id"], result["state"]) if status == 200 else result

    def transition(self, row, action, role="Requester", status=200, **details):
        response = self.command(row["tab"], action, status=status, request_id=row["id"], role=role, **details)
        return self.row(row["id"], response["state"]) if status == 200 else response

    def test_labs_conflict_role_reschedule_cancel_and_restart(self):
        initial = self.submit("labs", start="14:20", end="15:05", quantity=24, feature="Computers", session="Workshop")
        self.assertEqual(initial["proposal"]["choices"][0]["assets"], ["LAB-1"])
        self.assertIn("Preferred lab blocked", initial["reason"])
        self.approve(initial, status=409, role="Sports desk")
        booked = self.approve(initial)
        self.assertEqual(booked["status"], "booked")
        self.assertEqual(booked["session"], "Workshop")

        replacement = self.submit("labs", start="15:05", end="15:35", target="LAB-2", replaces=booked["id"])
        scheduled = self.approve(replacement)
        self.assertEqual(scheduled["assets"], ["LAB-2"])
        self.assertEqual(self.row(booked["id"])["status"], "rescheduled")
        cancellation = self.transition(scheduled, "cancel", role="Lab coordinator")
        self.assertEqual(cancellation["status"], "cancel_pending")

        with TestClient(create_app()) as restarted:
            self.assertEqual(self.state(restarted)["run_id"], self.run_id)
            self.assertEqual(self.row(scheduled["id"], self.state(restarted))["status"], "cancel_pending")

        canceled = self.approve(cancellation)
        self.assertEqual(canceled["status"], "canceled")
        self.assertTrue(any(event["stage"] == "Verify" for event in self.state()["audit"]))
        self.assertFalse(self.client.get("/api/state").json()["session"])

    def test_concurrent_approval_and_readback_rollback(self):
        first = self.submit("labs", target="LAB-1")
        second = self.submit("labs", target="LAB-1", requester="DEMO-02")
        with patch("prototype.resources.verify", side_effect=resources.ResourceError("Test readback mismatch")):
            self.approve(first, status=409)
        self.assertEqual(self.row(first["id"])["status"], "pending")
        self.assertEqual(self.state()["audit"][-1]["title"], "Write rolled back")

        bodies = [
            {"run_id": self.run_id, "key": uuid4().hex, "tab": "labs", "action": "review", **self.approval(row)}
            for row in (first, second)
        ]

        def submit_review(body):
            return self.client.post("/api/resources/command", json=body).status_code

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = sorted(pool.map(submit_review, bodies))
        self.assertEqual(results, [200, 409])
        self.assertEqual(sum(row["status"] == "booked" for row in self.state()["requests"]), 1)

    def test_library_expiry_fifo_claim_checkin_and_protected_capacity(self):
        original = self.approve(self.submit("library"))
        self.assertEqual(original["assets"], ["Q10"])
        second = self.submit("library", requester="DEMO-02", waitlist=True)
        third = self.submit("library", requester="DEMO-03", waitlist=True)
        self.assertEqual(second["status"], "queued")
        self.assertEqual(third["status"], "queued")
        self.command("library", "advance")
        self.assertEqual(self.row(original["id"])["status"], "expired")
        offered = self.row(second["id"])
        self.assertEqual(offered["status"], "offered")
        self.assertEqual(offered["assets"], ["Q10"])
        self.assertEqual(self.row(third["id"])["status"], "queued")
        held = self.transition(offered, "claim")
        occupied = self.transition(held, "check_in")
        self.transition(occupied, "release")
        self.assertEqual(self.row(third["id"])["status"], "offered")

        protected = self.submit("library", requester="DEMO-04", start="14:10", protected=True)
        self.approve(protected, status=409, role="Requester")
        protected = self.approve(protected)
        self.assertIn(protected["assets"][0], {"Q11", "Q12"})
        self.transition(protected, "check_in", status=409)
        self.assertEqual(self.transition(protected, "check_in", role="Library staff")["status"], "checked_in")

    def test_stock_reservation_partial_return_inspection_and_idempotency(self):
        reserved = self.approve(self.submit("equipment", quantity=2))
        checked_out = self.transition(reserved, "checkout", role="Sports desk")
        good, damaged = checked_out["assets"]
        self.assertEqual(checked_out["status"], "checked_out")
        waiting = self.submit("equipment", quantity=2, requester="DEMO-02", waitlist=True)
        self.assertEqual(waiting["status"], "queued")

        body = {
            "run_id": self.run_id, "key": uuid4().hex, "tab": "equipment", "action": "return",
            "request_id": checked_out["id"], "role": "Sports desk", "item": good, "condition": "good",
        }
        first = self.client.post("/api/resources/command", json=body)
        retry = self.client.post("/api/resources/command", json=body)
        self.assertEqual(first.status_code, 200, first.text)
        self.assertEqual(first.json()["receipt"], retry.json()["receipt"])
        self.assertEqual(self.client.post("/api/resources/command", json={**body, "item": damaged}).status_code, 409)
        self.assertEqual(self.row(waiting["id"])["status"], "offered")
        self.assertEqual(self.row(checked_out["id"])["status"], "checked_out")

        returned = self.transition(checked_out, "return", role="Sports desk", item=damaged, condition="damaged")
        self.assertEqual(returned["status"], "returned")
        self.assertEqual(next(item for item in self.state()["items"] if item["id"] == damaged)["condition"], "inspection")
        self.command("equipment", "clear_inspection", item=damaged, role="Sports desk")
        self.assertEqual(next(item for item in self.state()["items"] if item["id"] == damaged)["condition"], "ready")

    def test_overdue_stock_and_old_run_reset(self):
        reserved = self.approve(self.submit("equipment", end="14:10"))
        self.transition(reserved, "checkout", role="Sports desk")
        self.command("equipment", "advance")
        self.assertEqual(self.row(reserved["id"])["status"], "checked_out")
        next_request = self.submit("equipment", start="14:10", quantity=3)
        self.assertEqual(next_request["status"], "unavailable")
        response = self.client.post("/api/command", json={"action": "reset", "run_id": self.run_id})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.state()["requests"], [])
        self.command("equipment", "advance", status=409)

    def test_interpret_grounded_note_per_tab_and_offline_fallback(self):
        examples = [
            ("labs", "LAB-2", "Book Lab 2 from 14:20 to 15:05 for 24 students with computers."),
            ("library", "Quiet", "Find a quiet seat from 14:00 to 15:00."),
            ("equipment", "racket", "Reserve two badminton rackets from 14:00 to 15:00."),
        ]
        url = "/api/resources/interpret"
        for tab, target, note in examples:
            request = {"run_id": self.run_id, "tab": tab, "note": note}
            offline = self.client.post(url, json=request).json()
            self.assertEqual(offline["mode"], "Structured")
            with patch("prototype.agent.model_enabled", return_value=True), patch(
                "prototype.resource_agent.read_tool",
                return_value={"steps": [{"type": "function_call", "name": resource_agent.TOOL_NAMES[tab],
                                         "arguments": {"target": target}}]},
            ):
                result = self.client.post(url, json=request).json()
                self.assertEqual(result["mode"], "Gemini", result)
                fields = dict(result["fields"])
                self.assertEqual(fields.pop("tab"), tab)
                row = self.submit(tab, intake_id=result["intake_id"], **fields)
                self.assertEqual(row["mode"], "Gemini")
                changed = self.submit(tab, intake_id=result["intake_id"], **{**fields, "end": "15:30"})
                self.assertEqual(changed["mode"], "Structured")

        with patch("prototype.agent.model_enabled", return_value=True), patch(
            "prototype.resource_agent.read_tool", side_effect=TimeoutError,
        ):
            self.assertEqual(self.client.post(url, json=request).json()["mode"], "Structured")

        ambiguous = {"run_id": self.run_id, "tab": "labs", "note": "Lab 1 or Lab 2 from 14:00 to 15:00."}
        with patch("prototype.agent.model_enabled", return_value=True), patch(
            "prototype.resource_agent.read_tool",
            return_value={"steps": [{"type": "function_call", "name": "lookup_lab_schedule",
                                     "arguments": {"target": "LAB-2"}}]},
        ):
            self.assertEqual(self.client.post(url, json=ambiguous).json()["mode"], "Needs clarification")

    def test_same_origin_and_hosted_scope(self):
        response = self.client.post(
            "/api/resources/command", headers={"Origin": "https://elsewhere.example"},
            json={"tab": "labs", "action": "advance", "run_id": self.run_id, "key": uuid4().hex},
        )
        self.assertEqual(response.status_code, 403)
        with TestClient(create_app(hosted=True, database_url="")) as hosted:
            self.assertEqual(hosted.get("/api/resources").status_code, 404)
