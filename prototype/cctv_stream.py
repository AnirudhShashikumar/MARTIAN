"""Server-side DroidCam + YOLOv8n live MJPEG classroom CCTV stream engine.

Streams annotated JPEG frames (with YOLOv8 person bounding boxes) directly into
the CampusFlow web app (<img src="/api/cctv/stream">) with zero pop-up windows
and zero saved video frames (RAM-only processing).
"""

from __future__ import annotations

from dataclasses import dataclass, field
import sys
import threading
import time
from typing import Any, Callable, Iterator, Optional
from urllib.request import Request, urlopen


DEFAULT_DROIDCAM_URL = "http://10.110.18.80:4747/video"
TORCH_TIMEOUT_SECONDS = 1.5
TORCH_DEVICES: tuple[tuple[str, str], ...] = (
    ("Sanjana", "http://10.110.21.198:8080"),
    ("Ani", "http://10.100.36.157:8080"),
)


def _send_torch_http(url: str, timeout: float = TORCH_TIMEOUT_SECONDS) -> None:
    req = Request(url, headers={"User-Agent": "CampusFlow-Torch/1.0"})
    with urlopen(req, timeout=timeout) as resp:
        resp.read(64)


@dataclass
class DebouncedOccupancy:
    """Instant flip to OCCUPIED on person detection; debounced hold before EMPTY."""

    hold_seconds: float = 3.0
    clock: Callable[[], float] = time.monotonic

    state: str = "EMPTY"  # "OCCUPIED" | "EMPTY"
    empty_since: Optional[float] = None
    person_count: int = 0
    confidence: float = 0.0

    def hold_remaining(self, now: Optional[float] = None) -> float:
        if self.state != "OCCUPIED" or self.empty_since is None:
            return 0.0
        t = self.clock() if now is None else now
        return max(0.0, self.hold_seconds - (t - self.empty_since))

    def update(self, person_count: int, confidence: float = 0.0) -> str:
        now = self.clock()
        self.person_count = int(person_count)
        self.confidence = round(float(confidence), 3)

        if self.person_count >= 1:
            self.empty_since = None
            self.state = "OCCUPIED"
        elif self.state == "OCCUPIED":
            if self.empty_since is None:
                self.empty_since = now
            elif (now - self.empty_since) >= self.hold_seconds:
                self.state = "EMPTY"
                self.empty_since = None
        return self.state

    def devices(self, lights_on: bool = False) -> dict[str, str]:
        if lights_on:
            return {"Lights": "On", "Fans": "On", "Projector": "On"}
        return {"Lights": "Off", "Fans": "Off", "Projector": "Off"}

    def status_message(
        self,
        active: bool,
        has_frame: bool,
        manual_override: Optional[str] = None,
        lights_on: bool = False,
    ) -> str:
        if not active:
            if lights_on:
                return "Override ON — Lights On, Fans On, Projector On (Sanjana & Ani torches ON)"
            if manual_override == "off":
                return "Override OFF — Lights Off, Fans Off, Projector Off (Sanjana & Ani torches OFF)"
            return "CCTV inactive — click Initialize CCTV Cam or use Override to toggle lights."
        if not has_frame:
            if lights_on:
                return "Connecting to Phone 1 DroidCam stream… (Lights ON)"
            return "Connecting to Phone 1 DroidCam stream…"
        if self.state == "OCCUPIED":
            rem = self.hold_remaining()
            if self.person_count == 0 and rem > 0:
                if lights_on:
                    return f"Person left frame — turning lights off in {rem:.1f}s…"
                return f"Person left frame — verifying empty ({rem:.1f}s hold) · Lights Off"
            if lights_on:
                return "Person detected — Lights On, Fans On, Projector On"
            return "Person detected — Lights Off (no auto turn-on; use Override to turn ON)"
        if lights_on:
            return "Override ON — Lights On, Fans On, Projector On (waiting for occupancy)"
        return "Class empty — Lights Off, Fans Off, Projector Off"


def _iter_http_mjpeg(url: str, stop_event: threading.Event, timeout: float = 5.0) -> Iterator[bytes]:
    req = Request(url, headers={"User-Agent": "CampusFlow-CCTV/1.0"})
    with urlopen(req, timeout=timeout) as resp:
        buf = bytearray()
        while not stop_event.is_set():
            chunk = resp.read(16384)
            if not chunk:
                break
            buf.extend(chunk)
            latest_jpg: Optional[bytes] = None
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
                yield latest_jpg


class ClassroomCCTVEngine:
    """Manages Phone 1 DroidCam capture + YOLOv8n inference + live MJPEG output + wireless torches."""

    def __init__(
        self,
        *,
        model_name: str = "yolov8n.pt",
        imgsz: int = 416,
        conf: float = 0.35,
        hold_seconds: float = 3.0,
        clock: Callable[[], float] = time.monotonic,
        torch_devices: tuple[tuple[str, str], ...] = TORCH_DEVICES,
        torch_timeout: float = TORCH_TIMEOUT_SECONDS,
        torch_requester: Optional[Callable[[str, float], Any]] = None,
    ):
        self.model_name = model_name
        self.imgsz = imgsz
        self.conf = conf
        self._clock = clock
        self._torch_devices = tuple(torch_devices)
        self._torch_timeout = float(torch_timeout)
        self._torch_requester = torch_requester if torch_requester is not None else _send_torch_http

        self._lock = threading.Lock()
        self._frame_cond = threading.Condition(self._lock)
        self._stop_event = threading.Event()
        self._capture_thread: Optional[threading.Thread] = None
        self._infer_thread: Optional[threading.Thread] = None
        self._last_torch_threads: list[threading.Thread] = []

        self._active = False
        self._source = DEFAULT_DROIDCAM_URL
        self._backend = "idle"
        self._error: Optional[str] = None
        self._has_frame = False
        self._fps = 0.0
        self._infer_ms = 0.0
        self._occupancy = DebouncedOccupancy(hold_seconds=hold_seconds, clock=clock)
        self._lights_on = False  # RAM-only appliance/torch state (never auto-turns ON)
        self._manual_override: Optional[str] = None  # None | "on" | "off"

        self._raw_frame: Any = None
        self._raw_seq = 0
        self._jpeg_bytes: Optional[bytes] = None
        self._jpeg_seq = 0
        self._model: Any = None
        self._events: list[dict[str, str]] = []
        self._logged_initial_frame = False

    def _dispatch_torches(self, *, turn_on: bool) -> list[threading.Thread]:
        """Fire HTTP torch requests to all configured phones concurrently in background threads."""
        endpoint = "enabletorch" if turn_on else "disabletorch"
        requester = self._torch_requester
        timeout = self._torch_timeout
        threads: list[threading.Thread] = []

        def _worker(url: str) -> None:
            try:
                requester(url, timeout)
            except Exception:
                # Fault-tolerant: swallow slow/unreachable phone errors so CCTV & API never block or crash.
                pass

        for name, base_url in self._torch_devices:
            url = f"{base_url.rstrip('/')}/{endpoint}"
            th = threading.Thread(
                target=_worker,
                args=(url,),
                name=f"torch-{name.lower()}-{endpoint}",
                daemon=True,
            )
            th.start()
            threads.append(th)

        with self._lock:
            self._last_torch_threads = threads
        return threads

    def _record_event_locked(self, stage: str, title: str, detail: str) -> None:
        self._events.insert(0, {
            "time": time.strftime("%H:%M:%S"),
            "stage": stage,
            "title": title,
            "detail": detail,
        })
        if len(self._events) > 50:
            self._events.pop()

    def clear_events(self) -> dict[str, Any]:
        """Clear RAM-only classroom incident log entries."""
        with self._lock:
            self._events.clear()
        return self.status()

    def _encode_status_jpeg(self, cv2_mod: Any, np_mod: Any, title: str, detail: str) -> bytes:
        canvas = np_mod.zeros((420, 740, 3), dtype=np_mod.uint8)
        canvas[:] = (28, 24, 20)
        cv2_mod.putText(canvas, "Classroom C-101 · Live CCTV", (28, 58), cv2_mod.FONT_HERSHEY_SIMPLEX, 0.85, (245, 247, 250), 2)
        cv2_mod.putText(canvas, title[:62], (28, 124), cv2_mod.FONT_HERSHEY_SIMPLEX, 0.65, (110, 210, 255), 2)
        cv2_mod.putText(canvas, detail[:76], (28, 174), cv2_mod.FONT_HERSHEY_SIMPLEX, 0.52, (195, 205, 220), 1)
        cv2_mod.putText(
            canvas,
            "Tip: Keep Phone 1 & laptop on the same hotspot (or enter 0 for laptop webcam).",
            (28, 378),
            cv2_mod.FONT_HERSHEY_SIMPLEX,
            0.48,
            (150, 225, 175),
            1,
        )
        ok, enc = cv2_mod.imencode(".jpg", canvas, [int(cv2_mod.IMWRITE_JPEG_QUALITY), 80])
        return enc.tobytes() if ok else b""

    def start(self, source: str = DEFAULT_DROIDCAM_URL, hold_seconds: float = 3.0) -> dict[str, Any]:
        cleaned = (source or DEFAULT_DROIDCAM_URL).strip()
        if not cleaned:
            cleaned = DEFAULT_DROIDCAM_URL

        self.stop()

        try:
            import cv2  # type: ignore
            import numpy as np  # type: ignore
            from ultralytics import YOLO  # type: ignore
        except ImportError as exc:
            raise RuntimeError(
                f"Live CCTV requires opencv-python and ultralytics in the server Python environment ({exc})."
            ) from exc

        with self._lock:
            self._stop_event = threading.Event()
            self._active = True
            self._source = cleaned
            self._backend = "connecting"
            self._error = None
            self._has_frame = False
            self._fps = 0.0
            self._infer_ms = 0.0
            self._occupancy = DebouncedOccupancy(
                hold_seconds=max(0.5, min(30.0, float(hold_seconds))),
                clock=self._clock,
            )
            self._logged_initial_frame = False
            self._raw_frame = None
            self._raw_seq = 0
            self._record_event_locked("CCTV", "CCTV initialized", f"Connecting to {cleaned}")
            self._jpeg_bytes = self._encode_status_jpeg(
                cv2, np, f"Connecting to {cleaned}...", "Loading YOLOv8n person detector in RAM..."
            )
            self._jpeg_seq += 1
            self._frame_cond.notify_all()

        stop_ev = self._stop_event
        self._capture_thread = threading.Thread(
            target=self._capture_loop, args=(cleaned, stop_ev, cv2, np), daemon=True
        )
        self._infer_thread = threading.Thread(
            target=self._infer_loop, args=(stop_ev, cv2, np, YOLO), daemon=True
        )
        self._capture_thread.start()
        self._infer_thread.start()
        return self.status()

    def stop(self) -> dict[str, Any]:
        with self._lock:
            was_active = self._active
            self._active = False
            self._stop_event.set()
            self._raw_frame = None
            self._has_frame = False
            self._backend = "idle"
            self._error = None
            self._fps = 0.0
            self._infer_ms = 0.0
            if was_active:
                self._record_event_locked("CCTV", "CCTV disabled", "Live camera stream stopped.")
            self._frame_cond.notify_all()

        if was_active:
            for th in (self._capture_thread, self._infer_thread):
                if th is not None and th.is_alive():
                    th.join(timeout=1.5)
        self._capture_thread = None
        self._infer_thread = None
        return self.status()

    def set_manual_override(self, mode: str = "toggle") -> dict[str, Any]:
        """Toggle or explicitly set lights ON/OFF and dispatch concurrent IP Webcam torch requests."""
        if mode not in {"toggle", "on", "off", "auto"}:
            raise ValueError("mode must be 'toggle', 'on', 'off', or 'auto'")

        dispatch_turn_on: Optional[bool] = None
        with self._lock:
            if mode == "toggle":
                target_on = not self._lights_on
                self._lights_on = target_on
                self._manual_override = "on" if target_on else "off"
                dispatch_turn_on = target_on
            elif mode == "on":
                self._lights_on = True
                self._manual_override = "on"
                dispatch_turn_on = True
            elif mode == "off":
                self._lights_on = False
                self._manual_override = "off"
                dispatch_turn_on = False
            else:  # "auto"
                self._manual_override = None
                if self._lights_on and self._occupancy.state == "EMPTY":
                    self._lights_on = False
                    dispatch_turn_on = False
                self._record_event_locked(
                    "Auto",
                    "Auto-OFF monitoring active",
                    "Lights stay off until Override; auto-OFF fires when classroom empties.",
                )

            if dispatch_turn_on is True:
                self._record_event_locked(
                    "Override",
                    "Override — Lights ON",
                    "Dispatched /enabletorch concurrently to Sanjana & Ani.",
                )
            elif dispatch_turn_on is False and mode != "auto":
                self._record_event_locked(
                    "Override",
                    "Override — Lights OFF",
                    "Dispatched /disabletorch concurrently to Sanjana & Ani.",
                )

        if dispatch_turn_on is not None:
            self._dispatch_torches(turn_on=dispatch_turn_on)
        return self.status()

    def _effective_devices_locked(self) -> dict[str, str]:
        return self._occupancy.devices(lights_on=self._lights_on)

    def process_detection(
        self,
        person_count: int,
        confidence: float = 0.0,
        *,
        infer_ms: Optional[float] = None,
        fps_now: Optional[float] = None,
    ) -> tuple[str, float, bool]:
        """Apply a YOLOv8 person detection result in RAM and trigger Auto-OFF if student left.

        - Never auto-turns lights ON when a student appears while lights are OFF.
        - When lights are ON and a student was on screen and then leaves (count == 0
          past the hold timer), flips lights OFF and dispatches /disabletorch to both phones.
        """
        should_auto_off = False
        with self._lock:
            prev_state = self._occupancy.state
            first_frame = not self._logged_initial_frame
            new_state = self._occupancy.update(person_count, confidence)
            self._has_frame = True
            self._logged_initial_frame = True
            if infer_ms is not None:
                self._infer_ms = round(infer_ms, 1)
            if fps_now is not None:
                self._fps = round(fps_now, 1)

            rem = self._occupancy.hold_remaining()
            if prev_state == "OCCUPIED" and new_state == "EMPTY" and self._lights_on:
                self._lights_on = False
                self._manual_override = None
                should_auto_off = True
                self._record_event_locked(
                    "Auto-Off",
                    "Class empty — Lights Off, Fans Off, Projector Off",
                    f"Student left for {self._occupancy.hold_seconds:.1f}s; sent /disabletorch to Sanjana & Ani.",
                )
            elif first_frame or new_state != prev_state:
                if new_state == "OCCUPIED":
                    if self._lights_on:
                        self._record_event_locked(
                            "Occupied",
                            "Person detected — Lights remain On",
                            f"{person_count} {'person' if person_count == 1 else 'people'} detected in C-101.",
                        )
                    else:
                        self._record_event_locked(
                            "Occupied",
                            "Person detected — Lights remain Off",
                            f"{person_count} {'person' if person_count == 1 else 'people'} detected in C-101 (no auto turn-on).",
                        )
                else:
                    self._record_event_locked(
                        "Empty",
                        "Class empty — Lights Off, Fans Off, Projector Off",
                        f"No person detected for {self._occupancy.hold_seconds:.1f}s.",
                    )
            lights_snap = self._lights_on

        if should_auto_off:
            self._dispatch_torches(turn_on=False)

        return new_state, rem, lights_snap

    def _publish_raw(self, frame: Any, backend: str) -> None:
        with self._lock:
            self._raw_frame = frame
            self._raw_seq += 1
            self._backend = backend
            self._error = None

    def _publish_jpeg(self, jpeg: bytes) -> None:
        with self._lock:
            self._jpeg_bytes = jpeg
            self._jpeg_seq += 1
            self._frame_cond.notify_all()

    def _capture_loop(self, source: str, stop_ev: threading.Event, cv2_mod: Any, np_mod: Any) -> None:
        is_http = source.startswith(("http://", "https://"))
        src_arg: Any = int(source) if source.isdigit() else source

        while not stop_ev.is_set():
            try:
                if is_http:
                    try:
                        for jpg in _iter_http_mjpeg(source, stop_ev):
                            if stop_ev.is_set():
                                return
                            arr = np_mod.frombuffer(jpg, dtype=np_mod.uint8)
                            img = cv2_mod.imdecode(arr, cv2_mod.IMREAD_COLOR)
                            del arr, jpg
                            if img is not None:
                                self._publish_raw(img, "droidcam-mjpeg")
                        if stop_ev.is_set():
                            return
                        raise RuntimeError("DroidCam HTTP stream ended.")
                    except Exception:
                        if stop_ev.is_set():
                            return
                        # Fallback to OpenCV HTTP capture
                        self._read_opencv_until_error(src_arg, stop_ev, cv2_mod)
                else:
                    self._read_opencv_until_error(src_arg, stop_ev, cv2_mod)
            except Exception as exc:
                if stop_ev.is_set():
                    return
                with self._lock:
                    self._error = str(exc)
                    self._has_frame = False
                self._publish_jpeg(
                    self._encode_status_jpeg(cv2_mod, np_mod, f"Waiting for {source}", str(exc))
                )
                stop_ev.wait(1.0)

    def _read_opencv_until_error(self, src_arg: Any, stop_ev: threading.Event, cv2_mod: Any) -> None:
        if isinstance(src_arg, int) and sys.platform.startswith("win"):
            cap = cv2_mod.VideoCapture(src_arg, cv2_mod.CAP_DSHOW)
        else:
            cap = cv2_mod.VideoCapture(src_arg)
        if not cap.isOpened():
            cap.release()
            raise RuntimeError(f"Could not open video source: {src_arg}")
        cap.set(cv2_mod.CAP_PROP_BUFFERSIZE, 1)
        if isinstance(src_arg, int):
            cap.set(cv2_mod.CAP_PROP_FRAME_WIDTH, 640)
            cap.set(cv2_mod.CAP_PROP_FRAME_HEIGHT, 480)
        try:
            while not stop_ev.is_set():
                ok, frame = cap.read()
                if not ok or frame is None:
                    raise RuntimeError("Camera frame read failed.")
                self._publish_raw(frame, "webcam" if isinstance(src_arg, int) else "opencv-http")
        finally:
            cap.release()

    def _infer_loop(self, stop_ev: threading.Event, cv2_mod: Any, np_mod: Any, yolo_cls: Any) -> None:
        try:
            if self._model is None:
                self._model = yolo_cls(self.model_name)
        except Exception as exc:
            with self._lock:
                self._error = f"Failed to load {self.model_name}: {exc}"
            self._publish_jpeg(self._encode_status_jpeg(cv2_mod, np_mod, "YOLOv8 Load Error", str(exc)))
            return

        last_seen = 0
        fps_frames = 0
        fps_t0 = time.perf_counter()

        while not stop_ev.is_set():
            with self._lock:
                if self._raw_frame is None or self._raw_seq == last_seen:
                    frame = None
                else:
                    frame = self._raw_frame.copy()
                    last_seen = self._raw_seq

            if frame is None:
                stop_ev.wait(0.025)
                continue

            t0 = time.perf_counter()
            results = self._model.predict(
                frame,
                classes=[0],
                imgsz=self.imgsz,
                conf=self.conf,
                verbose=False,
            )
            infer_ms = (time.perf_counter() - t0) * 1000.0

            boxes = results[0].boxes if results else None
            count = len(boxes) if boxes is not None else 0
            max_conf = float(boxes.conf.max().item()) if count > 0 else 0.0

            fps_frames += 1
            elapsed = time.perf_counter() - fps_t0
            fps_now = None
            if elapsed >= 0.5:
                fps_now = fps_frames / elapsed
                fps_frames = 0
                fps_t0 = time.perf_counter()

            state_snap, rem, lights_snap = self.process_detection(
                count,
                max_conf,
                infer_ms=infer_ms,
                fps_now=fps_now,
            )

            # Draw YOLOv8 person bounding boxes + compact live overlay directly onto streamed frame
            annotated = results[0].plot()
            badge_bg = (34, 150, 72) if lights_snap else (52, 62, 78)
            if state_snap == "OCCUPIED" and count == 0 and rem > 0 and lights_snap:
                badge_txt = f"AUTO-OFF {rem:.1f}s"
            elif state_snap == "OCCUPIED":
                badge_txt = f"OCCUPIED ({count}) {'ON' if lights_snap else 'OFF'}"
            else:
                badge_txt = "EMPTY (ON)" if lights_snap else "CLASS EMPTY"
            cv2_mod.rectangle(annotated, (10, 10), (265, 44), badge_bg, -1)
            cv2_mod.putText(annotated, badge_txt, (20, 33), cv2_mod.FONT_HERSHEY_SIMPLEX, 0.58, (255, 255, 255), 2)

            ok, enc = cv2_mod.imencode(".jpg", annotated, [int(cv2_mod.IMWRITE_JPEG_QUALITY), 80])
            del frame, results, annotated  # RAM-only: discard immediately
            if ok:
                self._publish_jpeg(enc.tobytes())

    def mjpeg_frames(self) -> Iterator[bytes]:
        """Yields multipart MJPEG bytes for FastAPI StreamingResponse."""
        last_seq = -1
        while True:
            with self._frame_cond:
                if not self._active:
                    break
                if self._jpeg_seq == last_seq:
                    self._frame_cond.wait(timeout=0.5)
                if not self._active:
                    break
                jpg = self._jpeg_bytes
                last_seq = self._jpeg_seq
            if jpg:
                yield b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + jpg + b"\r\n"

    def status(self) -> dict[str, Any]:
        with self._lock:
            return {
                "active": self._active,
                "connecting": self._active and not self._has_frame,
                "has_frame": self._has_frame,
                "source": self._source,
                "backend": self._backend,
                "state": self._occupancy.state,
                "lights_on": self._lights_on,
                "manual_override": self._manual_override,
                "person_count": self._occupancy.person_count,
                "confidence": self._occupancy.confidence,
                "hold_seconds": self._occupancy.hold_seconds,
                "hold_remaining": round(self._occupancy.hold_remaining(), 1),
                "fps": self._fps,
                "infer_ms": self._infer_ms,
                "devices": self._effective_devices_locked(),
                "torch_devices": [{"name": name, "url": url} for name, url in self._torch_devices],
                "status_message": self._occupancy.status_message(
                    self._active,
                    self._has_frame,
                    self._manual_override,
                    lights_on=self._lights_on,
                ),
                "error": self._error,
                "events": list(self._events),
            }
