"""Regression checks for safety, replay, and sample allocation."""

from concurrent.futures import ThreadPoolExecutor
from unittest import TestCase, main
from unittest.mock import patch

from fastapi.testclient import TestClient

import agent
import scenario
from app import create_app


class ScenarioTest(TestCase):
    def setUp(self):
        client = TestClient(create_app())
        self.client = client.__enter__()
        self.addCleanup(client.__exit__, None, None, None)
        self.state = self.client.get("/api/state").json()

    def command(self, action, expected=200, **fields):
        reply = self.client.post("/api/command", json={
            "run_id": self.state["id"], "action": action, **fields,
        })
        self.assertEqual(reply.status_code, expected, reply.text)
        if expected == 200:
            self.state = reply.json()
        return reply

    def start(self):
        self.command("trigger")
        self.command("confirm")

    def approve(self, branch, expected=200, **overrides):
        fields = {
            "proposal": self.state["branches"][branch].get("id"),
            "role": scenario.ROLES[branch], "decision": "approve",
            **overrides,
        }
        return self.command("review", expected, branch=branch, **fields)

    def bay(self, target):
        return next(item for item in self.state["bays"] if item["id"] == target)

    def test_landing_dashboard_routes_and_local_assets(self):
        pages = {
            "/": ('href="/fleet"', 'href="/resources"', 'id="home-title"'),
            "/fleet": ('id="subtabs"', 'id="operation"', 'id="audit-dialog"'),
            "/resources": ('id="subtabs"', 'id="operation"', 'id="audit-dialog"'),
        }
        for path, markers in pages.items():
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 200)
                for marker in markers:
                    self.assertIn(marker, response.text)

        for name in ("campus-parking-map.webp", "resource-library.webp", "campusflow-icon.png"):
            with self.subTest(asset=name):
                response = self.client.get(f"/static/{name}")
                self.assertEqual(response.status_code, 200)
                self.assertTrue(response.headers["content-type"].startswith("image/"))

    def test_primary_recovery_and_reset(self):
        self.start()
        self.assertEqual(self.bay("B-03")["vehicle"], "BIKE-014")
        for target in ("C-04", "C-05", "OV-01"):
            self.assertIsNone(self.bay(target)["vehicle"])
        self.approve("parking")
        self.assertEqual(self.bay("OV-01")["vehicle"], "CAR-078")
        self.command("exit")
        self.assertIsNone(self.bay("C-01")["vehicle"])
        revoked = self.state["branches"]["room"]["id"]
        self.command("occupied")
        self.approve("room", 409, proposal=revoked)
        self.assertEqual(self.state["room"]["devices"], scenario.ACTIVE)
        self.assertEqual(self.state["branches"]["parking"]["status"], "verified")
        self.command("vacant")
        self.assertNotEqual(self.state["branches"]["room"]["id"], revoked)
        self.approve("room")
        self.assertEqual(self.state["room"]["devices"], scenario.STANDBY)
        self.assertTrue({"Pending standby blocked", "OV-01 readback verified",
                         "C-101 device readback verified"} <= {item["title"] for item in self.state["audit"]})
        old_id = self.state["id"]
        self.command("reset")
        self.assertNotEqual(self.state["id"], old_id)
        self.assertEqual(self.state["phase"], "baseline")
        self.assertEqual(self.state["room"]["devices"], scenario.ACTIVE)
        self.assertFalse(self.state["audit"])
        stale = self.client.post("/api/command", json={"run_id": old_id, "action": "trigger"})
        self.assertEqual(stale.status_code, 409)

    def test_role_rejection_and_duplicate_command(self):
        self.start()
        self.approve("parking", 409, role=scenario.ROLES["room"])
        self.assertIsNone(self.bay("OV-01")["vehicle"])
        self.approve("parking", decision="reject")
        self.approve("parking", 409)
        self.assertIsNone(self.bay("OV-01")["vehicle"])
        self.command("exit")
        before = self.state
        self.command("exit")
        self.assertEqual(self.state, before)
        self.assertEqual(self.state["branches"]["parking"]["status"], "rejected")

    def test_two_concurrent_approvals_create_one_assignment(self):
        self.start()
        data = {"action": "review", "run_id": self.state["id"], "branch": "parking",
                "role": scenario.ROLES["parking"], "decision": "approve",
                "proposal": self.state["branches"]["parking"]["id"]}
        with ThreadPoolExecutor(max_workers=2) as workers:
            replies = list(workers.map(lambda _: self.client.post("/api/command", json=data), range(2)))
        self.assertEqual(sorted(reply.status_code for reply in replies), [200, 409])
        self.state = self.client.get("/api/state").json()
        self.assertEqual(self.bay("OV-01")["vehicle"], "CAR-078")
        self.assertEqual(sum(item["title"] == "OV-01 readback verified" for item in self.state["audit"]), 1)

    def test_expiry_preserves_assignment_until_confirmed_exit(self):
        self.start()
        self.approve("parking")
        self.command("expire")
        self.assertEqual(self.bay("OV-01")["vehicle"], "CAR-078")
        self.command("exit_overflow")
        self.assertIsNone(self.bay("OV-01")["vehicle"])
        log_size = len(self.state["audit"])
        self.command("exit_overflow")
        self.assertEqual(len(self.state["audit"]), log_size)

    def test_expiry_prevents_pending_overflow(self):
        self.start()
        token = self.state["branches"]["parking"]["id"]
        self.command("expire")
        self.approve("parking", 409, proposal=token)
        self.assertEqual(self.state["branches"]["parking"]["status"], "held")
        self.assertIsNone(self.bay("OV-01")["vehicle"])

    def test_stale_counts_and_manual_hold_cannot_turn_devices_off(self):
        self.start()
        token = self.state["branches"]["room"]["id"]
        self.command("stale")
        self.approve("room", 409, proposal=token)
        self.command("override")
        self.command("vacant")
        self.assertIn("manual hold", self.state["branches"]["room"]["detail"])
        self.assertEqual(self.state["room"]["devices"], scenario.ACTIVE)
        self.command("override")
        self.approve("room")
        self.assertEqual(self.state["room"]["devices"], scenario.STANDBY)

    def test_regular_capacity_can_replan_pending_overflow(self):
        self.start()
        token = self.state["branches"]["parking"]["id"]
        self.command("exit")
        self.assertEqual(self.bay("C-01")["vehicle"], "CAR-078")
        self.assertEqual(self.state["branches"]["parking"]["status"], "verified")
        self.approve("parking", 409, proposal=token)
        self.assertIsNone(self.bay("OV-01")["vehicle"])

    def test_model_failure_holds_for_manual_lookup(self):
        self.command("trigger")
        result = agent.clarification("Model timeout. Coordinator confirmation required.")
        with patch.object(agent, "select_tool", return_value=result):
            self.command("run")
        self.assertEqual(self.state["phase"], "clarification")
        self.assertIsNone(self.bay("OV-01")["vehicle"])
        self.command("confirm")
        self.assertEqual(self.state["phase"], "active")
        self.assertEqual(self.state["intake"]["mode"], "manual")

    def test_readback_failure_rolls_back_assignment_and_audit(self):
        self.start()
        old_state = self.state
        with patch.object(scenario, "verify", side_effect=scenario.ScenarioError("Readback failed.")):
            self.approve("parking", 409)
        self.assertEqual(self.client.get("/api/state").json(), old_state)

    def test_sample_equipment_checkout_and_return(self):
        self.command("checkout_kit")
        self.assertEqual(self.state["equipment"]["available"], 3)
        self.command("checkout_kit", 409)
        self.command("return_kit")
        self.assertEqual(self.state["equipment"]["available"], 4)
        self.assertFalse(self.state["equipment"]["checked_out"])

    def test_invalid_command_is_rejected(self):
        self.command("trigger", 422, unsafe_extra_field=True)


class AgentToolTest(TestCase):
    def test_accepts_only_allowlisted_tools_and_exact_fixture_id(self):
        lookup = {"type": "function_call", "name": "lookup_session",
                  "arguments": {"session_id": scenario.SESSION_ID}}
        clarify = {"type": "function_call", "name": "request_clarification", "arguments": {}}
        self.assertEqual(agent.validate_selection({"steps": [lookup]})["mode"], "model")
        self.assertEqual(agent.validate_selection({"steps": [clarify]})["mode"], "clarification")
        for bad in (
            {"steps": [lookup, clarify]}, {"steps": []}, {"steps": None},
            {"steps": [{**lookup, "name": "set_lights"}]},
            {"steps": [{**lookup, "arguments": {"session_id": "UNVERIFIED"}}]},
        ):
            with self.subTest(response=bad), self.assertRaises(ValueError):
                agent.validate_selection(bad)


if __name__ == "__main__":
    main()
