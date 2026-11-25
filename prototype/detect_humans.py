"""CampusFlow · Multi-Phone Wireless Classroom Vision & Torch Controller.

Phase 1: Connects to Phone 1 (DroidCam Wi-Fi stream, e.g. http://<PHONE1_IP>:4747/video)
         with a zero-lag latest-frame buffer (CAP_PROP_BUFFERSIZE=1 + background reader),
         plus automatic fallback to DroidCam virtual webcam index or laptop webcam (--source 0).
Phase 2: Runs pretrained Ultralytics yolov8n.pt (class 0 = person only, imgsz=416, conf=0.50)
         strictly in RAM (zero saved frames) and renders a live annotated OpenCV HUD showing
         bounding boxes, person count, hold countdown, FPS, and LIGHTS: ON / OFF.
Phase 3: Triggers Phones 2 & 3 physical Android torches wirelessly ONLY when room state changes
         (OCCUPIED <-> EMPTY), using non-blocking background requests so video never stutters.

Quick Examples (use global python which already has cv2 + ultralytics installed):
  # Phone 1 DroidCam stream + Phones 2 & 3 running IP Webcam (recommended idempotent torch):
  python prototype/detect_humans.py --source http://10.110.18.80:4747/video --torches 192.168.137.102:8080 192.168.137.103:8080

  # Phone 1 DroidCam only (dry-run before adding Phones 2 & 3):
  python prototype/detect_humans.py --source http://10.110.18.80:4747/video

  # Built-in laptop webcam or DroidCam virtual webcam index fallback:
  python prototype/detect_humans.py --source 0

Hotkeys in the live window:
  Q / ESC : Quit cleanly
  M       : Toggle Manual Override (locks LIGHTS: ON)
  T       : Force re-send current torch state to Phones 2 & 3
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass, field
import sys
import threading
import time
from typing import Any, Callable, Optional
from urllib.error import URLError
from urllib.request import Request, urlopen


# =====================================================================
# PHASE 2: DEBOUNCED ROOM OCCUPANCY STATE MACHINE (TESTABLE PURE LOGIC)
# =====================================================================

@dataclass
class DebouncedRoomState:
    hold_seconds: float = 3.0
    clock: Callable[[], float] = time.monotonic

    state: str = "EMPTY"  # "OCCUPIED" | "EMPTY"
    manual_override: bool = False
    empty_since: Optional[float] = None
    last_count: int = 0
    last_conf: float = 0.0

    def lights_on(self) -> bool:
        return self.manual_override or self.state == "OCCUPIED"

    def hold_remaining(self, now: Optional[float] = None) -> float:
        if self.state != "OCCUPIED" or self.empty_since is None or self.manual_override:
            return 0.0
        t = self.clock() if now is None else now
        return max(0.0, self.hold_seconds - (t - self.empty_since))

    def update(self, person_count: int, confidence: float = 0.0) -> tuple[bool, str]:
        """Feed one detection frame. Returns (lights_changed, new_label)."""
        now = self.clock()
        prev_lights = self.lights_on()
        self.last_count = int(person_count)
        self.last_conf = float(confidence)

        if self.last_count >= 1:
            # Flip to OCCUPIED immediately when any person appears
            self.empty_since = None
            self.state = "OCCUPIED"
        else:
            # Wait through hold_seconds with zero detections before flipping to EMPTY
            if self.state == "OCCUPIED":
                if self.empty_since is None:
                    self.empty_since = now
                elif (now - self.empty_since) >= self.hold_seconds:
                    self.state = "EMPTY"
                    self.empty_since = None

        new_lights = self.lights_on()
        return (new_lights != prev_lights), ("OCCUPIED" if new_lights else "EMPTY")

    def toggle_override(self) -> tuple[bool, str]:
        prev_lights = self.lights_on()
        self.manual_override = not self.manual_override
        new_lights = self.lights_on()
        return (new_lights != prev_lights), ("OCCUPIED" if new_lights else "EMPTY")


# =====================================================================
# PHASE 3: WIRELESS TORCH DISPATCHER FOR PHONES 2 & 3
# =====================================================================

def build_torch_url(target: str, turn_on: bool, app_mode: str) -> str:
    base = target.strip().rstrip("/")
    if not base.startswith(("http://", "https://")):
        base = f"http://{base}"
    if app_mode == "ipwebcam":
        return f"{base}/enabletorch" if turn_on else f"{base}/disabletorch"
    if app_mode == "macrodroid":
        return f"{base}/lights_on" if turn_on else f"{base}/lights_off"
    if app_mode == "droidcam":
        return f"{base}/cam/1/led_toggle"
    raise ValueError(f"Unsupported torch app mode: {app_mode}")


@dataclass
class WirelessTorchController:
    targets: list[str]
    app_mode: str = "ipwebcam"
    timeout: float = 2.0
    statuses: dict[str, str] = field(default_factory=dict)
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def __post_init__(self) -> None:
        for t in self.targets:
            self.statuses[t] = "IDLE"

    def set_lights(self, turn_on: bool, reason: str = "") -> None:
        """Fire non-blocking HTTP requests to Phones 2 & 3 on state change."""
        if not self.targets:
            return
        action = "ON" if turn_on else "OFF"
        print(f"[TORCH] State change -> LIGHTS {action} ({reason}) -> {len(self.targets)} phone(s)")
        for target in self.targets:
            threading.Thread(
                target=self._send_one,
                args=(target, turn_on),
                daemon=True,
            ).start()

    def _send_one(self, target: str, turn_on: bool) -> None:
        url = build_torch_url(target, turn_on, self.app_mode)
        t0 = time.perf_counter()
        try:
            req = Request(url, headers={"User-Agent": "CampusFlow-Torch/1.0"})
            with urlopen(req, timeout=self.timeout) as resp:
                code = getattr(resp, "status", 200)
                ms = (time.perf_counter() - t0) * 1000.0
                status = f"{'ON' if turn_on else 'OFF'} OK ({ms:.0f}ms)"
                print(f"  [OK] {target} -> HTTP {code} ({url}) in {ms:.0f}ms")
        except (URLError, OSError) as exc:
            status = f"ERR ({type(exc).__name__})"
            print(f"  [ERR] {target} -> {url}: {exc}", file=sys.stderr)
        with self._lock:
            self.statuses[target] = status

    def snapshot(self) -> dict[str, str]:
        with self._lock:
            return dict(self.statuses)


# =====================================================================
# PHASE 1: ZERO-LAG LATEST-FRAME CAPTURE (DROIDCAM HTTP OR WEBCAM INDEX)
# =====================================================================

class LatestFrameStream:
    """Continuously drains Phone 1's stream in a background thread so stale frames never pile up."""

    def __init__(self, source: str, cv2_mod: Any, np_mod: Any):
        self.raw_source = source
        self.cv2 = cv2_mod
        self.np = np_mod
        self.is_http = source.startswith(("http://", "https://"))
        self.source_arg: Any = int(source) if source.isdigit() else source

        self._lock = threading.Lock()
        self._frame: Any = None
        self._frame_id: int = 0
        self._error: Optional[str] = None
        self._backend: str = "connecting"
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)

    def start(self) -> None:
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()

    def _set_frame(self, frame: Any, backend: str) -> None:
        with self._lock:
            self._frame = frame
            self._frame_id += 1
            self._backend = backend
            self._error = None

    def _set_error(self, msg: str) -> None:
        with self._lock:
            self._error = msg

    def _read_http_mjpeg(self, url: str) -> None:
        """Direct raw JPEG boundary reader (0xFFD8..0xFFD9) — zero FFmpeg buffer lag on DroidCam."""
        req = Request(url, headers={"User-Agent": "CampusFlow-Vision/1.0"})
        with urlopen(req, timeout=5.0) as resp:
            buf = bytearray()
            while not self._stop.is_set():
                chunk = resp.read(16384)
                if not chunk:
                    break
                buf.extend(chunk)
                latest_jpg = None
                while True:
                    start = buf.find(b"\xff\xd8")
                    if start == -1:
                        buf.clear()
                        break
                    end = buf.find(b"\xff\xd9", start + 2)
                    if end == -1:
                        if start > 0:
                            del buf[:start]
                        break
                    latest_jpg = bytes(buf[start : end + 2])
                    del buf[: end + 2]
                if latest_jpg is not None:
                    arr = self.np.frombuffer(latest_jpg, dtype=self.np.uint8)
                    img = self.cv2.imdecode(arr, self.cv2.IMREAD_COLOR)
                    del arr, latest_jpg
                    if img is not None:
                        self._set_frame(img, "http-mjpeg")

    def _read_opencv(self) -> None:
        if isinstance(self.source_arg, int) and sys.platform.startswith("win"):
            cap = self.cv2.VideoCapture(self.source_arg, self.cv2.CAP_DSHOW)
        else:
            cap = self.cv2.VideoCapture(self.source_arg)
        if not cap.isOpened():
            cap.release()
            raise RuntimeError(f"OpenCV could not open source: {self.raw_source}")

        cap.set(self.cv2.CAP_PROP_BUFFERSIZE, 1)
        if isinstance(self.source_arg, int):
            cap.set(self.cv2.CAP_PROP_FRAME_WIDTH, 640)
            cap.set(self.cv2.CAP_PROP_FRAME_HEIGHT, 480)
        try:
            while not self._stop.is_set():
                ok, frame = cap.read()
                if not ok or frame is None:
                    raise RuntimeError("Stream ended or dropped frame.")
                self._set_frame(frame, "opencv")
        finally:
            cap.release()

    def _run(self) -> None:
        while not self._stop.is_set():
            try:
                if self.is_http:
                    # Try direct zero-lag MJPEG parser first (works reliably on DroidCam /video);
                    # if the server serves non-MJPEG HTTP, fall back to OpenCV capture.
                    try:
                        self._read_http_mjpeg(self.raw_source)
                    except Exception:
                        if not self._stop.is_set():
                            self._read_opencv()
                else:
                    self._read_opencv()
            except Exception as exc:
                self._set_error(str(exc))
                time.sleep(1.0)

    def read_latest(self, last_seen_id: int) -> tuple[Any, int, str, Optional[str]]:
        with self._lock:
            if self._frame is None or self._frame_id == last_seen_id:
                return None, self._frame_id, self._backend, self._error
            return self._frame.copy(), self._frame_id, self._backend, self._error


# =====================================================================
# MAIN LOOP: LIVE HUD + YOLOV8N + STATE-CHANGE TORCH TRIGGERS
# =====================================================================

def draw_hud(
    cv2_mod: Any,
    frame: Any,
    room: DebouncedRoomState,
    torches: WirelessTorchController,
    infer_ms: float,
    fps: float,
    backend: str,
) -> Any:
    h, w = frame.shape[:2]
    lights_on = room.lights_on()
    banner_col = (40, 180, 60) if lights_on else (55, 65, 85)
    if room.manual_override:
        banner_col = (0, 140, 245)

    # Top status bar
    overlay = frame.copy()
    cv2_mod.rectangle(overlay, (0, 0), (w, 72), (14, 18, 28), -1)
    cv2_mod.addWeighted(overlay, 0.82, frame, 0.18, 0, frame)
    del overlay

    # Lights pill on top-right
    status_txt = "LIGHTS: ON" if lights_on else "LIGHTS: OFF"
    if room.manual_override:
        status_txt = "LIGHTS: ON (OVERRIDE)"
    cv2_mod.rectangle(frame, (w - 255, 10), (w - 10, 60), banner_col, -1)
    cv2_mod.putText(frame, status_txt, (w - 242, 42), cv2_mod.FONT_HERSHEY_SIMPLEX, 0.65, (255, 255, 255), 2)

    # Left telemetry
    state_label = "OCCUPIED" if room.state == "OCCUPIED" else "EMPTY"
    rem = room.hold_remaining()
    hold_txt = f" | Off in {rem:.1f}s" if rem > 0 else ""
    cv2_mod.putText(
        frame,
        f"C-101: {state_label} | Persons: {room.last_count}{hold_txt}",
        (12, 30),
        cv2_mod.FONT_HERSHEY_SIMPLEX,
        0.65,
        (240, 248, 255),
        2,
    )
    cv2_mod.putText(
        frame,
        f"YOLOv8n ({infer_ms:.0f}ms) | {fps:.1f} FPS | {backend} | [M] Override [T] Resend [Q] Quit",
        (12, 56),
        cv2_mod.FONT_HERSHEY_SIMPLEX,
        0.46,
        (170, 190, 215),
        1,
    )

    # Bottom torch phones status strip (if Phones 2 & 3 configured)
    snap = torches.snapshot()
    if snap:
        y0 = h - 28
        cv2_mod.rectangle(frame, (0, y0), (w, h), (14, 18, 28), -1)
        summary = "   |   ".join(f"Phone {i + 2} ({k}): {v}" for i, (k, v) in enumerate(snap.items()))
        cv2_mod.putText(frame, summary, (10, h - 9), cv2_mod.FONT_HERSHEY_SIMPLEX, 0.46, (125, 215, 255), 1)
    return frame


def main() -> None:
    parser = argparse.ArgumentParser(description="CampusFlow Phone 1 DroidCam -> YOLOv8n -> Phones 2 & 3 Torches")
    parser.add_argument(
        "--source",
        default="http://10.110.18.80:4747/video",
        help="Phone 1 DroidCam URL (default: http://10.110.18.80:4747/video) or webcam index (e.g., 0 or 1).",
    )
    parser.add_argument("--model", default="yolov8n.pt", help="Ultralytics model path/name (default: yolov8n.pt)")
    parser.add_argument("--imgsz", type=int, default=416, help="YOLO inference size (default: 416)")
    parser.add_argument("--conf", type=float, default=0.50, help="Person confidence threshold (default: 0.50)")
    parser.add_argument(
        "--hold-seconds",
        type=float,
        default=3.0,
        help="Seconds with 0 persons before flipping from OCCUPIED to EMPTY (default: 3.0s)",
    )
    parser.add_argument(
        "--torches",
        nargs="*",
        default=[],
        help="Phones 2 & 3 IP:PORT addresses (e.g., 192.168.137.102:8080 192.168.137.103:8080)",
    )
    parser.add_argument(
        "--torch-app",
        choices=["ipwebcam", "macrodroid", "droidcam"],
        default="ipwebcam",
        help="App on Phones 2 & 3 controlling the torch (default: ipwebcam -> /enabletorch & /disabletorch)",
    )
    parser.add_argument("--no-window", action="store_true", help="Run headless without cv2.imshow preview")
    args = parser.parse_args()

    try:
        import cv2  # type: ignore
        import numpy as np  # type: ignore
        from ultralytics import YOLO  # type: ignore
    except ImportError as exc:
        print(f"Missing dependency: {exc}. Run with global python or install opencv-python + ultralytics.", file=sys.stderr)
        sys.exit(1)

    print(f"Loading {args.model} (class 0: person only, imgsz={args.imgsz}, conf={args.conf})...")
    model = YOLO(args.model)

    room = DebouncedRoomState(hold_seconds=args.hold_seconds)
    torches = WirelessTorchController(targets=args.torches, app_mode=args.torch_app)
    stream = LatestFrameStream(args.source, cv2, np)
    stream.start()

    print(f"Streaming from Phone 1 source: {args.source}")
    if args.torches:
        print(f"Wireless torch targets ({args.torch_app}): {', '.join(args.torches)}")
    else:
        print("No --torches specified yet (visual laptop HUD mode). Add --torches <PHONE2_IP:8080> <PHONE3_IP:8080> when ready.")

    last_frame_id = 0
    last_err_log = 0.0
    fps = 0.0
    fps_frames = 0
    fps_t0 = time.perf_counter()

    try:
        while True:
            frame, fid, backend, err = stream.read_latest(last_frame_id)
            if frame is None:
                now = time.monotonic()
                if err and now - last_err_log > 3.0:
                    print(f"[WAIT] Waiting for video from {args.source}: {err}", file=sys.stderr)
                    last_err_log = now
                if not args.no_window:
                    if last_frame_id == 0:
                        blank = np.zeros((480, 760, 3), dtype=np.uint8)
                        blank[:] = (22, 16, 12)
                        cv2.putText(blank, "CampusFlow · Classroom C-101 Vision", (24, 52), cv2.FONT_HERSHEY_SIMPLEX, 0.85, (255, 255, 255), 2)
                        cv2.putText(blank, f"Connecting to: {args.source}", (24, 110), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (125, 215, 255), 2)
                        msg = (err or "Waiting for first frame from DroidCam...")[:78]
                        cv2.putText(blank, msg, (24, 155), cv2.FONT_HERSHEY_SIMPLEX, 0.52, (120, 180, 255), 1)
                        cv2.putText(blank, "Press [W] for Laptop Webcam Fallback  |  Press [Q] to Quit", (24, 435), cv2.FONT_HERSHEY_SIMPLEX, 0.56, (120, 240, 170), 2)
                        cv2.imshow("CampusFlow · Classroom C-101 Live Vision (Press Q to quit)", blank)
                    key = cv2.waitKey(30) & 0xFF
                    if key in (ord("q"), 27):
                        break
                    if key in (ord("w"), ord("W")) and args.source != "0":
                        print("[SWITCH] Switching live source to built-in laptop webcam (0)...")
                        stream.stop()
                        args.source = "0"
                        stream = LatestFrameStream("0", cv2, np)
                        stream.start()
                        last_frame_id = 0
                else:
                    time.sleep(0.02)
                continue

            last_frame_id = fid
            t0 = time.perf_counter()
            results = model.predict(
                frame,
                classes=[0],
                imgsz=args.imgsz,
                conf=args.conf,
                verbose=False,
            )
            infer_ms = (time.perf_counter() - t0) * 1000.0

            boxes = results[0].boxes if results else None
            count = len(boxes) if boxes is not None else 0
            max_conf = float(boxes.conf.max().item()) if count > 0 else 0.0

            changed, label = room.update(count, max_conf)
            if changed:
                reason = f"persons={count}" if room.lights_on() else f"vacant {args.hold_seconds:.1f}s"
                print(f"[STATE] Room -> {label} ({reason})")
                torches.set_lights(room.lights_on(), reason=reason)

            fps_frames += 1
            elapsed = time.perf_counter() - fps_t0
            if elapsed >= 0.5:
                fps = fps_frames / elapsed
                fps_frames = 0
                fps_t0 = time.perf_counter()

            if not args.no_window:
                annotated = results[0].plot()
                draw_hud(cv2, annotated, room, torches, infer_ms, fps, backend)
                cv2.imshow("CampusFlow · Classroom C-101 Live Vision (Press Q to quit)", annotated)
                del annotated
                key = cv2.waitKey(1) & 0xFF
                if key in (ord("q"), 27):
                    break
                if key in (ord("m"), ord("M")):
                    ov_changed, ov_label = room.toggle_override()
                    print(f"[OVERRIDE] Manual override -> {'ON' if room.manual_override else 'OFF'} ({ov_label})")
                    if ov_changed:
                        torches.set_lights(room.lights_on(), reason="manual override")
                if key in (ord("t"), ord("T")):
                    torches.set_lights(room.lights_on(), reason="manual resend")

            # RAM-only privacy: discard frame immediately
            del frame
            del results
    except KeyboardInterrupt:
        print("\nStopping CampusFlow classroom vision.")
    finally:
        stream.stop()
        if not args.no_window:
            cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
