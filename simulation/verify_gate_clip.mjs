import assert from "node:assert/strict";
import { spawn } from "node:child_process";
import { once } from "node:events";
import { readFile, writeFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import { GateVision } from "../prototype/static/fleet/vision.mjs";
import { act, newRun, verifyParking } from "../prototype/static/fleet/parking-agent.mjs";

const assets = new URL("../prototype/static/fleet/", import.meta.url);
const read = async (url) => JSON.parse(await readFile(url, "utf8"));
const model = await read(new URL("gate-model.json", assets));
const expected = await read(new URL("gate-expected.json", import.meta.url));
const footage = await read(new URL("gate-real-trace.json", assets));
const rates = [8, 5];
let manifest;

function verifyDecisions(events) {
  let state = newRun();
  for (const event of events) state = act(state, event);
  verifyParking(state.records);

  const get = (offset) => state.log[offset];
  assert.equal(get(0).bay, "C-06");
  assert.equal(get(1).bay, "B-08");
  assert.equal(get(2).action, "Overflow assigned");
  assert.equal(get(3).bay, "OB-01");
  assert.equal(get(5).action, "Waitlisted");
  assert.equal(get(6).action, "Released · queue advanced");
  assert.deepEqual(get(6).motion.map((item) => item.plate), ["CF1001", "CF1104"]);
  assert.equal(get(8).action, "Review");
  assert.match(get(8).reason, /Duplicate/);
  assert.equal(get(9).action, "Review");
  assert.equal(get(10).action, "Review");
  return state.log.reduce((counts, event) => ({ ...counts, [event.action]: (counts[event.action] ?? 0) + 1 }), {});
}

for (const rate of rates) {
  const engine = new GateVision(model);
  const [width, height] = model.size;
  const frameSize = width * height * 3;
  const frame = Buffer.allocUnsafe(frameSize);
  const ffmpeg = spawn(process.env.FFMPEG || "ffmpeg", [
    "-loglevel", "error", "-nostdin", "-i", fileURLToPath(new URL("gate-a.mp4", assets)),
    "-vf", `fps=${rate}`, "-an", "-threads", "2", "-pixel_format", "rgb24", "-pix_fmt", "rgb24",
    "-f", "rawvideo", "pipe:1",
  ], { stdio: ["ignore", "pipe", "inherit"] });
  const exit = once(ffmpeg, "close");
  let filled = 0, frames = 0;
  const events = [];
  for await (const chunk of ffmpeg.stdout) {
    let offset = 0;
    while (offset !== chunk.length) {
      const copied = Math.min(frameSize - filled, chunk.length - offset);
      chunk.copy(frame, filled, offset, offset + copied);
      filled += copied;
      offset += copied;
      if (filled === frameSize) {
        events.push(...engine.scan(frame, frames / rate, 3).events);
        frames++;
        filled = 0;
      }
    }
  }
  const [code] = await exit;
  assert.equal(code, 0);
  assert.equal(filled, 0);
  assert.equal(frames, model.duration * rate);
  assert.equal(events.length, expected.length, `crossing count at ${rate} FPS`);
  events.forEach((entry, index) => {
    const [time, kind, direction, plate] = expected[index];
    assert.deepEqual([entry.kind, entry.direction, entry.plate], [kind, direction, plate],
      `crossing ${index + 1} at ${rate} FPS`);
    assert.ok(Math.abs(entry.time - time) < .8, `crossing offset ${entry.time - time}`);
  });
  const decisions = verifyDecisions(events);
  console.log(`${rate} FPS: ${events.length} matched gate crossings, ${events.filter((event) => event.plate).length} exact readings, one unreadable plate held.`);
  if (!manifest) manifest = {
    duration: model.duration, fps: rate, events,
    validation: { crossings: events.length, plates: events.filter((event) => event.plate).length, decisions },
  };
}

if (process.argv.includes("--write")) {
  await writeFile(new URL("gate-trace.json", assets), JSON.stringify(manifest) + "\n");
}

let realRun = newRun(footage.seed);
for (const event of footage.events) {
  assert.ok(event.time >= 0 && event.time < footage.duration);
  assert.ok(event.trackSamples >= 3 && event.plate === null);
  realRun = act(realRun, event);
}
assert.deepEqual(realRun.log.map(({ direction, kind, bay, action }) => [direction, kind, bay, action]), [
  ["Entry", "Car", "OC-01", "Overflow assigned"],
  ["Entry", "Bike", "B-08", "Bay assigned"],
  ["Exit", "Car", "C-01", "Bay released"],
  ["Exit", "Bike", "B-01", "Bay released"],
]);
assert.equal(realRun.records["R-C02"].status, "Departed");
assert.equal(realRun.records["R-B02"].status, "Departed");
console.log("Real reel: car and motorcycle arrivals and departures produced four verified bay decisions.");
