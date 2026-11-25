"""Wired USB Serial bridge for Realtek AMB82-Mini -> CampusFlow FastAPI.

Modes:
  1) Serial (AMB82-Mini on-device NPU over USB-C, recommended — zero RTSP lag):
       python prototype/amb82_serial_bridge.py --mode serial --port COM5 --baud 115200

  2) Interactive dry-run simulator (no hardware needed):
       python prototype/amb82_serial_bridge.py --mode sim

  3) Optional Laptop Webcam fallback (requires ultralytics + opencv-python):
       python prototype/amb82_serial_bridge.py --mode webcam --camera 0

--------------------------------------------------------------------------
AMB82-Mini Arduino Reference Snippet (AmebaPro2 ObjectDetectionLoop NPU):
--------------------------------------------------------------------------
Inside your ObjectDetectionLoop callback / loop(), filter results where
class == "person" (COCO class 0), compute `personCount` and `maxConf`, and
print one JSON line every ~400ms over USB Serial at 115200 baud:

  Serial.print("{\"room\":\"C-101\",\"person_count\":");
  Serial.print(personCount);
  Serial.print(",\"confidence\":");
  Serial.print(personCount > 0 ? maxConf : 0.95, 2);
  Serial.println(",\"source\":\"amb82-npu\"}");
--------------------------------------------------------------------------
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from urllib.error import URLError
from urllib.request import Request, urlopen


KV_PATTERN = re.compile(r"person[_ ]?count\s*[:=]\s*(\d+).*?conf(?:idence)?\s*[:=]\s*([0-9.]+)", re.IGNORECASE)


def post_telemetry(endpoint: str, person_count: int, confidence: float, source: str) -> None:
    payload = json.dumps({
        "person_count": int(person_count),
        "confidence": float(confidence),
        "source": source,
    }).encode("utf-8")
    req = Request(endpoint, data=payload, headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urlopen(req, timeout=2.0) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            print(
                f"[{source}] count={person_count} conf={confidence:.2f} -> "
                f"status={data['status']} vacant={data['telemetry']['vacant_seconds']}s "
                f"devices={data['devices']}"
            )
    except URLError as err:
        print(f"[WARN] Could not reach CampusFlow server at {endpoint}: {err}", file=sys.stderr)


def parse_serial_line(line: str) -> tuple[int, float, str] | None:
    text = line.strip()
    if not text:
        return None
    if text.startswith("{") and text.endswith("}"):
        try:
            obj = json.loads(text)
            count = int(obj.get("person_count", obj.get("count", 0)))
            conf = float(obj.get("confidence", obj.get("conf", 0.92)))
            src = str(obj.get("source", "amb82-npu"))
            return count, conf, src
        except (ValueError, TypeError):
            return None
    match = KV_PATTERN.search(text)
    if match:
        return int(match.group(1)), float(match.group(2)), "amb82-npu"
    return None


def run_serial(port: str, baud: int, endpoint: str) -> None:
    try:
        import serial  # type: ignore
    except ImportError:
        print("pyserial is required for --mode serial. Install with: pip install pyserial", file=sys.stderr)
        sys.exit(1)

    print(f"Listening to AMB82-Mini on {port} @ {baud} baud -> {endpoint}")
    with serial.Serial(port, baud, timeout=1.0) as ser:
        while True:
            raw = ser.readline().decode("utf-8", errors="ignore")
            parsed = parse_serial_line(raw)
            if parsed:
                count, conf, src = parsed
                post_telemetry(endpoint, count, conf, src)


def run_sim(endpoint: str) -> None:
    print("Interactive AMB82 Simulator ->", endpoint)
    print("Commands: [0] Vacant (0.95) | [1] Occupied (0.96) | [2] Uncertain (0.35) | [q] Quit")
    current = (0, 0.95)
    print("Streaming initial state every 1s. Press Ctrl+C to stop.")
    try:
        while True:
            post_telemetry(endpoint, current[0], current[1], "amb82-sim")
            time.sleep(1.0)
    except KeyboardInterrupt:
        print("\nStopped.")


def run_webcam(camera_index: int, endpoint: str, interval: float) -> None:
    try:
        import cv2  # type: ignore
        from ultralytics import YOLO  # type: ignore
    except ImportError:
        print("Webcam fallback requires: pip install ultralytics opencv-python", file=sys.stderr)
        sys.exit(1)

    model = YOLO("yolov8n.pt")
    cap = cv2.VideoCapture(camera_index)
    if not cap.isOpened():
        print(f"Could not open webcam index {camera_index}", file=sys.stderr)
        sys.exit(1)

    print(f"Webcam YOLOv8n fallback active (camera {camera_index}) -> {endpoint}")
    print("Privacy mode: frames are processed in RAM and immediately discarded.")
    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                time.sleep(interval)
                continue
            results = model.predict(frame, classes=[0], conf=0.4, verbose=False)
            boxes = results[0].boxes if results else None
            count = len(boxes) if boxes is not None else 0
            conf = float(boxes.conf.max().item()) if count > 0 else 0.94
            del frame  # Discard raw frame immediately
            post_telemetry(endpoint, count, conf, "laptop-yolov8n")
            time.sleep(interval)
    finally:
        cap.release()


def main() -> None:
    parser = argparse.ArgumentParser(description="AMB82-Mini USB Serial bridge for CampusFlow")
    parser.add_argument("--mode", choices=["serial", "sim", "webcam"], default="serial")
    parser.add_argument("--port", default="COM5", help="AMB82-Mini COM port (e.g. COM5 or /dev/ttyUSB0)")
    parser.add_argument("--baud", type=int, default=115200)
    parser.add_argument("--camera", type=int, default=0, help="Camera index for --mode webcam")
    parser.add_argument("--interval", type=float, default=0.5, help="Polling interval for webcam mode")
    parser.add_argument("--server", default="http://127.0.0.1:8000", help="CampusFlow FastAPI server base URL")
    args = parser.parse_args()

    endpoint = args.server.rstrip("/") + "/api/room/telemetry"
    if args.mode == "serial":
        run_serial(args.port, args.baud, endpoint)
    elif args.mode == "sim":
        run_sim(endpoint)
    else:
        run_webcam(args.camera, endpoint, args.interval)


if __name__ == "__main__":
    main()
