"""Unit tests for the Classroom C-101 web-embedded DroidCam + YOLOv8 CCTV endpoints."""

from unittest import TestCase, main

from fastapi.testclient import TestClient

from prototype.app import create_app
from prototype.cctv_stream import DebouncedOccupancy


class FakeCctvEngine:
    def __init__(self):
        self.active = False
        self.source = "http://10.110.18.80:4747/video"
        self.occ = DebouncedOccupancy(hold_seconds=3.0)
        self.manual_override = None

    def start(self, source="http://10.110.18.80:4747/video", hold_seconds=3.0):
        self.active = True
        self.source = source
        self.occ = DebouncedOccupancy(hold_seconds=hold_seconds)
        return self.status()

    def stop(self):
        self.active = False
        return self.status()

    def set_manual_override(self, mode):
        self.manual_override = None if mode == "auto" else mode
        return self.status()

    def mjpeg_frames(self):
        yield b"--frame\r\nContent-Type: image/jpeg\r\n\r\n\xff\xd8FAKE\xff\xd9\r\n"

    def status(self):
        devices = (
            {"Lights": "On", "Fans": "On", "Projector": "On"} if self.manual_override == "on"
            else ({"Lights": "Off", "Fans": "Off", "Projector": "Off"} if self.manual_override == "off" else self.occ.devices())
        )
        return {
            "active": self.active,
            "connecting": False,
            "has_frame": self.active,
            "source": self.source,
            "backend": "droidcam-mjpeg" if self.active else "idle",
            "state": self.occ.state,
            "manual_override": self.manual_override,
            "person_count": self.occ.person_count,
            "confidence": self.occ.confidence,
            "hold_seconds": self.occ.hold_seconds,
            "hold_remaining": 0.0,
            "fps": 14.0 if self.active else 0.0,
            "infer_ms": 28.0 if self.active else 0.0,
            "devices": devices,
            "status_message": self.occ.status_message(self.active, self.active, self.manual_override),
            "error": None,
            "events": [],
        }


class CctvTest(TestCase):
    def test_debounced_occupancy_messages_and_devices(self):
        now = [100.0]
        occ = DebouncedOccupancy(hold_seconds=3.0, clock=lambda: now[0])

        self.assertEqual(occ.state, "EMPTY")
        self.assertEqual(occ.devices(), {"Lights": "Off", "Fans": "Off", "Projector": "Off"})
        self.assertEqual(occ.status_message(True, True), "Class empty — Lights Off, Fans Off, Projector Off")

        # Person enters -> instant OCCUPIED + all appliances ON
        occ.update(1, 0.88)
        self.assertEqual(occ.state, "OCCUPIED")
        self.assertEqual(occ.devices(), {"Lights": "On", "Fans": "On", "Projector": "On"})
        self.assertEqual(occ.status_message(True, True), "Person detected — Lights On, Fans On, Projector On")

        # Brief 1.5s exit does not turn off lights
        now[0] += 1.5
        occ.update(0, 0.0)
        self.assertEqual(occ.state, "OCCUPIED")
        self.assertIn("verifying empty", occ.status_message(True, True))

        # Full 3.0s empty -> Class empty — Lights Off, Fans Off, Projector Off
        now[0] += 3.0
        occ.update(0, 0.0)
        self.assertEqual(occ.state, "EMPTY")
        self.assertEqual(occ.devices(), {"Lights": "Off", "Fans": "Off", "Projector": "Off"})
        self.assertEqual(occ.status_message(True, True), "Class empty — Lights Off, Fans Off, Projector Off")

    def test_cctv_start_status_stream_override_and_stop(self):
        fake = FakeCctvEngine()
        with TestClient(create_app(cctv_engine=fake)) as client:
            s0 = client.get("/api/cctv/status").json()
            self.assertFalse(s0["active"])
            self.assertEqual(client.get("/api/cctv/stream").status_code, 409)

            # Manual override works even before CCTV is started
            ov_on = client.post("/api/cctv/override", json={"mode": "on"}).json()
            self.assertEqual(ov_on["devices"], {"Lights": "On", "Fans": "On", "Projector": "On"})
            ov_off = client.post("/api/cctv/override", json={"mode": "off"}).json()
            self.assertEqual(ov_off["devices"], {"Lights": "Off", "Fans": "Off", "Projector": "Off"})
            client.post("/api/cctv/override", json={"mode": "auto"})

            started = client.post("/api/cctv/start", json={"source": "http://10.110.18.80:4747/video"})
            self.assertEqual(started.status_code, 200)
            self.assertTrue(started.json()["active"])

            fake.occ.update(2, 0.91)
            s1 = client.get("/api/cctv/status").json()
            self.assertEqual(s1["person_count"], 2)
            self.assertEqual(s1["devices"], {"Lights": "On", "Fans": "On", "Projector": "On"})
            self.assertEqual(s1["status_message"], "Person detected — Lights On, Fans On, Projector On")

            stream_res = client.get("/api/cctv/stream")
            self.assertEqual(stream_res.status_code, 200)
            self.assertIn("multipart/x-mixed-replace", stream_res.headers["content-type"])
            self.assertIn(b"\xff\xd8FAKE\xff\xd9", stream_res.content)

            stopped = client.post("/api/cctv/stop")
            self.assertEqual(stopped.status_code, 200)
            self.assertFalse(stopped.json()["active"])

    def test_hosted_mode_disables_cctv_endpoints(self):
        with TestClient(create_app(hosted=True, database_url="")) as client:
            self.assertEqual(client.get("/api/cctv/status").status_code, 404)
            self.assertEqual(client.post("/api/cctv/start", json={}).status_code, 404)


if __name__ == "__main__":
    main()
