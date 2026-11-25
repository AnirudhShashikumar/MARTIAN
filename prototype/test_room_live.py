"""Regression tests for live AMB82 telemetry, tiered room policy, and Android WebSocket ACK."""

from unittest import TestCase, main

from fastapi.testclient import TestClient

from prototype import amb82_serial_bridge
from prototype.app import create_app


class FakeClock:
    def __init__(self, start=1000.0):
        self.t = float(start)

    def __call__(self):
        return self.t

    def advance(self, seconds):
        self.t += float(seconds)


class RoomLiveTest(TestCase):
    def setUp(self):
        self.clock = FakeClock()
        client = TestClient(create_app(room_clock=self.clock))
        self.client = client.__enter__()
        self.addCleanup(client.__exit__, None, None, None)

    def send_frame(self, count, conf=0.95, source="amb82-npu"):
        reply = self.client.post(
            "/api/room/telemetry",
            json={"person_count": count, "confidence": conf, "source": source},
        )
        self.assertEqual(reply.status_code, 200, reply.text)
        return reply.json()

    def test_tiered_unscheduled_auto_off_projector_approval_and_ws_ack(self):
        with self.client.websocket_connect("/ws/room-panel?role=phone") as ws:
            init = ws.receive_json()
            self.assertEqual(init["type"], "snapshot")
            self.assertEqual(init["state"]["connected_phones"], 1)

            # Start vacancy countdown (unscheduled by default)
            s1 = self.send_frame(0)
            self.assertEqual(s1["status"], "counting_vacant")
            self.assertEqual(s1["devices"], {"Lights": "On", "Fans": "On", "Projector": "On"})
            ws.receive_json()  # snapshot broadcast

            # Advance 15s -> Tier 1 auto-off Lights & Fans, Tier 2 proposal for Projector Standby
            self.clock.advance(15.0)
            s2 = self.send_frame(0)
            self.assertEqual(s2["devices"], {"Lights": "Off", "Fans": "Off", "Projector": "On"})
            self.assertIsNotNone(s2["pending_proposal"])
            self.assertEqual(s2["pending_proposal"]["scope"], "projector_standby")

            cmd = ws.receive_json()
            self.assertEqual(cmd["type"], "command")
            self.assertEqual(cmd["tier"], "tier1_auto_off")
            self.assertEqual(cmd["devices"], {"Lights": "Off", "Fans": "Off", "Projector": "On"})
            ws.receive_json()  # snapshot broadcast

            # Phone sends closed-loop ACK
            ws.send_json({"type": "ack", "cmd_id": cmd["cmd_id"], "devices": cmd["devices"]})
            ack_snap = ws.receive_json()
            self.assertTrue(ack_snap["state"]["last_ack"]["verified"])

            # Facilities approves Tier 2 Projector Standby
            pid = s2["pending_proposal"]["id"]
            approved = self.client.post(
                "/api/room/review",
                json={"proposal_id": pid, "decision": "approve"},
            )
            self.assertEqual(approved.status_code, 200, approved.text)
            self.assertEqual(approved.json()["devices"]["Projector"], "Standby")

            cmd2 = ws.receive_json()
            self.assertEqual(cmd2["type"], "command")
            self.assertEqual(cmd2["devices"]["Projector"], "Standby")
            ws.receive_json()

            # Auto-wake Lights & Fans after 2 occupied frames
            self.clock.advance(1.0)
            self.send_frame(1)
            ws.receive_json()
            self.clock.advance(1.0)
            woke = self.send_frame(1)
            self.assertEqual(woke["devices"]["Lights"], "On")
            self.assertEqual(woke["devices"]["Fans"], "On")
            wake_cmd = ws.receive_json()
            self.assertEqual(wake_cmd["tier"], "auto_wake")

    def test_mid_schedule_blocks_auto_off_and_stale_approval_recheck(self):
        # Switch to mid-schedule (class booked)
        sched = self.client.post("/api/room/schedule", json={"class_scheduled": True})
        self.assertEqual(sched.status_code, 200)

        self.send_frame(0)
        self.clock.advance(16.0)
        s = self.send_frame(0)

        # Mid-schedule MUST NOT auto-turn off lights/fans
        self.assertEqual(s["devices"], {"Lights": "On", "Fans": "On", "Projector": "On"})
        self.assertIsNotNone(s["pending_proposal"])
        self.assertEqual(s["pending_proposal"]["scope"], "mid_schedule_shutdown")
        stale_token = s["pending_proposal"]["id"]

        # Someone enters right before Facilities clicks Approve
        self.clock.advance(1.0)
        self.send_frame(1)

        # Stale approval MUST be rejected (409) and devices stay On
        rejected = self.client.post(
            "/api/room/review",
            json={"proposal_id": stale_token, "decision": "approve"},
        )
        self.assertEqual(rejected.status_code, 409)
        live = self.client.get("/api/room/live").json()
        self.assertEqual(live["devices"], {"Lights": "On", "Fans": "On", "Projector": "On"})

    def test_phone_wall_override_blocks_shutdown_and_restores(self):
        with self.client.websocket_connect("/ws/room-panel?role=phone") as ws:
            ws.receive_json()
            self.send_frame(0)
            ws.receive_json()
            self.clock.advance(15.0)
            s = self.send_frame(0)
            ws.receive_json()  # tier1 command
            ws.receive_json()  # snapshot
            pid = s["pending_proposal"]["id"]

            # Phone flips Wall Manual Override ON
            ws.send_json({"type": "wall_override", "active": True})
            cmd = ws.receive_json()
            self.assertEqual(cmd["type"], "command")
            self.assertEqual(cmd["devices"], {"Lights": "On", "Fans": "On", "Projector": "On"})
            snap = ws.receive_json()
            self.assertTrue(snap["state"]["wall_override"])
            self.assertIsNone(snap["state"]["pending_proposal"])

            # Previously staged proposal is now blocked
            res = self.client.post("/api/room/review", json={"proposal_id": pid, "decision": "approve"})
            self.assertEqual(res.status_code, 409)

    def test_low_confidence_and_stale_feed_fail_safe_hold(self):
        self.send_frame(0, conf=0.35)
        live = self.client.get("/api/room/live").json()
        self.assertEqual(live["status"], "fail_safe_hold")
        self.assertEqual(live["devices"], {"Lights": "On", "Fans": "On", "Projector": "On"})

        # Fresh vacant -> wait until stale (>5s) -> approval blocked
        self.send_frame(0, conf=0.95)
        self.clock.advance(15.0)
        s = self.send_frame(0, conf=0.95)
        pid = s["pending_proposal"]["id"]
        self.clock.advance(6.0)  # feed now stale!
        res = self.client.post("/api/room/review", json={"proposal_id": pid, "decision": "approve"})
        self.assertEqual(res.status_code, 409)

    def test_serial_bridge_parser(self):
        self.assertEqual(
            amb82_serial_bridge.parse_serial_line('{"room":"C-101","person_count":2,"confidence":0.89,"source":"amb82-npu"}'),
            (2, 0.89, "amb82-npu"),
        )
        self.assertEqual(
            amb82_serial_bridge.parse_serial_line("person_count=0 conf=0.95"),
            (0, 0.95, "amb82-npu"),
        )
        self.assertIsNone(amb82_serial_bridge.parse_serial_line("booting ameba..."))


if __name__ == "__main__":
    main()
