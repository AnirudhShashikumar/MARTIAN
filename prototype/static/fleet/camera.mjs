import { GateVision } from "./vision.mjs";
import { act, bays, newRun } from "./parking-agent.mjs";
import { drawMap, mapMarkup } from "./parking-map.mjs";

const folder = "/static/fleet/";
const reducedMotion = matchMedia("(prefers-reduced-motion: reduce)");
const colors = { Car: "#7ab5ff", Bike: "#6fe3b3", review: "#f6bc73" };
let mounted;

const esc = (value) => String(value ?? "").replace(/[&<>"']/g, (char) => ({
  "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
})[char]);
const score = (value) => Number.isFinite(value) ? `${Math.round(value * 100)}%` : "—";
const timestamp = (time) => {
  const seconds = Math.max(0, Math.floor(time || 0));
  return `${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, "0")}`;
};

function markup() {
  return `<section class="fleet-camera" aria-labelledby="gate-camera-title">
    <div class="fleet-replay-head">
      <div><p class="fleet-source"><span></span> <span class="fleet-source-text" data-fleet="source-title">Gate A · Real footage</span></p>
        <h2 id="gate-camera-title">Gate operations</h2>
        <p class="fleet-sub" data-fleet="intro">Real entry and exit footage with a synchronized campus parking simulation.</p></div>
      <div class="fleet-replay-actions">
        <button type="button" class="button primary" data-camera="start" disabled>Play footage</button>
        <a class="button secondary" href="#fleet-incident">Shared incident</a>
      </div>
    </div>
    <div class="fleet-stats" data-fleet="stats"></div>
    <div class="fleet-views">
      <article class="fleet-card" aria-label="Gate A camera">
        <header class="fleet-card-head"><div><h3>Gate camera</h3><p data-fleet="mode">Loading camera footage…</p></div>
          <span class="fleet-camera-status" data-fleet="clock">0:00</span></header>
        <div class="gate-picture">
          <video preload="auto" muted playsinline controls aria-label="Parking entry and exit footage"
            width="800" height="450"></video>
          <canvas class="gate-detection" width="800" height="450" aria-hidden="true"></canvas>
        </div>
        <div class="gate-inference" aria-label="Model outputs">
          <div><span>Vehicle model</span><strong data-fleet="vehicle">Awaiting vehicle</strong></div>
          <div><span data-fleet="identity-label">Anonymous vehicle ID</span><strong data-fleet="plate">Awaiting vehicle</strong></div>
          <div><span>Policy agent</span><strong data-fleet="agent">Ready</strong></div>
        </div>
        <div class="fleet-transport"><label>Camera feed <select data-camera="source" disabled>
          <option value="real">Real footage</option><option value="test">Synthetic model test</option>
        </select></label><label>Jump to <select data-camera="jump" disabled><option value="">Choose event</option></select></label>
        <label>Speed <select data-camera="speed" disabled><option value="1">1×</option><option value="1.5">1.5×</option><option value="2">2×</option></select></label>
        <button type="button" class="button ghost" data-camera="restart" disabled>Restart clip</button></div>
        <p class="fleet-card-note" data-fleet="credit"></p>
      </article>
      ${mapMarkup()}
    </div>
    <article class="fleet-card fleet-ledger">
      <header class="fleet-card-head"><div><h3>Gate decisions</h3><p data-fleet="summary">The ledger updates as vehicles cross.</p></div>
        <button type="button" class="button secondary" data-camera="export" disabled>Export CSV</button></header>
      <div class="fleet-table-wrap"><table class="fleet-table"><thead><tr>
        <th scope="col">Clip time</th><th scope="col">Movement</th><th scope="col">Vehicle</th><th scope="col" data-fleet="table-identity">Track ID</th>
        <th scope="col">Bay</th><th scope="col">Decision</th><th scope="col">Policy check</th>
      </tr></thead><tbody data-fleet="rows"><tr><td colspan="7">Awaiting a gate crossing.</td></tr></tbody></table></div>
      <p class="fleet-card-note">Automatic overflow uses only designated reserve bays. Accessible and reserved bays have separate eligibility rules.</p>
    </article>
    <p class="fleet-camera-problem" data-fleet="error" role="alert" hidden></p>
  </section>`;
}

async function json(name, signal) {
  const response = await fetch(folder + name, { signal });
  if (!response.ok) throw Error("The local replay assets could not load. Refresh the parking overview.");
  return response.json();
}

function assetStats(context) {
  const vehicles = Object.values(context.run.records);
  const used = vehicles.filter((row) => row.status === "Parked");
  const free = (kind, policy) => bays.filter((bay) => bay.kind === kind && bay.policy === policy &&
    !used.some((row) => row.bay === bay.id)).length;
  const waiting = vehicles.filter((row) => row.status === "Waiting").length;
  const reserve = free("Car", "Overflow reserve") + free("Bike", "Overflow reserve");
  return [
    ["Car lot", free("Car", "General"), "free general bays"],
    ["Bike lot", free("Bike", "General"), "free general bays"],
    ["Overflow", reserve, "reserve bays free"],
    ["Gate queue", waiting, waiting === 1 ? "vehicle waiting" : "vehicles waiting"],
  ];
}

function updateLedger(context) {
  const { run, fields } = context;
  fields.stats.innerHTML = assetStats(context).map(([label, total, suffix]) =>
    `<div><span>${label}</span><strong>${total}</strong><small>${suffix}</small></div>`).join("");
  const last = run.log.at(-1);
  const review = run.log.filter((event) => event.action === "Review").length;
  const decisions = run.log.length;
  fields.summary.textContent = decisions ?
    `${decisions} gate decisions · ${review} held for staff review` : "The ledger updates as vehicles cross.";
  fields.rows.innerHTML = decisions ? [...run.log].reverse().map((event) =>
    `<tr><td>${timestamp(event.time)}</td><td>${event.direction}</td>
      <td>${event.kind} <small>${score(event.classConfidence)}</small></td>
      <td class="fleet-registration">${esc(event.track ?? event.plate ?? "Unreadable")} <small>${event.track ? "" : score(event.plateConfidence)}</small></td>
      <td>${esc(event.bay ?? "—")}</td>
      <td><span class="fleet-decision ${event.action === "Review" || event.action === "Waitlisted" ? "is-held" : ""}">${esc(event.action)}</span></td>
      <td>${esc(event.title ? `${event.title}. ${event.reason}` : event.reason)}</td></tr>`).join("") : '<tr><td colspan="7">Awaiting a gate crossing.</td></tr>';
  fields.agent.textContent = last?.action ?? "Ready";
  context.shell.querySelector('[data-camera="export"]').disabled = !decisions;
}

function drawScan(context, readings) {
  const drawing = context.scanLayer;
  const [width, height] = context.model.size;
  drawing.clearRect(0, 0, width, height);
  if (!readings.length) return;
  drawing.textBaseline = "top";
  drawing.font = "bold 15px system-ui";
  drawing.lineWidth = 2;
  if (context.source === "test") {
    drawing.setLineDash([6, 5]);
    drawing.strokeStyle = "#e6f2dfad";
    drawing.beginPath();
    drawing.moveTo(context.model.gate, 105);
    drawing.lineTo(context.model.gate, 307);
    drawing.stroke();
    drawing.setLineDash([]);
  }
  for (const hit of readings) {
    const [x, y, w, h] = hit.box;
    drawing.strokeStyle = colors[hit.kind];
    drawing.strokeRect(x - 3, y - 3, w + 6, h + 6);
    const label = `${hit.kind.toUpperCase()}  ${score(hit.confidence)}`;
    drawing.fillStyle = "#142722";
    drawing.fillRect(x - 3, y - 23, drawing.measureText(label).width + 15, 20);
    drawing.fillStyle = colors[hit.kind];
    drawing.fillText(label, x + 3, y - 21);
  }
}

function updateReadings(context, readings) {
  const best = readings.find((reading) => reading.reading) ?? readings[0];
  const last = context.run.log.at(-1);
  context.fields.vehicle.textContent = best ? `${best.kind} · ${score(best.confidence)}` :
    last ? `${last.kind} · ${score(last.classConfidence)}` : "Awaiting vehicle";
  if (context.source === "real") {
    context.fields.plate.textContent = best?.track ?? last?.track ?? "Awaiting vehicle";
    return;
  }
  context.fields.plate.textContent = best?.reading ? `${best.reading.plate} · ${score(best.reading.confidence)}` :
    last ? (last.plate ?? "Unreadable") : "Awaiting scan";
  if (best && !best.reading && Math.abs(best.x - context.model.gate) < 103) {
    context.fields.plate.textContent = "Reading test plate…";
  }
}

function fresh(context, mode) {
  context.run = newRun(context.trace.seed);
  context.engine.reset();
  context.cursor = 0;
  context.lastSample = -1;
  context.mode = mode;
  context.fields.mode.textContent = mode === "footage" ? "Reviewed YOLOX tracks · footage-time replay" : mode === "live"
    ? "Models reading frames locally · no API key"
    : "Verified inference replay · synchronized to clip time";
  drawScan(context, []);
  updateReadings(context, []);
  updateLedger(context);
  drawMap(context, context.video.currentTime);
}

function replayTo(context, time) {
  if (context.cursor && context.trace.events[context.cursor - 1].time > time) fresh(context, context.mode);
  let changed = false;
  while (context.cursor < context.trace.events.length && context.trace.events[context.cursor].time <= time) {
    context.run = act(context.run, context.trace.events[context.cursor++]);
    changed = true;
  }
  if (changed) {
    updateLedger(context);
    updateReadings(context, []);
  }
}

function footageReadings(trace, time) {
  return trace.tracks.flatMap(({ track, kind, samples }) => {
    const right = samples.findIndex((sample) => sample[0] >= time);
    const next = samples[right];
    const previous = samples[right === -1 ? samples.length - 1 : right - 1];
    const nearest = [previous, next].filter(Boolean).sort((a, b) => Math.abs(a[0] - time) - Math.abs(b[0] - time))[0];
    if (!nearest || Math.abs(nearest[0] - time) > .32) return [];
    let box = nearest.slice(2);
    if (previous && next && next[0] - previous[0] < .6) {
      const fraction = (time - previous[0]) / (next[0] - previous[0]);
      box = next.slice(2).map((value, index) => previous[index + 2] + (value - previous[index + 2]) * fraction);
    }
    return [{ track, kind, box, confidence: nearest[1] }];
  });
}

function tick(context, time) {
  const timeLabel = `${timestamp(time)} / ${timestamp(context.trace.duration)}`;
  if (context.fields.clock.textContent !== timeLabel) context.fields.clock.textContent = timeLabel;
  if (context.video.seeking) return;
  if (context.mode === "footage") {
    replayTo(context, time);
    const chapter = context.trace.chapters.find((part) => time >= part.start && time < part.end);
    if (chapter && context.fields.credit.textContent !== chapter.credit) context.fields.credit.textContent = chapter.credit;
    const readings = footageReadings(context.trace, time);
    drawScan(context, readings);
    updateReadings(context, readings);
    drawMap(context, time);
    return;
  }
  if (context.mode === "replay") {
    replayTo(context, time);
  }
  if (context.video.readyState >= 2 && time - context.lastSample > .1) {
    context.lastSample = time;
    context.frame.drawImage(context.video, 0, 0, ...context.model.size);
    const frame = context.frame.getImageData(0, 0, ...context.model.size);
    const result = context.engine.scan(frame.data, time);
    if (context.mode === "live" && result.events.length) {
      for (const event of result.events) context.run = act(context.run, event);
      updateLedger(context);
    }
    drawScan(context, result.readings);
    updateReadings(context, result.readings);
  }
  drawMap(context, time);
}

function report(context, message) {
  context.fields.error.textContent = message;
  context.fields.error.hidden = false;
}

function schedule(context) {
  const callback = (_, metadata) => {
    if (mounted !== context) return;
    try {
      tick(context, metadata?.mediaTime ?? context.video.currentTime);
      schedule(context);
    } catch {
      context.video.pause();
      report(context, "Frame analysis paused. Choose an event to inspect the verified replay.");
    }
  };
  if (typeof context.video.requestVideoFrameCallback === "function") {
    context.callback = context.video.requestVideoFrameCallback(callback);
  } else {
    context.callback = requestAnimationFrame(callback);
  }
}

function exportLedger(context) {
  const quote = (value) => '"' + String(value ?? "").replaceAll('"', '""') + '"';
  const rows = context.run.log.map((event) => [
    event.time, event.direction, event.kind, event.track ?? event.plate, event.bay, event.action, event.reason,
  ].map(quote).join(","));
  const link = document.createElement("a");
  const csv = "clip_seconds,direction,vehicle,vehicle_id,bay,decision,policy\n" + rows.join("\n");
  link.href = URL.createObjectURL(new Blob([csv], { type: "text/csv" }));
  link.download = "campusflow-gate-a.csv";
  link.click();
  setTimeout(() => URL.revokeObjectURL(link.href), 1000);
}

function play(context) {
  context.video.play().catch(() => report(context, "Select play on the video to start the clip."));
}

function showCameras(context) {
  context.shell.querySelector(".fleet-views").scrollIntoView({ block: "start",
    behavior: reducedMotion.matches ? "instant" : "smooth" });
}

function playLabel(context) {
  return context.source === "real" ? "Play footage" : "Play & analyze";
}

function setSource(context, source) {
  const real = source === "real";
  context.source = source;
  context.trace = context.traces[source];
  const { fields, shell, video } = context;
  video.pause();
  context.starting = true;
  video.poster = folder + (real ? "gate-real-poster.webp" : "gate-poster.webp");
  video.src = folder + (real ? "gate-real.mp4" : "gate-a.mp4");
  video.playbackRate = Number(shell.querySelector('[data-camera="speed"]').value);
  fields["source-title"].textContent = real ? "Gate A · Real footage" : "Gate A · Synthetic model test";
  fields.intro.textContent = real
    ? "Real entry and exit footage with a synchronized campus parking simulation."
    : "Vehicle classification, registration reading and bay assignment on one timeline.";
  fields["identity-label"].textContent = real ? "Anonymous vehicle ID" : "Registration model";
  fields["table-identity"].textContent = real ? "Track ID" : "Test registration";
  fields.credit.textContent = real ? context.trace.chapters[0].credit : "Controlled clip · synthetic registrations";
  fields.clock.textContent = `0:00 / ${timestamp(context.trace.duration)}`;
  fields.error.hidden = true;
  shell.querySelector('[data-camera="restart"]').textContent = real ? "Restart clip" : "Run models from start";
  shell.querySelector('[data-camera="start"]').textContent = playLabel(context);
  const jump = shell.querySelector('[data-camera="jump"]');
  const choices = real ? context.trace.events.map((event) => [Math.max(0, event.time - 1.5), `${event.kind} ${event.direction.toLowerCase()}`]) :
    [[0,"Start"], [20,"Car overflow"], [28,"Bike overflow"], [52,"Departure frees a bay"], [76,"Unreadable plate"]];
  jump.replaceChildren(new Option("Choose event", ""), ...choices.map(([time, label]) => new Option(label, time)));
  fresh(context, real ? "footage" : "live");
}

function setup(context) {
  const { shell, video, abort } = context;
  const options = { signal: abort.signal };
  const startButton = shell.querySelector('[data-camera="start"]');
  shell.querySelectorAll('[data-camera]').forEach((control) => {
    if (control.dataset.camera !== "export") control.disabled = false;
  });
  video.addEventListener("play", () => { startButton.textContent = "Pause replay"; }, options);
  video.addEventListener("pause", () => {
    startButton.textContent = video.ended || video.currentTime < .05 ? playLabel(context) : "Resume replay";
  }, options);
  video.addEventListener("seeking", () => {
    if (context.source === "real") return;
    if (context.starting && video.currentTime < .05) return;
    context.starting = false;
    if (context.mode !== "replay") fresh(context, "replay");
  }, options);
  video.addEventListener("seeked", () => {
    context.starting = false;
    tick(context, video.currentTime);
  }, options);
  video.addEventListener("ended", () => tick(context, video.duration), options);
  video.addEventListener("error", () => report(context, "The local Gate A clip could not play in this browser."), options);
  shell.addEventListener("click", (event) => {
    if (event.target.closest('a[href="#fleet-incident"]')) video.pause();
    const command = event.target.closest("button[data-camera]")?.dataset.camera;
    if (command === "start" && !video.paused) {
      video.pause();
      return;
    }
    if (command === "start" || command === "restart") {
      context.fields.error.hidden = true;
      const reset = command === "restart" || video.ended;
      if (reset) {
        fresh(context, context.source === "real" ? "footage" : "live");
        context.starting = true;
        video.currentTime = 0;
      }
      play(context);
      showCameras(context);
      video.focus({ preventScroll: true });
    }
    if (command === "export") exportLedger(context);
  }, options);
  shell.addEventListener("change", (event) => {
    const command = event.target.dataset.camera;
    if (command === "source") setSource(context, event.target.value);
    if (command === "speed") video.playbackRate = Number(event.target.value);
    if (command === "jump" && event.target.value !== "") {
      fresh(context, context.source === "real" ? "footage" : "replay");
      video.currentTime = Number(event.target.value);
      event.target.value = "";
      play(context);
      showCameras(context);
    }
  }, options);
}

export async function mount(shell) {
  if (mounted?.shell === shell) return;
  const styleId = "fleet-gate-camera-styles";
  if (!document.getElementById(styleId)) {
    const link = document.createElement("link");
    link.id = styleId;
    link.rel = "stylesheet";
    link.href = folder + "camera.css";
    document.head.append(link);
  }
  shell.innerHTML = markup();
  const abort = new AbortController();
  const context = {
    shell, abort, video: shell.querySelector("video"),
    fields: Object.fromEntries([...shell.querySelectorAll("[data-fleet]")].map((element) => [element.dataset.fleet, element])),
    mapLayer: shell.querySelector(".fleet-map-model").getContext("2d"),
    scanLayer: shell.querySelector(".gate-detection").getContext("2d"),
  };
  mounted = context;
  try {
    const [model, testTrace, footage] = await Promise.all([
      json("gate-model.json", abort.signal), json("gate-trace.json", abort.signal),
      json("gate-real-trace.json", abort.signal),
    ]);
    if (mounted !== context) return;
    context.model = model;
    context.traces = { real: footage, test: testTrace };
    const decoder = document.createElement("canvas");
    [decoder.width, decoder.height] = model.size;
    context.frame = decoder.getContext("2d", { willReadFrequently: true });
    context.engine = new GateVision(model);
    setup(context);
    setSource(context, "real");
    schedule(context);
  } catch (error) {
    if (mounted === context) report(context, error.message);
  }
}

export function unmount(shell) {
  const context = mounted;
  if (context?.shell !== shell) return;
  context.abort.abort();
  context.video.pause();
  if (typeof context.video.cancelVideoFrameCallback === "function") {
    if (context.callback !== undefined) context.video.cancelVideoFrameCallback(context.callback);
  } else {
    cancelAnimationFrame(context.callback);
  }
  mounted = null;
}
