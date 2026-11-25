"""Unit tests for the Classroom C-101 CCTV endpoints and concurrent IP Webcam torch control."""

import threading
from unittest import TestCase, main
from unittest.mock import MagicMock, patch
from urllib.error import URLError

from fastapi.testclient import TestClient

from prototype.app import create_app
from prototype.cctv_stream import (
    ClassroomCCTVEngine,
    DebouncedOccupancy,
    TORCH_DEVICES,
    TORCH_TIMEOUT_SECONDS,
)

SANJANA_ON = "http://10.110.21.198:8080/enabletorch"
SANJANA_OFF = "http://10.110.21.198:8080/disabletorch"
ANI_ON = "http://10.100.36.157:8080/enabletorch"
ANI_OFF = "http://10.100.36.157:8080/disabletorch"


class FakeCctvEngine:
    def __init__(self):
        self.active = False
        self.source = "http://10.110.18.80:4747/video"
        self.occ = DebouncedOccupancy(hold_seconds=3.0)
        self.lights_on = False
        self.manual_override = None

    def start(self, source="http://10.110.18.80:4747/video", hold_seconds=3.0):
        self.active = True
        self.source = source
        self.occ = DebouncedOccupancy(hold_seconds=hold_seconds)
        return self.status()

    def stop(self):
        self.active = False
        return self.status()

    def set_manual_override(self, mode="toggle"):
        if mode == "toggle":
            self.lights_on = not self.lights_on
            self.manual_override = "on" if self.lights_on else "off"
        elif mode == "on":
            self.lights_on = True
            self.manual_override = "on"
        elif mode == "off":
            self.lights_on = False
            self.manual_override = "off"
        else:
            self.manual_override = None
        return self.status()

    def clear_events(self):
        return self.status()

    def mjpeg_frames(self):
        yield b"--frame\r\nContent-Type: image/jpeg\r\n\r\n\xff\xd8FAKE\xff\xd9\r\n"

    def status(self):
        return {
            "active": self.active,
            "connecting": False,
            "has_frame": self.active,
            "source": self.source,
            "backend": "droidcam-mjpeg" if self.active else "idle",
            "state": self.occ.state,
            "lights_on": self.lights_on,
            "manual_override": self.manual_override,
            "person_count": self.occ.person_count,
            "confidence": self.occ.confidence,
            "hold_seconds": self.occ.hold_seconds,
            "hold_remaining": 0.0,
            "fps": 14.0 if self.active else 0.0,
            "infer_ms": 28.0 if self.active else 0.0,
            "devices": self.occ.devices(lights_on=self.lights_on),
            "torch_devices": [{"name": name, "url": url} for name, url in TORCH_DEVICES],
            "status_message": self.occ.status_message(
                self.active, self.active, self.manual_override, lights_on=self.lights_on
            ),
            "error": None,
            "events": [],
        }


def _join_torch_threads(engine: ClassroomCCTVEngine, timeout: float = 2.0) -> None:
    for th in list(engine._last_torch_threads):
        th.join(timeout=timeout)


class CctvTest(TestCase):
    def test_debounced_occupancy_messages_and_devices(self):
        now = [100.0]
        occ = DebouncedOccupancy(hold_seconds=3.0, clock=lambda: now[0])

        self.assertEqual(occ.state, "EMPTY")
        self.assertEqual(occ.devices(lights_on=False), {"Lights": "Off", "Fans": "Off", "Projector": "Off"})
        self.assertEqual(occ.status_message(True, True, lights_on=False), "Class empty — Lights Off, Fans Off, Projector Off")

        # Person enters while lights are OFF -> OCCUPIED, but lights stay OFF (no auto turn-on)
        occ.update(1, 0.88)
        self.assertEqual(occ.state, "OCCUPIED")
        self.assertEqual(occ.devices(lights_on=False), {"Lights": "Off", "Fans": "Off", "Projector": "Off"})
        self.assertIn("no auto turn-on", occ.status_message(True, True, lights_on=False))

        # When lights are ON and person leaves briefly (1.5s < 3.0s hold) -> still OCCUPIED, countdown shown
        now[0] += 1.5
        occ.update(0, 0.0)
        self.assertEqual(occ.state, "OCCUPIED")
        self.assertIn("turning lights off", occ.status_message(True, True, lights_on=True))

        # Full 3.0s empty -> EMPTY
        now[0] += 3.0
        occ.update(0, 0.0)
        self.assertEqual(occ.state, "EMPTY")
        self.assertEqual(occ.devices(lights_on=False), {"Lights": "Off", "Fans": "Off", "Projector": "Off"})

    def test_override_toggles_both_torches_concurrently_with_timeout(self):
        calls: list[tuple[str, float]] = []
        calls_lock = threading.Lock()
        barrier = threading.Barrier(2, timeout=2.0)

        def concurrent_urlopen(req, timeout=None):
            # Barrier proves both Sanjana and Ani HTTP calls execute concurrently in separate threads.
            barrier.wait()
            with calls_lock:
                calls.append((req.full_url, timeout))
            resp = MagicMock()
            resp.__enter__.return_value = resp
            resp.read.return_value = b"ok"
            return resp

        engine = ClassroomCCTVEngine()
        with patch("prototype.cctv_stream.urlopen", side_effect=concurrent_urlopen):
            with TestClient(create_app(cctv_engine=engine)) as client:
                # 1st Override click -> toggles OFF -> ON and fires /enabletorch to both phones concurrently
                res_on = client.post("/api/cctv/override", json={"mode": "toggle"})
                self.assertEqual(res_on.status_code, 200)
                body_on = res_on.json()
                self.assertTrue(body_on["lights_on"])
                self.assertEqual(body_on["devices"], {"Lights": "On", "Fans": "On", "Projector": "On"})
                _join_torch_threads(engine)

                self.assertEqual({url for url, _ in calls}, {SANJANA_ON, ANI_ON})
                self.assertTrue(all(t == TORCH_TIMEOUT_SECONDS for _, t in calls))

                # 2nd Override click (even with empty body) -> toggles ON -> OFF and fires /disabletorch concurrently
                calls.clear()
                barrier.reset()
                res_off = client.post("/api/cctv/override")
                self.assertEqual(res_off.status_code, 200)
                body_off = res_off.json()
                self.assertFalse(body_off["lights_on"])
                self.assertEqual(body_off["devices"], {"Lights": "Off", "Fans": "Off", "Projector": "Off"})
                _join_torch_threads(engine)

                self.assertEqual({url for url, _ in calls}, {SANJANA_OFF, ANI_OFF})
                self.assertTrue(all(t == TORCH_TIMEOUT_SECONDS for _, t in calls))

                # Incident log clear endpoint empties RAM events cleanly
                self.assertGreater(len(body_off["events"]), 0)
                cleared = client.post("/api/cctv/events/clear")
                self.assertEqual(cleared.status_code, 200)
                self.assertEqual(cleared.json()["events"], [])

    def test_no_auto_on_when_student_appears_and_auto_off_when_student_leaves(self):
        now = [100.0]
        calls: list[tuple[str, float]] = []
        calls_lock = threading.Lock()

        def fake_requester(url: str, timeout: float):
            with calls_lock:
                calls.append((url, timeout))

        engine = ClassroomCCTVEngine(
            hold_seconds=3.0,
            clock=lambda: now[0],
            torch_requester=fake_requester,
        )

        # Rule 3: Lights start OFF; student enters -> OCCUPIED, lights stay OFF, ZERO HTTP requests sent
        state, _, lights = engine.process_detection(1, 0.92)
        self.assertEqual(state, "OCCUPIED")
        self.assertFalse(lights)
        self.assertEqual(calls, [])

        # Student leaves while lights are still OFF -> EMPTY, still ZERO HTTP requests sent
        now[0] += 0.5
        engine.process_detection(0, 0.0)
        now[0] += 3.1
        state, _, lights = engine.process_detection(0, 0.0)
        self.assertEqual(state, "EMPTY")
        self.assertFalse(lights)
        self.assertEqual(calls, [])

        # Rule 1: Override turns lights ON -> sends /enabletorch to both phones
        engine.set_manual_override("toggle")
        _join_torch_threads(engine)
        self.assertTrue(engine.status()["lights_on"])
        self.assertEqual({u for u, _ in calls}, {SANJANA_ON, ANI_ON})
        calls.clear()

        # Student sits in classroom while lights are ON -> stays ON, no extra torch calls
        now[0] += 1.0
        state, _, lights = engine.process_detection(1, 0.89)
        self.assertEqual(state, "OCCUPIED")
        self.assertTrue(lights)
        self.assertEqual(calls, [])

        # Student briefly steps out (1.5s < 3.0s hold) -> lights stay ON, no /disabletorch yet
        now[0] += 1.5
        state, _, lights = engine.process_detection(0, 0.0)
        self.assertEqual(state, "OCCUPIED")
        self.assertTrue(lights)
        self.assertEqual(calls, [])

        # Rule 2: Student gone past 3.0s hold timer -> lights flip OFF and /disabletorch sent to BOTH phones
        now[0] += 3.0
        state, _, lights = engine.process_detection(0, 0.0)
        _join_torch_threads(engine)
        self.assertEqual(state, "EMPTY")
        self.assertFalse(lights)
        self.assertEqual(engine.status()["devices"], {"Lights": "Off", "Fans": "Off", "Projector": "Off"})
        self.assertEqual({u for u, _ in calls}, {SANJANA_OFF, ANI_OFF})
        self.assertTrue(all(t == 1.5 for _, t in calls))

    def test_fault_tolerant_dispatch_ignores_unreachable_phone(self):
        reached: list[str] = []
        lock = threading.Lock()

        def flaky_requester(url: str, timeout: float):
            if "10.110.21.198" in url:
                raise URLError("Phone 2 unreachable")
            with lock:
                reached.append(url)

        engine = ClassroomCCTVEngine(torch_requester=flaky_requester)
        status = engine.set_manual_override("on")
        _join_torch_threads(engine)

        self.assertTrue(status["lights_on"])
        self.assertEqual(reached, [ANI_ON])

        # Even if both fail, engine does not raise
        def all_fail(url: str, timeout: float):
            raise TimeoutError("timed out")

        engine2 = ClassroomCCTVEngine(torch_requester=all_fail)
        status2 = engine2.set_manual_override("on")
        _join_torch_threads(engine2)
        self.assertTrue(status2["lights_on"])

    def test_cctv_start_status_stream_override_and_stop(self):
        fake = FakeCctvEngine()
        with TestClient(create_app(cctv_engine=fake)) as client:
            s0 = client.get("/api/cctv/status").json()
            self.assertFalse(s0["active"])
            self.assertFalse(s0["lights_on"])
            self.assertEqual(client.get("/api/cctv/stream").status_code, 409)

            # Dual-action Override toggles ON and OFF even before CCTV is started
            ov_on = client.post("/api/cctv/override", json={"mode": "toggle"}).json()
            self.assertTrue(ov_on["lights_on"])
            self.assertEqual(ov_on["devices"], {"Lights": "On", "Fans": "On", "Projector": "On"})
            ov_off = client.post("/api/cctv/override", json={"mode": "toggle"}).json()
            self.assertFalse(ov_off["lights_on"])
            self.assertEqual(ov_off["devices"], {"Lights": "Off", "Fans": "Off", "Projector": "Off"})

            started = client.post("/api/cctv/start", json={"source": "http://10.110.18.80:4747/video"})
            self.assertEqual(started.status_code, 200)
            self.assertTrue(started.json()["active"])

            # Student detected while lights OFF -> OCCUPIED, devices stay Off
            fake.occ.update(2, 0.91)
            s1 = client.get("/api/cctv/status").json()
            self.assertEqual(s1["person_count"], 2)
            self.assertEqual(s1["devices"], {"Lights": "Off", "Fans": "Off", "Projector": "Off"})

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
            self.assertEqual(client.post("/api/cctv/override", json={"mode": "toggle"}).status_code, 404)
            self.assertEqual(client.post("/api/cctv/events/clear").status_code, 404)


if __name__ == "__main__":
    main()
