import { bays } from "./parking-agent.mjs";

const reducedMotion = matchMedia("(prefers-reduced-motion: reduce)");
const routeDuration = 2.35;
const mono = "ui-monospace, monospace";
const paint = ["#38bdf8", "#a78bfa", "#34d399", "#fbbf24", "#f472b6"];
const cameras = [
  { id: "CAM-1", point: [50.08, 82.08], angle: 90, spread: 76, reach: 70 },
  { id: "CAM-2", point: [59.18, 58.73], angle: -28, spread: 64, reach: 99 },
  { id: "CAM-3", point: [28.16, 66.98], angle: -118, spread: 64, reach: 95 },
];

export function mapMarkup() {
  return `<article class="fleet-card fleet-map-card" aria-label="Campus parking map and bay usage">
    <header class="fleet-card-head"><div><h3>Campus parking map</h3><p>Gate A · Synchronized simulation</p></div></header>
    <div class="fleet-map-stage">
      <img src="/static/campus-parking-map.webp" width="1264" height="848"
        alt="Campus parking layout with Gate A, the bike lot, car lot and second bike zone.">
      <canvas class="fleet-map-model" width="1000" height="671" aria-hidden="true"></canvas>
      <div class="fleet-map-story" data-fleet="map-status" role="status">Awaiting a gate crossing</div>
      <div class="fleet-map-sign" data-fleet="map-sign">
        <span class="fleet-map-sign-head">SIGN_JUNCTION · LIVE</span>
        <span data-fleet="map-sign-first">BIKE LOT 1: OPEN (LEFT)</span>
        <span data-fleet="map-sign-second">CAR LOT: OPEN (RIGHT)</span>
      </div>
      <span class="fleet-map-destination" data-fleet="map-overflow" hidden>OVERFLOW ↗</span>
      <span class="fleet-map-destination fleet-map-zone-two" data-fleet="map-zone-two" hidden>BIKE ZONE 2 →</span>
      <div class="fleet-map-gate" aria-label="Entry and exit lanes"><span>ENTRY ▲</span><span>▼ EXIT</span></div>
    </div>
    <div class="fleet-legend"><span><i class="legend-free"></i> Free</span><span><i class="legend-used"></i> Parked</span>
      <span><i class="legend-overflow"></i> Overflow</span><span><i class="legend-protected"></i> Accessible / reserved</span>
      <span><i class="legend-camera"></i> Cameras</span></div>
  </article>`;
}

function routeFor(bay, direction) {
  const leaving = direction === "Exit";
  const lane = leaving ? 52.7 : 47.3;
  const points = [[lane, 97], [lane, 83.25], [leaving ? 52.4 : 48.1, 66]];
  if (bay.id.startsWith("OC")) {
    points.push([48.6, 43], [48.6, 6.4], [56.6, 5.7], [bay.point[0], 5.4]);
  } else if (bay.id.startsWith("OB")) {
    points.push([54.6, 63], [59.5, 62], [61.6, 64.6], [64.1, 66.8], [70.7, 69.7]);
  } else if (bay.kind === "Bike") {
    points.push([42.7, 68.6], [30.1, 70.5], [22.1, 71.7], [22, 58], [bay.point[0] + 2.7, bay.point[1]]);
  } else {
    points.push([54.6, 63], [59.5, 62], [62, 63.7], [67.2, 66.3], [72.8, 63.8], [72.8, bay.point[1]]);
  }
  points.push(bay.point);
  return leaving ? points.reverse() : points;
}

function progressPoint(points, progress, heightRatio) {
  const segments = points.slice(1).map(([x, y], index) =>
    Math.hypot(x - points[index][0], (y - points[index][1]) * heightRatio));
  let distance = progress * segments.reduce((sum, value) => sum + value, 0);
  for (let index = 0; index < segments.length; index++) {
    if (distance <= segments[index] || index === segments.length - 1) {
      const at = segments[index] ? Math.min(1, distance / segments[index]) : 0;
      return points[index].map((value, axis) => value + (points[index + 1][axis] - value) * at);
    }
    distance -= segments[index];
  }
  return points.at(-1);
}

function drawRoute(drawing, points, accent, elapsed) {
  drawing.save();
  drawing.beginPath();
  points.forEach(([x, y], index) => drawing[index ? "lineTo" : "moveTo"](x, y));
  drawing.strokeStyle = accent;
  drawing.lineCap = "round";
  drawing.lineJoin = "round";
  drawing.lineWidth = 7;
  drawing.globalAlpha = .24;
  drawing.stroke();

  drawing.globalAlpha = 1;
  drawing.lineWidth = 2.8;
  drawing.shadowBlur = 5;
  drawing.shadowColor = accent;
  drawing.setLineDash([10, 8]);
  drawing.lineDashOffset = -18 * elapsed;
  drawing.stroke();
  drawing.restore();
}

function drawVehicleMarker(drawing, x, y, angle, kind, identifier, accent, parked = false, tagColor = accent) {
  drawing.save();
  drawing.translate(x, y);
  drawing.save();
  drawing.rotate(angle);
  drawing.strokeStyle = "#0b0f17";
  drawing.lineWidth = 1.3;
  const fillRounded = (left, top, width, height, radius) => {
    drawing.beginPath();
    drawing.roundRect(left, top, width, height, radius);
    drawing.fill();
  };
  const light = (left, top, radius, color) => {
    drawing.fillStyle = color;
    drawing.beginPath();
    drawing.arc(left, top, radius, 0, 2 * Math.PI);
    drawing.fill();
  };

  drawing.fillStyle = accent;
  if (kind === "Car") {
    drawing.fillStyle = "#05080e73";
    fillRounded(-14.8, -6.9, 32, 17, 4.5);
    drawing.fillStyle = accent;
    fillRounded(-16, -8.5, 32, 17, 4.5);
    drawing.stroke();
    drawing.fillStyle = "#0f172ad6";
    fillRounded(2, -6, 6.5, 12, 1.8);
    drawing.fillStyle = "#0f172ab8";
    fillRounded(-11, -5.5, 5, 11, 1.4);
    light(14.5, -5, 1.7, "#fef08a");
    light(14.5, 5, 1.7, "#fef08a");
  } else {
    fillRounded(-9.5, -3.8, 19, 7.6, 3.2);
    drawing.stroke();
    drawing.strokeStyle = "#e2e8f0";
    drawing.lineCap = "round";
    drawing.lineWidth = 1.6;
    drawing.beginPath();
    drawing.moveTo(3.5, -5.2);
    drawing.lineTo(3.5, 5.2);
    drawing.stroke();
    light(-1, 0, 3, "#f8fafc");
    drawing.strokeStyle = "#0b0f17";
    drawing.lineWidth = .9;
    drawing.stroke();
    light(9, 0, 1.5, "#fef08a");
  }
  drawing.restore();

  if (parked && kind === "Bike") {
    drawing.restore();
    return;
  }
  const label = parked ? identifier.slice(-3) : identifier;
  const top = parked ? -6.5 : -29;
  const height = parked ? 13 : 16;
  drawing.font = `800 ${parked ? 9 : 13}px ui-monospace, monospace`;
  const width = drawing.measureText(label).width + (parked ? 4 : 12);
  drawing.fillStyle = "#080b11eb";
  fillRounded(-width / 2, top, width, height, 3);
  drawing.strokeStyle = tagColor;
  drawing.lineWidth = 1.2;
  drawing.stroke();
  drawing.fillStyle = "#f8fafc";
  drawing.textAlign = "center";
  drawing.textBaseline = "middle";
  drawing.fillText(label, 0, top + height / 2);
  drawing.restore();
}

function drawBay(drawing, bay, parked, incoming, [x, y]) {
  const car = bay.kind === "Car";
  const angle = car ? 0 : .18;
  const [width, height] = car ? [37, 20] : [19, 10];
  const protectedBay = bay.policy === "Accessible" || bay.policy === "Reserved";
  const state = incoming ? ["#fbbf24", "#f59e0b42"] :
    parked ? ["#f87171", "#ef444447"] :
    protectedBay ? ["#38bdf8", "#38bdf846"] : ["#10b981", "#10b98138"];

  drawing.save();
  drawing.translate(x, y);
  drawing.rotate(angle);
  drawing.beginPath();
  drawing.roundRect(-width / 2, -height / 2, width, height, 2.5);
  drawing.fillStyle = state[1];
  drawing.fill();
  drawing.strokeStyle = state[0];
  drawing.lineWidth = 1.35;
  if (incoming || bay.policy === "Reserved") drawing.setLineDash([3, 2]);
  drawing.stroke();
  if (protectedBay) {
    drawing.fillStyle = "#dff5ff";
    drawing.textAlign = "center";
    drawing.textBaseline = "middle";
    drawing.font = `800 11px ${mono}`;
    drawing.fillText(bay.policy === "Accessible" ? "♿" : "R", 0, 0);
  }
  drawing.restore();
  if (parked && !incoming) {
    const shade = Number(bay.id.slice(-2)) % paint.length;
    drawVehicleMarker(drawing, x, y, angle, bay.kind, parked.plate, paint[shade], true);
  }
}

function drawCamera(drawing, camera, [x, y], active) {
  const angle = Math.PI / 180;
  const left = (camera.angle - camera.spread / 2) * angle;
  const right = (camera.angle + camera.spread / 2) * angle;
  const color = active ? "#fbbf24" : "#38bdf8";

  drawing.save();
  drawing.beginPath();
  drawing.moveTo(x, y);
  drawing.arc(x, y, camera.reach, left, right);
  drawing.closePath();
  drawing.fillStyle = active ? "#fbbf2445" : "#38bdf826";
  drawing.fill();
  drawing.strokeStyle = active ? "#fbbf24b8" : "#38bdf880";
  drawing.lineWidth = 1;
  drawing.setLineDash([2.5, 3]);
  drawing.stroke();
  drawing.setLineDash([]);

  drawing.beginPath();
  drawing.arc(x, y, 9, 0, 2 * Math.PI);
  drawing.fillStyle = "#0b111e";
  drawing.fill();
  drawing.strokeStyle = color;
  drawing.lineWidth = 1.7;
  drawing.stroke();

  drawing.fillStyle = active ? "#fde68a" : "#bae6fd";
  drawing.beginPath();
  drawing.roundRect(x - 5, y - 2.75, 6.5, 5.5, 1);
  drawing.fill();
  drawing.beginPath();
  drawing.moveTo(x + 1, y - 1);
  drawing.lineTo(x + 5, y - 2.75);
  drawing.lineTo(x + 5, y + 2.75);
  drawing.lineTo(x + 1, y + 1);
  drawing.fill();

  const [tagX, tagY] = camera.id === "CAM-1" ? [x + 30, y] : [x, y - 14];
  drawing.beginPath();
  drawing.roundRect(tagX - 18, tagY - 5.5, 36, 11, 2.5);
  drawing.fillStyle = "#101929";
  drawing.fill();
  drawing.lineWidth = 1;
  drawing.stroke();
  drawing.fillStyle = active ? "#fde68a" : "#bae6fd";
  drawing.font = `800 8px ${mono}`;
  drawing.textAlign = "center";
  drawing.textBaseline = "middle";
  drawing.fillText(camera.id, tagX, tagY);
  drawing.restore();
}

function drawSignPin(drawing, xy) {
  const [x, y] = xy([45.49, 59.9]);
  const [fromX, fromY] = xy([43.8, 57.05]);
  drawing.save();
  drawing.strokeStyle = "#f59e0b";
  drawing.lineWidth = 1.65;
  drawing.setLineDash([2.4, 2]);
  drawing.beginPath();
  drawing.moveTo(fromX, fromY);
  drawing.lineTo(x, y);
  drawing.stroke();
  drawing.setLineDash([]);
  drawing.beginPath();
  drawing.arc(x, y, 5.1, 0, 2 * Math.PI);
  drawing.fillStyle = "#0e121b";
  drawing.fill();
  drawing.stroke();
  drawing.beginPath();
  drawing.arc(x, y, 2.1, 0, 2 * Math.PI);
  drawing.fillStyle = "#fbbf24";
  drawing.fill();
  drawing.restore();
}

function updateSign(context, parked) {
  const { fields, run } = context;
  const last = run.log.at(-1);
  const id = last?.track ?? last?.plate;
  const motion = last?.motion[0];
  let story = "Awaiting a gate crossing";
  if (motion?.direction === "Exit") {
    story = `${motion.plate} exiting → ${motion.bay} released`;
    if (last.motion[1]) story += ` · ${last.motion[1].plate} routed in`;
  } else if (last?.action === "Overflow assigned") {
    story = `Overflow assigned · ${motion.plate} → ${motion.bay}`;
  } else if (motion) {
    story = `${motion.plate} entering → ${motion.bay}`;
  } else if (last) {
    story = [id, last.action].filter(Boolean).join(" · ");
  }
  fields["map-status"].textContent = story;
  fields["map-status"].dataset.tone = last?.action === "Overflow assigned" ? "amber" :
    last && !motion ? "red" : "green";

  const hasFree = (kind, policy) => bays.some((bay) =>
    bay.kind === kind && bay.policy === policy && !parked.has(bay.id));
  const carFull = !hasFree("Car", "General");
  const bikeFull = !hasFree("Bike", "General");
  const carReserve = hasFree("Car", "Overflow reserve");
  const bikeReserve = hasFree("Bike", "Overflow reserve");

  let first = "BIKE LOT 1: OPEN (LEFT)";
  let second = "CAR LOT: OPEN (RIGHT)";
  let tone = "green";
  if (bikeFull) {
    first = bikeReserve ? "BIKE LOT 1: FULL → ZONE 2" : "BIKE LOTS FULL → WAIT";
    tone = bikeReserve ? "amber" : "red";
  }
  if (carFull) {
    second = carReserve ? "CAR LOT: FULL → OVERFLOW ↗" : "CAR LOTS FULL → WAIT";
    tone = carReserve && tone !== "red" ? "amber" : "red";
  }
  if (carFull && carReserve && !bikeFull && last?.action === "Overflow assigned" && last.kind === "Car") {
    first = "CAR LOT: FULL → OVERFLOW";
    second = "STRAIGHT AHEAD → TURN RIGHT ↗";
  }
  fields["map-sign-first"].textContent = first;
  fields["map-sign-second"].textContent = second;
  fields["map-sign"].dataset.tone = tone;
  fields["map-overflow"].hidden = !carFull || !carReserve;
  fields["map-zone-two"].hidden = !bikeFull || !bikeReserve;
}

// Read the ledger and media clock without making any allocation decisions here.
export function drawMap(context, time) {
  const drawing = context.mapLayer;
  const { width, height } = drawing.canvas;
  const xy = ([x, y]) => [x / 100 * width, y / 100 * height];
  const parked = new Map(Object.values(context.run.records).filter((record) => record.status === "Parked")
    .map((record) => [record.bay, record]));

  if (context.mapRun !== context.run) {
    updateSign(context, parked);
    context.mapRun = context.run;
  }

  const movements = [];
  if (!reducedMotion.matches) {
    for (const event of context.run.log.slice(-2)) {
      event.motion.forEach((motion, index) => {
        const start = event.time + index * .25;
        const duration = Math.max(.25, Math.min(routeDuration, context.trace.duration - start));
        const elapsed = time - start;
        const progress = elapsed / duration;
        if (progress < 0 || progress > 1) return;
        const bay = bays.find((candidate) => candidate.id === motion.bay);
        const points = routeFor(bay, motion.direction);
        const accent = bay.policy === "Overflow reserve" && motion.direction === "Entry" ?
          (motion.kind === "Car" ? "#f59e0b" : "#38bdf8") :
          motion.direction === "Exit" ? "#fbbf24" : motion.kind === "Car" ? "#38bdf8" : "#34d399";
        const point = (progress) => xy(progressPoint(points, progress, height / width));
        const [fromX, fromY] = point(Math.max(0, progress - .011));
        const [toX, toY] = point(Math.min(1, progress + .011));
        movements.push({ ...motion, route: points.map(xy), elapsed, accent, point: point(progress),
          angle: Math.atan2(toY - fromY, toX - fromX) });
      });
    }
  }

  drawing.clearRect(0, 0, width, height);
  for (const motion of movements) drawRoute(drawing, motion.route, motion.accent, motion.elapsed);
  for (const bay of bays) {
    const record = parked.get(bay.id);
    const incoming = movements.some((motion) =>
      motion.direction === "Entry" && motion.bay === bay.id && motion.plate === record?.plate);
    drawBay(drawing, bay, record, incoming, xy(bay.point));
  }
  const last = context.run.log.at(-1);
  const crossing = last && time >= last.time && time < last.time + .42 && !reducedMotion.matches;
  for (const camera of cameras) {
    const [x, y] = xy(camera.point);
    const nearby = movements.some((motion) => Math.hypot(motion.point[0] - x, motion.point[1] - y) < 30);
    drawCamera(drawing, camera, [x, y], nearby || (camera.id === "CAM-1" && crossing));
  }
  for (const motion of movements) {
    const color = motion.kind === "Car" ? "#38bdf8" : "#34d399";
    drawVehicleMarker(drawing, ...motion.point, motion.angle, motion.kind, motion.plate, color, false, motion.accent);
  }
  drawSignPin(drawing, xy);
}
