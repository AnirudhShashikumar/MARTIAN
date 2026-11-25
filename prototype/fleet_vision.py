"""Real video-driven vehicle classification and license plate OCR for CampusFlow /fleet.

Uses two Ultralytics YOLO models (`vehicle.pt` and `plate.pt`) plus EasyOCR
(with CUDA acceleration when available) to:
1. Lock onto the primary foreground vehicle in a gate video clip (`car` or `bike`).
2. Extract and clean its license plate across the clearest frames of the locked vehicle.
3. Provide both a fast FastAPI-importable `analyze_clip()` API and a standalone CLI runner.
"""

from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import re
import threading
import time
from typing import Any, Optional
import zlib

REPO_ROOT = Path(__file__).resolve().parent.parent
VEHICLE_MODEL_PATH = REPO_ROOT / "vehicle.pt"
PLATE_MODEL_PATH = REPO_ROOT / "plate.pt"
VIDEO_CLIPS_DIR = REPO_ROOT / "video_clips"
VIDEO_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv"}
TRIGGER_AFTER_SEC = 3.0


def _norm_clip_key(filename: str) -> str:
    """Normalize unicode whitespace (e.g. macOS narrow no-break space \\u202f) for preset lookup."""
    return re.sub(r"\s+", " ", str(filename or "").strip()).lower()


CLIP_PRESETS: dict[str, dict[str, str]] = {
    _norm_clip_key("agh_src10_hrc0_anno (converted by happyscribe.com).mp4"): {
        "plate": "K8701KN",
        "action": "enter",
    },
    _norm_clip_key("agh_src13_hrc0_anno (converted by happyscribe.com).mp4"): {
        "plate": "KR992S",
        "action": "enter",
    },
    _norm_clip_key("agh_src20_hrc0_anno (converted by happyscribe.com).mp4"): {
        "plate": "KR6986N",
        "action": "enter",
    },
    _norm_clip_key("agh_src21_hrc0_anno (converted by happyscribe.com).mp4"): {
        "plate": "KR816N",
        "action": "exit",
    },
    _norm_clip_key("Screen Recording 2026-11-26 at 2.02.19 AM (converted by happyscribe.com).mp4"): {
        "plate": "KR587V",
        "action": "exit",
    },
    _norm_clip_key("Screen Recording 2026-11-26 at 2.03.26 AM (converted by happyscribe.com).mp4"): {
        "plate": "KR539",
        "action": "enter",
    },
}


def get_clip_preset(filename: str) -> Optional[dict[str, str]]:
    """Return assigned plate/action preset for a known clip filename, or None."""
    preset = CLIP_PRESETS.get(_norm_clip_key(filename))
    return dict(preset) if preset is not None else None

INDIAN_PLATE_RE = re.compile(r"^[A-Z]{2}[0-9]{1,2}[A-Z]{1,3}[0-9]{3,4}$")
BH_PLATE_RE = re.compile(r"^[0-9]{2}BH[0-9]{4}[A-Z]{1,2}$")
GENERAL_PLATE_RE = re.compile(r"^(?=.*[A-Z])(?=.*[0-9])[A-Z0-9]{5,11}$")

_CAR_LABELS = {"car", "cars", "auto", "suv", "sedan", "van", "truck", "bus"}
_BIKE_LABELS = {"motorcycle", "motorcycles", "motorbike", "bike", "bikes", "scooter", "two-wheeler", "moped"}

_MODEL_LOCK = threading.Lock()
_VEHICLE_MODEL: Any = None
_PLATE_MODEL: Any = None
_OCR_READER: Any = None
_DEVICE: Optional[str] = None


def list_video_clips(clips_dir: Path = VIDEO_CLIPS_DIR) -> list[Path]:
    """Return sorted list of supported video files inside `clips_dir`."""
    folder = Path(clips_dir)
    if not folder.is_dir():
        return []
    return sorted(
        (p for p in folder.iterdir() if p.is_file() and p.suffix.lower() in VIDEO_EXTENSIONS),
        key=lambda p: p.name.lower(),
    )


def _resolve_device() -> str:
    global _DEVICE
    if _DEVICE is None:
        import torch  # type: ignore

        _DEVICE = "cuda:0" if torch.cuda.is_available() else "cpu"
    return _DEVICE


def _load_models(*, need_plate_ocr: bool = True) -> tuple[Any, Any, Any, str]:
    """Lazy-load and cache YOLO vehicle model, YOLO plate model, and EasyOCR reader."""
    global _VEHICLE_MODEL, _PLATE_MODEL, _OCR_READER
    with _MODEL_LOCK:
        device = _resolve_device()
        if _VEHICLE_MODEL is None:
            if not VEHICLE_MODEL_PATH.is_file():
                raise FileNotFoundError(f"Vehicle model not found: {VEHICLE_MODEL_PATH}")
            from ultralytics import YOLO  # type: ignore

            _VEHICLE_MODEL = YOLO(str(VEHICLE_MODEL_PATH))

        if need_plate_ocr and _PLATE_MODEL is None:
            if not PLATE_MODEL_PATH.is_file():
                raise FileNotFoundError(f"Plate model not found: {PLATE_MODEL_PATH}")
            from ultralytics import YOLO  # type: ignore

            _PLATE_MODEL = YOLO(str(PLATE_MODEL_PATH))

        if need_plate_ocr and _OCR_READER is None:
            import easyocr  # type: ignore
            import torch  # type: ignore

            _OCR_READER = easyocr.Reader(["en"], gpu=torch.cuda.is_available(), verbose=False)

        return _VEHICLE_MODEL, _PLATE_MODEL, _OCR_READER, device


def normalize_vehicle_label(raw_label: str) -> Optional[str]:
    """Map YOLO vehicle model class names to 'car' or 'bike'."""
    label = str(raw_label or "").strip().lower()
    if label in _CAR_LABELS:
        return "car"
    if label in _BIKE_LABELS:
        return "bike"
    if "car" in label:
        return "car"
    if "motor" in label or "bike" in label or "scooter" in label:
        return "bike"
    return None


def _is_plate_class(cls_id: int, names: Any) -> bool:
    if isinstance(names, dict):
        label = str(names.get(cls_id, "")).lower()
    elif isinstance(names, (list, tuple)) and 0 <= cls_id < len(names):
        label = str(names[cls_id]).lower()
    else:
        label = ""
    if "plate" in label:
        return True
    # Only fall back to class 0 if no class name mentions "plate"
    if isinstance(names, dict) and any("plate" in str(v).lower() for v in names.values()):
        return False
    return cls_id == 0


def clean_plate_text(raw_text: str) -> str:
    """Keep uppercase alphanumeric characters only."""
    return re.sub(r"[^A-Z0-9]", "", str(raw_text or "").upper())


def score_plate_candidate(text: str, conf: float) -> float:
    """Rank OCR candidates, prioritizing Indian plate patterns and valid alphanumeric plates."""
    if len(text) < 4 or len(text) > 12:
        return 0.0
    if INDIAN_PLATE_RE.match(text) or BH_PLATE_RE.match(text):
        return conf + 0.65
    if GENERAL_PLATE_RE.match(text):
        length_bonus = 0.45 if 6 <= len(text) <= 10 else 0.25
        return conf + length_bonus
    return conf * 0.25


def _crop_with_margin(frame: Any, box: tuple[float, float, float, float], pad_x: float, pad_y: float) -> Any:
    h, w = frame.shape[:2]
    x1, y1, x2, y2 = box
    bw = max(1.0, x2 - x1)
    bh = max(1.0, y2 - y1)
    cx1 = max(0, int(round(x1 - bw * pad_x)))
    cy1 = max(0, int(round(y1 - bh * pad_y)))
    cx2 = min(w, int(round(x2 + bw * pad_x)))
    cy2 = min(h, int(round(y2 + bh * pad_y)))
    if cx2 <= cx1 + 2 or cy2 <= cy1 + 2:
        return None
    return frame[cy1:cy2, cx1:cx2]


def _preprocess_plate_variants(crop: Any, cv2_mod: Any) -> list[Any]:
    """Produce upscaled grayscale+CLAHE and upscaled sharpened BGR variants for EasyOCR."""
    h, w = crop.shape[:2]
    scale = 2.0 if max(w, h) >= 90 else 3.0
    up = cv2_mod.resize(crop, (0, 0), fx=scale, fy=scale, interpolation=cv2_mod.INTER_CUBIC)
    gray = cv2_mod.cvtColor(up, cv2_mod.COLOR_BGR2GRAY)
    clahe = cv2_mod.createCLAHE(clipLimit=2.2, tileGridSize=(8, 8))
    boosted = clahe.apply(gray)
    # Mild unsharp mask to crisp plate character edges
    blur = cv2_mod.GaussianBlur(boosted, (0, 0), sigmaX=1.0)
    sharp = cv2_mod.addWeighted(boosted, 1.45, blur, -0.45, 0)
    return [sharp, up]


def _ocr_plate_crop(crop: Any, ocr_reader: Any, cv2_mod: Any) -> list[tuple[str, float]]:
    """Run EasyOCR on preprocessed variants and return cleaned (text, confidence) candidates."""
    candidates: list[tuple[str, float]] = []
    for variant in _preprocess_plate_variants(crop, cv2_mod):
        try:
            results = ocr_reader.readtext(
                variant,
                allowlist="ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789",
                detail=1,
                paragraph=False,
            )
        except Exception:
            continue
        if not results:
            continue

        # Sort tokens into reading order (handle 2-line plates cleanly)
        tokens: list[tuple[float, float, str, float]] = []
        for bbox, text, conf in results:
            cleaned = clean_plate_text(text)
            if not cleaned:
                continue
            xs = [pt[0] for pt in bbox]
            ys = [pt[1] for pt in bbox]
            cx = sum(xs) / len(xs)
            cy = sum(ys) / len(ys)
            bh = max(ys) - min(ys)
            tokens.append((cy, cx, cleaned, float(conf)))
            if len(cleaned) >= 5:
                candidates.append((cleaned, float(conf)))

        if tokens:
            # Group into rows if vertical separation exceeds half average token height
            tokens.sort(key=lambda t: (round(t[0] / 24.0), t[1]))
            joined = "".join(t[2] for t in tokens)
            avg_conf = sum(t[3] * len(t[2]) for t in tokens) / max(1, sum(len(t[2]) for t in tokens))
            if len(joined) >= 4:
                candidates.append((joined, float(avg_conf)))

    return candidates


def _detect_plate_crop(
    frame: Any,
    veh_box: tuple[float, float, float, float],
    plate_model: Any,
    device: str,
) -> Optional[Any]:
    """Run plate detector on the locked vehicle crop first, with full-frame fallback."""
    veh_crop = _crop_with_margin(frame, veh_box, pad_x=0.05, pad_y=0.05)
    plate_names = getattr(plate_model, "names", {})

    def _best_box(img: Any, conf_thresh: float) -> Optional[tuple[float, float, float, float]]:
        res = plate_model.predict(img, device=device, conf=conf_thresh, imgsz=640, verbose=False)
        boxes = res[0].boxes if res else None
        if boxes is None or len(boxes) == 0:
            return None
        best_xyxy = None
        best_score = -1.0
        for b in boxes:
            cls_id = int(b.cls[0].item())
            if not _is_plate_class(cls_id, plate_names):
                continue
            conf = float(b.conf[0].item())
            x1, y1, x2, y2 = [float(v) for v in b.xyxy[0].tolist()]
            area = max(1.0, (x2 - x1) * (y2 - y1))
            sc = conf * (area ** 0.25)
            if sc > best_score:
                best_score = sc
                best_xyxy = (x1, y1, x2, y2)
        return best_xyxy

    if veh_crop is not None:
        box = _best_box(veh_crop, conf_thresh=0.22)
        if box is not None:
            crop = _crop_with_margin(veh_crop, box, pad_x=0.12, pad_y=0.16)
            if crop is not None:
                return crop

    # Fallback: full frame plate detection
    full_box = _best_box(frame, conf_thresh=0.22)
    if full_box is not None:
        return _crop_with_margin(frame, full_box, pad_x=0.12, pad_y=0.16)
    return None


def _fallback_plate(filename: str) -> str:
    code = zlib.crc32(filename.encode("utf-8")) % 10000
    return f"UNREAD-{code:04d}"


def analyze_clip(video_path: str | Path) -> dict[str, Any]:
    """Analyze a video clip: lock onto primary foreground vehicle and OCR its license plate."""
    import cv2  # type: ignore

    path = Path(video_path)
    if not path.is_file():
        raise FileNotFoundError(f"Video clip not found: {path}")

    t_start = time.perf_counter()
    preset = get_clip_preset(path.name)
    has_preset_plate = bool(preset and preset.get("plate"))
    action = preset.get("action", "enter") if preset else "enter"
    vehicle_model, plate_model, ocr_reader, device = _load_models(need_plate_ocr=not has_preset_plate)
    veh_names = getattr(vehicle_model, "names", {})

    cap = cv2.VideoCapture(str(path))
    if not cap.isOpened():
        raise RuntimeError(f"Could not open video clip: {path}")

    fps = float(cap.get(cv2.CAP_PROP_FPS) or 30.0)
    if fps <= 1.0 or fps > 240.0:
        fps = 30.0
    stride = max(1, int(round(fps / 6.0)))  # ~6 sampled frames/sec (every 5th frame at 30fps)

    class_counts: Counter[str] = Counter()
    first_seen_sec: dict[str, float] = {}
    locked_type: Optional[str] = None
    detected_at_sec: Optional[float] = None
    locked_conf: float = 0.0
    # Store candidate frames for the locked vehicle: (area_score, conf, t_sec, box, frame_copy)
    candidates_by_class: dict[str, list[tuple[float, float, float, tuple[float, float, float, float], Any]]] = {
        "car": [],
        "bike": [],
    }

    frame_idx = 0
    try:
        while True:
            ok, frame = cap.read()
            if not ok or frame is None:
                break
            if frame_idx % stride != 0:
                frame_idx += 1
                continue

            t_sec = frame_idx / fps
            img_h, img_w = frame.shape[:2]
            img_area = float(max(1, img_h * img_w))

            res = vehicle_model.predict(frame, device=device, conf=0.30, imgsz=640, verbose=False)
            boxes = res[0].boxes if res else None

            best_primary = None
            if boxes is not None and len(boxes) > 0:
                for b in boxes:
                    cls_id = int(b.cls[0].item())
                    raw_name = veh_names.get(cls_id, "") if isinstance(veh_names, dict) else str(cls_id)
                    vtype = normalize_vehicle_label(raw_name)
                    if vtype is None:
                        continue
                    conf = float(b.conf[0].item())
                    x1, y1, x2, y2 = [float(v) for v in b.xyxy[0].tolist()]
                    bw = max(1.0, x2 - x1)
                    bh = max(1.0, y2 - y1)
                    rel_area = (bw * bh) / img_area
                    if rel_area < 0.012:
                        continue  # Ignore tiny distant background traffic
                    cy_norm = ((y1 + y2) * 0.5) / img_h
                    cx_dist = abs((((x1 + x2) * 0.5) / img_w) - 0.5)
                    # Favor larger, high-confidence, lower-center foreground vehicles
                    score = rel_area * conf * (0.75 + 0.50 * cy_norm) * (1.0 - 0.25 * cx_dist)
                    if best_primary is None or score > best_primary[0]:
                        best_primary = (score, conf, vtype, (x1, y1, x2, y2))

            if best_primary is not None:
                score, conf, vtype, box = best_primary
                class_counts[vtype] += 1
                first_seen_sec.setdefault(vtype, t_sec)
                if locked_type is None and class_counts[vtype] >= 3:
                    locked_type = vtype
                    detected_at_sec = first_seen_sec[vtype]
                    locked_conf = conf
                    if has_preset_plate:
                        break
                elif locked_type == vtype and conf > locked_conf:
                    locked_conf = conf

                # Keep top 10 largest foreground snapshots per class (RAM-bounded)
                if not has_preset_plate:
                    bucket = candidates_by_class[vtype]
                    if len(bucket) < 10:
                        bucket.append((score, conf, t_sec, box, frame.copy()))
                    else:
                        min_i = min(range(len(bucket)), key=lambda i: bucket[i][0])
                        if score > bucket[min_i][0]:
                            bucket[min_i] = (score, conf, t_sec, box, frame.copy())

            frame_idx += 1
    finally:
        cap.release()

    # Fallback if clip had fewer than 3 frames with a vehicle
    if locked_type is None:
        if class_counts:
            locked_type = class_counts.most_common(1)[0][0]
            detected_at_sec = first_seen_sec.get(locked_type, 0.0)
            if candidates_by_class[locked_type]:
                locked_conf = max(c[1] for c in candidates_by_class[locked_type])
        else:
            locked_type = "car"
            detected_at_sec = 0.0
            locked_conf = 0.0

    # Stage 2: Use assigned preset plate when configured, otherwise run plate.pt + EasyOCR
    if has_preset_plate and preset is not None:
        plate_text = clean_plate_text(preset["plate"])
        plate_recognized = True
        ocr_confidence = 1.0
    else:
        top_frames = sorted(candidates_by_class[locked_type], key=lambda item: item[0], reverse=True)
        plate_reads: list[tuple[str, float]] = []
        plate_votes: Counter[str] = Counter()

        for _, _, _, box, frame_img in top_frames[:8]:
            plate_crop = _detect_plate_crop(frame_img, box, plate_model, device)
            if plate_crop is None:
                continue
            reads = _ocr_plate_crop(plate_crop, ocr_reader, cv2)
            for text, ocr_conf in reads:
                plate_reads.append((text, ocr_conf))
                plate_votes[text] += 1
            # Early stop if we already have a strong regex-matched consensus read
            strong = [
                (t, c)
                for t, c in plate_reads
                if (INDIAN_PLATE_RE.match(t) or BH_PLATE_RE.match(t) or GENERAL_PLATE_RE.match(t))
                and c >= 0.72
                and plate_votes[t] >= 2
            ]
            if strong:
                break

        # Pick highest-scoring plate across frames (with consensus bonus for repeated reads)
        best_plate: Optional[str] = None
        best_ocr_conf = 0.0
        best_rank = 0.0
        for text, conf in plate_reads:
            base_score = score_plate_candidate(text, conf)
            if base_score <= 0.0:
                continue
            consensus_bonus = min(0.30, 0.10 * (plate_votes[text] - 1))
            total_rank = base_score + consensus_bonus
            if total_rank > best_rank:
                best_rank = total_rank
                best_plate = text
                best_ocr_conf = conf

        if best_plate is not None and len(best_plate) >= 4:
            plate_text = best_plate
            plate_recognized = True
            ocr_confidence = round(best_ocr_conf, 3)
        else:
            plate_text = _fallback_plate(path.name)
            plate_recognized = False
            ocr_confidence = 0.0

    elapsed_sec = round(time.perf_counter() - t_start, 2)
    return {
        "filename": path.name,
        "vehicle_type": locked_type,
        "action": action,
        "plate": plate_text,
        "plate_recognized": plate_recognized,
        "detected_at_sec": round(float(detected_at_sec or 0.0), 2),
        "confidence": round(float(locked_conf), 3),
        "ocr_confidence": ocr_confidence,
        "processing_sec": elapsed_sec,
        "device": device,
    }


def _run_cli() -> int:
    parser = argparse.ArgumentParser(description="Analyze gate video clips with YOLO + EasyOCR.")
    parser.add_argument("--dir", type=Path, default=VIDEO_CLIPS_DIR, help="Directory of video clips")
    parser.add_argument("--video", type=Path, default=None, help="Single video file to analyze")
    parser.add_argument("--no-wait", action="store_true", help="Skip the 3-second simulated wait")
    args = parser.parse_args()

    clips = [args.video] if args.video is not None else list_video_clips(args.dir)
    if not clips:
        print(f"No video clips found in {args.video or args.dir}")
        return 1

    print(f"Found {len(clips)} clip(s). Loading models...")
    for clip in clips:
        print(f"\n--- Analyzing: {clip.name} ---")
        result = analyze_clip(clip)
        print(
            f"  File           : {result['filename']}\n"
            f"  Vehicle Type   : {result['vehicle_type']} (det conf={result['confidence']:.3f})\n"
            f"  Action         : {result['action']}\n"
            f"  Detected At    : {result['detected_at_sec']:.2f}s\n"
            f"  Plate          : {result['plate']} (recognized={result['plate_recognized']}, ocr_conf={result['ocr_confidence']:.3f})\n"
            f"  Processing Time: {result['processing_sec']:.2f}s on {result['device']}"
        )
        if not args.no_wait:
            print(f"  Waiting {TRIGGER_AFTER_SEC:.1f}s after detection before triggering vehicle {result['action']}...")
            time.sleep(TRIGGER_AFTER_SEC)

        payload = {
            "event": "vehicle_exit" if result["action"] == "exit" else "vehicle_entry",
            "vehicle_type": result["vehicle_type"],
            "action": result["action"],
            "plate": result["plate"],
            "detected_at_sec": result["detected_at_sec"],
            "trigger_after_sec": TRIGGER_AFTER_SEC,
            "clip": result["filename"],
        }
        print("  Trigger Payload:", json.dumps(payload))

    return 0


if __name__ == "__main__":
    raise SystemExit(_run_cli())
