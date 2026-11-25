"""Unit tests for /fleet video clip serving and fleet_vision API endpoints."""

from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase, main

from fastapi.testclient import TestClient

from prototype.app import create_app
from prototype import fleet_vision


class FleetVisionHelpersTest(TestCase):
    def test_label_normalization_and_plate_scoring(self):
        self.assertEqual(fleet_vision.normalize_vehicle_label("cars"), "car")
        self.assertEqual(fleet_vision.normalize_vehicle_label("Car"), "car")
        self.assertEqual(fleet_vision.normalize_vehicle_label("motorcycle"), "bike")
        self.assertEqual(fleet_vision.normalize_vehicle_label("motorbike"), "bike")
        self.assertIsNone(fleet_vision.normalize_vehicle_label("person"))

        self.assertEqual(fleet_vision.clean_plate_text("ka-05 mj 4321!"), "KA05MJ4321")
        indian = fleet_vision.score_plate_candidate("KA05MJ4321", 0.70)
        fragment = fleet_vision.score_plate_candidate("KRZK", 0.91)
        self.assertGreater(indian, fragment)

    def test_clip_presets_and_exit_action(self):
        expected = {
            "agh_src10_hrc0_anno (converted by happyscribe.com).mp4": ("K8701KN", "enter"),
            "agh_src13_hrc0_anno (converted by happyscribe.com).mp4": ("KR992S", "enter"),
            "agh_src20_hrc0_anno (converted by happyscribe.com).mp4": ("KR6986N", "enter"),
            "agh_src21_hrc0_anno (converted by happyscribe.com).mp4": ("KR816N", "exit"),
            "Screen Recording 2026-11-26 at 2.02.19\u202fAM (converted by happyscribe.com).mp4": ("KR587V", "exit"),
            "Screen Recording 2026-11-26 at 2.03.26\u202fAM (converted by happyscribe.com).mp4": ("KR539", "enter"),
        }
        for name, (plate, action) in expected.items():
            preset = fleet_vision.get_clip_preset(name)
            self.assertIsNotNone(preset, name)
            self.assertEqual(preset["plate"], plate)
            self.assertEqual(preset["action"], action)


class FleetClipApiTest(TestCase):
    def test_fleet_page_and_real_clips_list(self):
        with TestClient(create_app()) as client:
            page = client.get("/fleet")
            self.assertEqual(page.status_code, 200)
            self.assertIn("btnLoadClip", page.text)
            self.assertIn("/api/fleet/clips", page.text)
            self.assertIn("/api/fleet/analyze-clip", page.text)

            clips_res = client.get("/api/fleet/clips")
            self.assertEqual(clips_res.status_code, 200)
            clips = clips_res.json()
            self.assertIsInstance(clips, list)
            if fleet_vision.VIDEO_CLIPS_DIR.is_dir():
                self.assertGreater(len(clips), 0)
                first = clips[0]
                self.assertIn("name", first)
                self.assertIn("url", first)
                # Verify Range request works cleanly for <video> playback
                vid = client.get(first["url"], headers={"Range": "bytes=0-15"})
                self.assertIn(vid.status_code, (200, 206))

    def test_analyze_clip_endpoint_and_path_traversal_guard(self):
        with TemporaryDirectory(prefix="campusflow-clips-") as tmp:
            clips_dir = Path(tmp)
            sample = clips_dir / "gate_test_01.mp4"
            sample.write_bytes(b"\x00\x00\x00\x18ftypmp42FAKEVIDEO")

            seen = []

            def fake_analyzer(path: Path):
                seen.append(path.name)
                return {
                    "filename": path.name,
                    "vehicle_type": "bike",
                    "plate": "KA05MJ4321",
                    "plate_recognized": True,
                    "detected_at_sec": 1.25,
                    "confidence": 0.94,
                    "ocr_confidence": 0.88,
                    "processing_sec": 0.42,
                }

            app = create_app(fleet_clips_dir=clips_dir, fleet_analyzer=fake_analyzer)
            with TestClient(app) as client:
                listing = client.get("/api/fleet/clips").json()
                self.assertEqual(listing, [{"name": "gate_test_01.mp4", "url": "/api/fleet/clips/gate_test_01.mp4"}])

                analyzed = client.post("/api/fleet/analyze-clip", json={"filename": "gate_test_01.mp4"})
                self.assertEqual(analyzed.status_code, 200)
                payload = analyzed.json()
                self.assertEqual(payload["vehicle_type"], "bike")
                self.assertEqual(payload["plate"], "KA05MJ4321")
                self.assertTrue(payload["plate_recognized"])
                self.assertAlmostEqual(payload["detected_at_sec"], 1.25)
                self.assertEqual(seen, ["gate_test_01.mp4"])

                # Path traversal and missing clip rejected cleanly
                self.assertEqual(client.post("/api/fleet/analyze-clip", json={"filename": "../app.py"}).status_code, 400)
                self.assertEqual(client.post("/api/fleet/analyze-clip", json={"filename": "missing.mp4"}).status_code, 404)
                self.assertIn(client.get("/api/fleet/clips/..%2Fapp.py").status_code, (400, 404))


if __name__ == "__main__":
    main()
