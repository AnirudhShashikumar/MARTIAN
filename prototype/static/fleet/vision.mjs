// Pixel-level inference for the calibrated Gate A camera. Shared by browser and clip verifier.
function likelihood(features, weights) {
  const value = features.reduce((total, feature, index) => total + feature * weights[index], 0);
  return 1 / (1 + Math.exp(-value));
}

export function detectVehicle(frame, stride, model, lane) {
  const [width] = model.size;
  const [left, right] = model.roi;
  const [red, green, blue] = model.road;
  let lowX = right, lowY = lane + 36, highX = left, highY = lane - 34, count = 0;
  for (let y = lane - 34; y < lane + 36; y += 2) {
    for (let x = left; x < right; x += 2) {
      const pixel = (y * width + x) * stride;
      if (Math.max(Math.abs(frame[pixel] - red), Math.abs(frame[pixel + 1] - green),
        Math.abs(frame[pixel + 2] - blue)) < 33) continue;
      lowX = Math.min(x, lowX);
      highX = Math.max(x, highX);
      lowY = Math.min(y, lowY);
      highY = Math.max(y, highY);
      count++;
    }
  }
  if (count < 52) return null;
  const boxWidth = highX - lowX + 2;
  const boxHeight = highY - lowY + 2;
  const area = boxWidth * boxHeight;
  const car = likelihood([boxWidth / 132, boxHeight / 68, count * 4 / area, area / 9000, 1], model.vehicle.weights);
  return { x: lowX + boxWidth / 2, box: [lowX, lowY, boxWidth, boxHeight], car,
    kind: car >= 0.5 ? "Car" : "Bike", confidence: Math.max(car, 1 - car) };
}

function brightness(frame, stride, width, x, y) {
  const start = (y * width + x) * stride;
  return (frame[start] + frame[start + 1] + frame[start + 2]) / 3;
}

export function readPlate(frame, stride, model) {
  const [width] = model.size;
  const [left, top, cell, step] = model.plate;
  if (brightness(frame, stride, width, left - 5, top + 10) < 185) return null;

  let plate = "";
  let errors = 0;
  for (let index = 0; index < 6; index++) {
    let glyph = "";
    for (let row = 0; row < 7; row++) {
      for (let column = 0; column < 5; column++) {
        const x = left + index * step + column * cell + Math.floor(cell / 2);
        const y = top + row * cell + Math.floor(cell / 2);
        glyph += brightness(frame, stride, width, x, y) < 115 ? "1" : "0";
      }
    }
    const alphabet = index < 2 ? ["C", "F"] : [..."0123456789"];
    const choices = alphabet.map((character) => ({
      character, distance: [...glyph].filter((pixel, position) => pixel !== model.glyphs[character][position]).length,
    })).sort((first, second) => first.distance - second.distance);
    const [best, next] = choices;
    if (best.distance > 4 || next.distance - best.distance < 2) return null;
    plate += best.character;
    errors += best.distance;
  }
  return /^CF\d{4}$/.test(plate) ? { plate, confidence: 1 - errors / 210 } : null;
}

export class GateVision {
  constructor(model) {
    this.model = model;
    this.reset();
  }

  reset() {
    this.tracks = this.model.lanes.map(() => null);
  }

  scan(frame, time, stride = 4) {
    const { model } = this;
    const visible = model.lanes.map((lane) => detectVehicle(frame, stride, model, lane));
    const reading = visible.filter(Boolean).length === 1 ? readPlate(frame, stride, model) : null;
    const events = [];
    const readings = [];

    visible.forEach((vehicle, lane) => {
      let track = this.tracks[lane];
      if (!vehicle) {
        if (track && time - track.seen > .5) this.tracks[lane] = null;
        return;
      }
      if (!track || time - track.seen > 1.2 || Math.abs(vehicle.x - track.x) > 195) {
        track = { seen: time, x: vehicle.x, left: false, right: false, counted: false,
          scores: [], plates: new Map() };
        this.tracks[lane] = track;
      }

      track.seen = time;
      track.x = vehicle.x;
      if (Math.abs(vehicle.x - model.gate) < 107) {
        track.scores.push(vehicle.car);
        if (reading) {
          const agreement = track.plates.get(reading.plate) ?? { count: 0, confidence: 0 };
          track.plates.set(reading.plate, { count: agreement.count + 1, confidence: reading.confidence });
        }
      }
      readings.push({ ...vehicle, reading });
      const left = vehicle.x < model.gate - 24;
      const right = vehicle.x > model.gate + 24;
      const direction = right && track.left ? "Entry" : left && track.right ? "Exit" : null;
      track.left ||= left;
      track.right ||= right;
      if (!direction || track.counted || track.scores.length < 3) return;

      track.counted = true;
      const car = track.scores.reduce((total, value) => total + value, 0) / track.scores.length;
      const [best, next] = [...track.plates].sort((first, second) => second[1].count - first[1].count);
      const plate = best && best[1].count >= 2 && (!next || best[1].count > next[1].count) ? best : null;
      events.push({
        id: `gate-${lane}-${Math.round(time * 1000)}`, time: Number(time.toFixed(3)), direction,
        kind: car >= .5 ? "Car" : "Bike", classConfidence: Math.max(car, 1 - car),
        plate: plate?.[0] ?? null, plateConfidence: plate?.[1].confidence ?? null,
        plateSamples: plate?.[1].count ?? 0, box: vehicle.box,
      });
    });
    return { readings, events };
  }
}
