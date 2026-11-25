"""Prepare the privacy-edited real gate reel and reviewed, model-backed crossing trace.

Place the three credited source files in an external working directory as
car-entry.mp4, bike-aisle.mp4 and mixed.mp4. See the prototype README for sources.
"""

import argparse
import json
from pathlib import Path
import subprocess

import cv2 as cv
import numpy as np

WIDTH, HEIGHT, FPS = 800, 450, 24
OUTPUT = Path(__file__).resolve().parents[1] / "prototype/static/fleet"
PARTS = (
    ("car-entry", 4.0, 24.0, "Driveway gate · Taryn Elliott"),
    ("bike-aisle", 0.0, 4.75, "Garage access aisle · Michele Lazzari"),
    ("mixed", 10.5, 18.25, "Parking garage exit · Ivan Chumak"),
)
# Reviewed thresholds on the source timeline. IDs identify edited tracks only.
PASSAGES = (
    ("car-entry", 11.8, "Car", "Entry", "R-C01", "Car crosses the driveway gate", (7, 2), (8.5, 13.5)),
    ("bike-aisle", 1.15, "Bike", "Entry", "R-B01", "Motorcycle enters the marked garage access aisle", (3,), (0, 4.75)),
    ("mixed", 12.75, "Car", "Exit", "R-C02", "Car leaves the garage approach", (2,), (10.5, 15.1)),
    ("mixed", 17.1, "Bike", "Exit", "R-B02", "Motorcycle crosses the garage exit path", (3,), (15, 18.25)),
)


def model_grids():
    grids, strides = [], []
    for stride in (8, 16, 32):
        y, x = np.indices((640 // stride, 640 // stride))
        grids.append(np.stack((x, y), axis=-1).reshape(-1, 2))
        strides.extend([stride] * x.size)
    return np.concatenate(grids), np.asarray(strides)[:, None]


class Detector:
    def __init__(self, weights):
        self.net = cv.dnn.readNet(str(weights))
        self.grid, self.strides = model_grids()

    def detect(self, source):
        crop = cv.resize(source, (640, 360), interpolation=cv.INTER_AREA)
        pixels = np.full((640, 640, 3), 114, dtype=np.float32)
        pixels[:360] = cv.cvtColor(crop, cv.COLOR_BGR2RGB)
        self.net.setInput(np.moveaxis(pixels, 2, 0)[None])
        pred = self.net.forward()[0]
        scores = pred[:, 4, None] * pred[:, 5:]
        labels, quality = scores.argmax(axis=1), scores.max(axis=1)
        useful = (quality > .24) & np.isin(labels, [0, 2, 3, 7])
        sizes = np.exp(pred[useful, 2:4]) * self.strides[useful] * 1.25
        centers = (pred[useful, :2] + self.grid[useful]) * self.strides[useful] * 1.25
        boxes = np.concatenate((centers - sizes / 2, sizes), axis=1)
        labels, quality = labels[useful], quality[useful]
        result = []
        for label in np.unique(labels):
            indices = np.flatnonzero(labels == label)
            keep = cv.dnn.NMSBoxes(boxes[indices].tolist(), quality[indices].tolist(), .24, .45)
            for offset in np.asarray(keep).reshape(-1):
                index = indices[offset]
                result.append([int(label), round(float(quality[index]), 3), *np.rint(boxes[index]).astype(int).tolist()])
        return result


def resized(frame):
    return cv.resize(frame, (WIDTH, HEIGHT), interpolation=cv.INTER_AREA)


def sample(directory, detector):
    observations = {}
    for name, start, end, _ in PARTS:
        capture = cv.VideoCapture(str(directory / (name + ".mp4")))
        rows = []
        for time in np.arange(start, end, .25):
            capture.set(cv.CAP_PROP_POS_MSEC, time * 1000)
            ok, frame = capture.read()
            if not ok:
                break
            frame = resized(frame)
            if name == "car-entry":
                left, top, w, h = 245, 215, 285, 225
                rotated = cv.rotate(frame[top:top + h, left:left + w], cv.ROTATE_180)
                detections = []
                for label, confidence, bx, by, bw, bh in detector.detect(rotated):
                    detections.append([label, confidence, round(left + (WIDTH - bx - bw) * w / WIDTH),
                                       round(top + (HEIGHT - by - bh) * h / HEIGHT),
                                       round(bw * w / WIDTH), round(bh * h / HEIGHT)])
            else:
                detections = detector.detect(frame)
            rows.append((round(float(time), 3), detections))
        capture.release()
        observations[name] = rows
    return observations


def mosaic(frame, x, y, right, bottom, block=18):
    x, y = max(0, int(x)), max(0, int(y))
    right, bottom = min(WIDTH, int(right)), min(HEIGHT, int(bottom))
    if right <= x or bottom <= y:
        return
    patch = frame[y:bottom, x:right]
    tiny = cv.resize(patch, (max(1, (right-x)//block), max(1, (bottom-y)//block)), interpolation=cv.INTER_AREA)
    frame[y:bottom, x:right] = cv.resize(tiny, (right-x, bottom-y), interpolation=cv.INTER_NEAREST)


def redact(frame, name, time, detections):
    # Cover windshield, plate regions and pedestrian head locations through the entire exit cut.
    if name == "mixed":
        for label, _, x, y, w, h in detections:
            if label in (2, 7):
                mosaic(frame, x-15, y-20, x+w+24, y+h*.44, 24)
                mosaic(frame, x-18, y+h*.71, x+w+24, y+h+17, 25)
            if label == 0:
                mosaic(frame, x-12, y-15, x+w+16, y+h*.40, 22)
            if label == 3:
                mosaic(frame, x-23, y-70, x+w*.74, y+18, 22)
                mosaic(frame, x-22, y+h*.53, x+w+17, y+h+9, 23)
        # A generous moving mask spans the front number plate even between detector samples.
        if time < 14.3:
            car = max((item for item in detections if item[0] == 2), key=lambda item: item[4], default=None)
            if car:
                _, _, x, y, w, h = car
                mosaic(frame, x+w*.13, y+h*.62, x+w*.89, min(HEIGHT, y+h+35), 27)
    elif name == "bike-aisle":
        for label, _, x, y, w, h in detections:
            if label == 0:
                mosaic(frame, x-12, y-17, x+w+16, y+h*.32, 23)
            elif label == 2:
                mosaic(frame, x-6, y+h*.46, x+w+6, y+h+5, 15)


def render(directory, observations, ffmpeg):
    command = [ffmpeg, "-loglevel", "error", "-nostdin", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24",
               "-s", f"{WIDTH}x{HEIGHT}", "-r", str(FPS), "-i", "-", "-an", "-c:v", "libx264",
               "-preset", "fast", "-crf", "23", "-pix_fmt", "yuv420p", "-movflags", "+faststart",
               str(OUTPUT / "gate-real.mp4")]
    with subprocess.Popen(command, stdin=subprocess.PIPE) as writer:
        for name, start, end, _ in PARTS:
            capture = cv.VideoCapture(str(directory / (name + ".mp4")))
            source_fps = capture.get(cv.CAP_PROP_FPS)
            capture.set(cv.CAP_PROP_POS_FRAMES, round(start * source_fps))
            index, frame = 0, None
            matches = observations[name]
            for offset in range(round((end - start) * FPS)):
                target = round(offset / FPS * source_fps)
                while index <= target:
                    ok, frame = capture.read()
                    if not ok:
                        raise RuntimeError(f"Footage ended early in {name}")
                    index += 1
                time = start + offset / FPS
                nearest = min(matches, key=lambda item: abs(item[0] - time))[1]
                redacted = resized(frame)
                redact(redacted, name, time, nearest)
                if name == "car-entry" and offset == 0:
                    cv.imwrite(str(OUTPUT / "gate-real-poster.webp"), redacted)
                writer.stdin.write(redacted.tobytes())
            capture.release()
        writer.stdin.close()
        if writer.wait():
            raise RuntimeError("The reel could not be encoded")


def manifest(observations):
    timeline, duration = {}, 0.0
    chapters = []
    for name, start, end, credit in PARTS:
        timeline[name] = (duration, start)
        chapters.append({"start": duration, "end": duration + end - start, "credit": credit})
        duration += end - start
    events, tracks = [], []
    for name, time, kind, direction, track, title, classes, (start, end) in PASSAGES:
        offset, cut = timeline[name]
        samples = []
        for at, detections in observations[name]:
            if not start <= at < end:
                continue
            matches = [item for item in detections if item[0] in classes and item[4] * item[5] > 600]
            if name == "mixed":
                matches = [item for item in matches if item[3] > 100]
            if matches:
                _, confidence, x, y, w, h = max(matches, key=lambda item: item[4] * item[5])
                samples.append([round(offset + at - cut, 3), confidence, x, y, w, h])
        if len(samples) < 3:
            raise RuntimeError(f"Insufficient vehicle detections for {title}")
        close = [row for row in samples if abs(row[0] - (offset + time - cut)) < 1.8] or samples
        events.append({
            "id": track, "track": track, "source": "reviewed-footage", "time": round(offset + time - cut, 3),
            "title": title, "kind": kind, "direction": direction, "plate": None,
            "classConfidence": round(float(np.median([row[1] for row in close])), 3),
            "trackSamples": len(samples),
        })
        tracks.append({"track": track, "kind": kind, "samples": samples})
    return {"duration": duration, "chapters": chapters, "events": events, "tracks": tracks,
            "seed": {"cars": 6, "bikes": 7, "aliases": {"CF1001": "R-C02", "CF2001": "R-B02"}}}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("source_dir", type=Path)
    parser.add_argument("weights", type=Path)
    parser.add_argument("--ffmpeg", default="ffmpeg")
    args = parser.parse_args()
    cv.setNumThreads(2)
    observations = sample(args.source_dir, Detector(args.weights))
    evidence = manifest(observations)
    render(args.source_dir, observations, args.ffmpeg)
    (OUTPUT / "gate-real-trace.json").write_text(json.dumps(evidence) + "\n")
    print([(event["time"], event["direction"], event["kind"], event["classConfidence"], event["trackSamples"])
           for event in evidence["events"]])


if __name__ == "__main__":
    main()
