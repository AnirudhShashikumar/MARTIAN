"""Build the Gate A synthetic camera clip and fit the two clip-specific models.

Run with Pillow, NumPy and imageio-ffmpeg installed. The inference runtime is
shared by the offline validation command and the browser.
"""

import json
import math
from pathlib import Path
import subprocess

from imageio_ffmpeg import get_ffmpeg_exe
import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFont


ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT.parent / "prototype" / "static" / "fleet"
WIDTH, HEIGHT = 800, 450
FPS = 24
DURATION = 330
LANES = [155, 262]
GATE = WIDTH // 2
ROAD = (70, 77, 78)
PLATE_X, PLATE_Y, CELL, GLYPH_STEP = 547, 368, 4, 29
ROI = [132, 668]
FONT = {
    "C": ["01111", "11000", "10000", "10000", "10000", "11000", "01111"],
    "F": ["11111", "11000", "11000", "11110", "11000", "11000", "11000"],
    "0": ["01110", "11011", "11011", "11011", "11011", "11011", "01110"],
    "1": ["00100", "01100", "00100", "00100", "00100", "00100", "01110"],
    "2": ["01110", "11011", "00011", "00110", "01100", "11000", "11111"],
    "3": ["11110", "00011", "00011", "01110", "00011", "00011", "11110"],
    "4": ["00011", "00111", "01111", "11011", "11111", "00011", "00011"],
    "5": ["11111", "11000", "11000", "11110", "00011", "00011", "11110"],
    "6": ["01111", "11000", "11000", "11110", "11011", "11011", "01110"],
    "7": ["11111", "00011", "00110", "00110", "01100", "01100", "01100"],
    "8": ["01110", "11011", "11011", "01110", "11011", "11011", "01110"],
    "9": ["01110", "11011", "11011", "01111", "00011", "00011", "11110"],
}
PASSES = [
    (6, "Car", "Entry", "CF1101"), (14, "Bike", "Entry", "CF2101"),
    (22, "Car", "Entry", "CF1102"), (30, "Bike", "Entry", "CF2102"),
    (38, "Car", "Entry", "CF1103"), (46, "Car", "Entry", "CF1104"),
    (54, "Car", "Exit", "CF1001"), (62, "Bike", "Exit", "CF2102"),
    (70, "Car", "Entry", "CF1101"), (78, "Bike", "Entry", None),
    (86, "Car", "Exit", "CF9998"), (96, "Bike", "Exit", "CF2001"),
    (108, "Bike", "Entry", "CF2103"), (122, "Car", "Exit", "CF1102"),
    (136, "Car", "Entry", "CF1105"), (149, "Bike", "Entry", "CF2104"),
    (162, "Car", "Exit", "CF1104"), (175, "Bike", "Exit", "CF2101"),
    (188, "Car", "Entry", "CF1106"), (200, "Bike", "Entry", "CF2105"),
    (212, "Car", "Exit", "CF1103"), (224, "Car", "Entry", "CF1107"),
    (235, "Bike", "Exit", "CF2104"), (245, "Bike", "Entry", "CF2106"),
    (256, "Car", "Exit", "CF1106"), (267, "Car", "Entry", "CF1108"),
    (278, "Bike", "Exit", "CF2106"), (289, "Car", "Exit", "CF1105"),
    (300, "Car", "Entry", "CF1109"), (310, "Bike", "Entry", "CF2107"),
    (319, "Car", "Exit", "CF1101"), (326, "Bike", "Exit", "CF2103"),
]


def font(size):
    for file in ("/System/Library/Fonts/Menlo.ttc", "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"):
        if Path(file).is_file():
            return ImageFont.truetype(file, size)
    return ImageFont.load_default(size=size)


def backdrop():
    canvas = Image.new("RGB", (WIDTH, HEIGHT), "#1a302b")
    draw = ImageDraw.Draw(canvas)
    rng = np.random.default_rng(81)
    draw.rectangle((0, 93, WIDTH, 318), fill="#8d948a")
    draw.rectangle((0, 103, WIDTH, 310), fill=ROAD)
    draw.rectangle((0, 199, WIDTH, 217), fill="#596364")
    for x in range(-12, WIDTH, 60):
        draw.rounded_rectangle((x, 206, x + 33, 210), radius=2, fill="#acb4a3")
    for y in (105, 310):
        draw.line((0, y, WIDTH, y), fill="#a4b4a8", width=2)
    for x in (GATE - 12, GATE + 12):
        # Road stripes stay outside the two detection strips.
        draw.line((x, 103, x, 110), fill="#d3c47d", width=4)
        draw.line((x, 198, x, 218), fill="#d3c47d", width=4)
        draw.line((x, 307, x, 312), fill="#d3c47d", width=4)
    for y in (80, 213, 309):
        draw.rounded_rectangle((GATE - 17, y, GATE + 17, y + 14), radius=4, fill="#c0c6ba", outline="#344441")
        draw.rectangle((GATE - 6, y, GATE + 5, y + 7), fill="#e6b45e")
    for i in range(46):
        x, y = int(rng.integers(-10, 806)), int(rng.choice([20, 31, 65, 330, 412, 446]))
        radius = int(rng.integers(6, 27))
        if x < 340 or 445 < x < 484:
            shade = int(rng.integers(0, 4))
            draw.ellipse((x-radius, y-radius, x+radius, y+radius),
                         fill=("#244039", "#28453a", "#344d3d", "#2c5147")[shade])
    draw.rounded_rectangle((22, 18, 293, 78), radius=10, fill="#162924", outline="#54756a")
    draw.text((37, 30), "GATE A  /  CAMERA 01", font=font(19), fill="#f1f6ef")
    draw.text((38, 58), "SYNTHETIC CAMPUS REPLAY", font=font(10), fill="#99b8ac")
    draw.rounded_rectangle((504, 337, 772, 426), radius=12, fill="#142622", outline="#5d786f")
    draw.text((523, 348), "PLATE CAMERA  /  TEST ID", font=font(11), fill="#a6c2b6")
    draw.rounded_rectangle((28, 346, 295, 418), radius=10, fill="#162924", outline="#54756a")
    draw.text((43, 361), "ENTRY  >", font=font(14), fill="#bfdfcb")
    draw.text((151, 361), "<  EXIT", font=font(14), fill="#bfdfcb")
    draw.text((43, 393), "Gate crossing zone", font=font(11), fill="#91aea4")
    draw.text((579, 36), "BMSITM / GATE SIMULATION", font=font(12), fill="#abc3b7")
    return canvas


def sprites():
    return {label: [Image.open(path).convert("RGBA") for path in sorted((ROOT / "fleet_art").glob(f"{prefix}-*.png"))]
            for label, prefix in (("Car", "car"), ("Bike", "bike"))}


def sized(sprite, kind, scale, brightness):
    size = (132, 63) if kind == "Car" else (86, 39)
    vehicle = sprite.resize(tuple(round(value * scale) for value in size), Image.Resampling.LANCZOS)
    return ImageEnhance.Brightness(vehicle).enhance(brightness)


def features(canvas, y):
    frame = np.asarray(canvas, dtype=np.int16)
    crop = frame[y-34:y+36:2, ROI[0]:ROI[1]:2, :]
    delta = np.max(np.abs(crop - np.asarray(ROAD, dtype=np.int16)), axis=2)
    ys, xs = np.where(delta >= 33)
    width = (xs.max() - xs.min() + 1) * 2
    height = (ys.max() - ys.min() + 1) * 2
    return [width / 132, height / 68, 4 * len(xs) / (width * height), width * height / 9000, 1.0]


def fit(images, sample_art):
    rng = np.random.default_rng(121)
    train, truth, test, expected = [], [], [], []
    for label, variants in images.items():
        for index, sprite in enumerate(variants):
            for _ in range(60):
                frame = sample_art.copy()
                row = int(rng.choice(LANES))
                vehicle = sized(sprite, label, rng.uniform(.79, 1.1), rng.uniform(.8, 1.25))
                frame.paste(vehicle, (GATE - vehicle.width // 2 + int(rng.integers(-50, 50)),
                                      row - vehicle.height // 2 + int(rng.integers(-3, 4))), vehicle)
                if index == len(variants) - 1:
                    test.append(features(frame, row))
                    expected.append(float(label == "Car"))
                else:
                    train.append(features(frame, row))
                    truth.append(float(label == "Car"))

    inputs, targets = np.array(train), np.array(truth)
    weights = np.zeros(inputs.shape[1])
    for _ in range(2500):
        scores = 1 / (1 + np.exp(-np.sum(inputs * weights, axis=1)))
        weights -= .22 * (np.mean(inputs * (scores - targets)[:, None], axis=0) + .0003 * weights)
    predicted = np.sum(np.array(test) * weights, axis=1) > 0
    return weights.tolist(), int(np.sum(predicted == expected)), len(expected)


def write_clip(images, background):
    target = OUTPUT / "gate-a.mp4"
    command = [
        get_ffmpeg_exe(), "-hide_banner", "-loglevel", "error", "-nostdin", "-y", "-f", "rawvideo",
        "-pix_fmt", "rgb24", "-s", f"{WIDTH}x{HEIGHT}", "-r", str(FPS), "-i", "-",
        "-an", "-c:v", "libx264", "-threads", "4", "-preset", "fast", "-crf", "24", "-pix_fmt",
        "yuv420p", "-movflags", "+faststart", str(target),
    ]
    assets = []
    for index, (at, kind, direction, plate) in enumerate(PASSES):
        variants = images[kind]
        vehicle = sized(variants[index % len(variants)], kind, .92 + .035 * (index % 4), 1.0)
        if direction == "Exit":
            vehicle = vehicle.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
        assets.append((at, direction, plate, vehicle))

    with subprocess.Popen(command, stdin=subprocess.PIPE) as writer:
        active = 0
        empty = background.tobytes()
        for index in range(DURATION * FPS):
            time = index / FPS
            while active + 1 < len(assets) and time > assets[active][0] + 3.15:
                active += 1
            at, direction, plate, vehicle = assets[active]
            offset = time - at
            if abs(offset) > 3.15:
                writer.stdin.write(empty)
                continue
            y = LANES[0 if direction == "Entry" else 1]
            center = GATE + (1 if direction == "Entry" else -1) * offset * 155
            frame = background.copy()
            frame.paste(vehicle, (round(center - vehicle.width / 2), y - vehicle.height // 2), vehicle)
            if plate and abs(offset) <= 1.26:
                draw = ImageDraw.Draw(frame)
                draw.rounded_rectangle((PLATE_X-10, PLATE_Y-6, PLATE_X+175, PLATE_Y+34), radius=5, fill="#f5f8ed")
                for col, letter in enumerate(plate):
                    for row, glyph_row in enumerate(FONT[letter]):
                        for column, pixel in enumerate(glyph_row):
                            if pixel == "1":
                                x, y = PLATE_X + col * GLYPH_STEP + column * CELL, PLATE_Y + row * CELL
                                draw.rectangle((x, y, x + CELL - 1, y + CELL - 1), fill="#101d19")
            writer.stdin.write(frame.tobytes())
        writer.stdin.close()
        if writer.wait():
            raise RuntimeError("FFmpeg could not encode the gate clip")


def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    background = backdrop()
    background.save(OUTPUT / "gate-poster.webp", quality=86)
    images = sprites()
    weights, correct, total = fit(images, background)
    model = {
        "size": [WIDTH, HEIGHT], "lanes": LANES, "roi": ROI, "gate": GATE, "road": ROAD,
        "plate": [PLATE_X, PLATE_Y, CELL, GLYPH_STEP], "duration": DURATION,
        "vehicle": {"weights": weights, "holdout": [correct, total]},
        "glyphs": {key: "".join(rows) for key, rows in FONT.items()},
    }
    (OUTPUT / "gate-model.json").write_text(json.dumps(model, indent=2) + "\n")
    (ROOT / "gate-expected.json").write_text(json.dumps(PASSES, indent=2) + "\n")
    write_clip(images, background)
    print(f"Built {DURATION}s gate clip, class holdout {correct}/{total} synthetic sprite samples.")


if __name__ == "__main__":
    main()
