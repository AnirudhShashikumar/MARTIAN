// A deterministic policy agent for synthetic clip registrations and marked campus bays.
const carPoints = [[69.4,29], [69.4,32.3], [69.4,35.6], [69.4,38.7], [69.4,42], [69.4,45.2]];
const bikePoints = [[21.4,25.2], [20.8,27.7], [20.4,30.5], [20,33.3], [19.6,36.1],
  [19,38.9], [18.6,41.4], [18.1,44.2]];

function slots(prefix, kind, policy, points) {
  return points.map((point, index) => ({
    id: `${prefix}-${String(index + 1).padStart(2, "0")}`, kind, policy, point,
  }));
}

export const bays = [
  ...slots("C", "Car", "General", carPoints),
  ...slots("B", "Bike", "General", bikePoints),
  ...slots("OC", "Car", "Overflow reserve", [[69.4,9.7], [72.1,9.25]]),
  ...slots("OB", "Bike", "Overflow reserve", [[73.7,73], [76,74.1]]),
  ...slots("AC", "Car", "Accessible", [[69.4,57.8]]),
  ...slots("RC", "Car", "Reserved", [[69.4,54.6]]),
];

export function newRun(seed = {}) {
  const records = {};
  for (const [kind, id, count] of [["Car", 1000, seed.cars ?? 5], ["Bike", 2000, seed.bikes ?? 7]]) {
    bays.filter((bay) => bay.kind === kind && bay.policy === "General").slice(0, count).forEach((bay, index) => {
      const initial = `CF${id + index + 1}`;
      const plate = seed.aliases?.[initial] ?? initial;
      records[plate] = { plate, kind, bay: bay.id, status: "Parked", time: 0 };
    });
  }
  return { records, log: [] };
}

function freeBay(records, kind) {
  const used = new Set(Object.values(records).filter((record) => record.status === "Parked").map((record) => record.bay));
  return bays.find((bay) => bay.kind === kind && ["General", "Overflow reserve"].includes(bay.policy) && !used.has(bay.id));
}

function allocate(records, record, time) {
  const bay = freeBay(records, record.kind);
  if (!bay) return null;
  record.bay = bay.id;
  record.status = "Parked";
  record.assigned = time;
  return bay;
}

export function verifyParking(records) {
  const occupied = new Set();
  for (const vehicle of Object.values(records)) {
    if (vehicle.status !== "Parked") {
      if (vehicle.bay !== null) throw new Error("Inactive registration still owns a bay.");
      continue;
    }
    const bay = bays.find((candidate) => candidate.id === vehicle.bay);
    if (!bay || bay.kind !== vehicle.kind || !["General", "Overflow reserve"].includes(bay.policy) || occupied.has(bay.id)) {
      throw new Error("The assignment failed the class, eligibility or unique occupancy check.");
    }
    occupied.add(bay.id);
  }
}

export function act(run, event) {
  if (run.log.some((entry) => entry.id === event.id)) return run;
  let records = run.records;
  const evidence = { ...event, bay: null, action: "Review", motion: [], reason: "" };
  const real = event.source === "reviewed-footage";
  const plate = real ? event.track : event.plate;
  const reliable = real
    ? /^R-[CB]\d{2}$/.test(plate) && event.trackSamples >= 3 && event.classConfidence >= .24
    : /^CF\d{4}$/.test(plate) && event.classConfidence >= .72 && event.plateSamples >= 2;
  if (!reliable) {
    evidence.reason = real ? "Vehicle track needs staff review." : "Registration or vehicle evidence is uncertain. Staff review required.";
  } else if (event.direction === "Entry" && ["Parked", "Waiting"].includes(records[plate]?.status)) {
    evidence.reason = real ? "This track already has an active entry." : "Registration already has an active entry. Duplicate scan held.";
  } else if (event.direction === "Entry") {
    records = structuredClone(records);
    const incoming = { plate, kind: event.kind, bay: null, status: "Waiting", time: event.time };
    records[plate] = incoming;
    const bay = allocate(records, incoming, event.time);
    if (bay) {
      const overflow = bay.policy === "Overflow reserve";
      Object.assign(evidence, { action: overflow ? "Overflow assigned" : "Bay assigned", bay: bay.id,
        reason: overflow ? "General lot full. Used a designated overflow reserve." : "First free bay for this vehicle class.",
        motion: [{ direction: "Entry", kind: incoming.kind, bay: bay.id, plate }] });
    } else {
      evidence.action = "Waitlisted";
      evidence.reason = "General and overflow bays are full for this vehicle class.";
    }
  } else if (records[plate]?.status === "Parked" && records[plate].kind === event.kind) {
    records = structuredClone(records);
    const outgoing = records[plate];
    const released = outgoing.bay;
    Object.assign(outgoing, { status: "Departed", bay: null, exited: event.time });
    const motion = [{ direction: "Exit", kind: outgoing.kind, bay: released, plate }];
    const waiting = Object.values(records).filter((record) => record.kind === outgoing.kind && record.status === "Waiting")
      .sort((first, second) => first.time - second.time)[0];
    const assigned = waiting ? allocate(records, waiting, event.time) : null;
    if (assigned) motion.push({ direction: "Entry", kind: waiting.kind, bay: assigned.id, plate: waiting.plate });
    const releaseReason = real ? "Released the seeded bay linked to this anonymous track." :
      "Matching active registration released its bay.";
    Object.assign(evidence, { action: assigned ? "Released · queue advanced" : "Bay released", bay: released, motion,
      reason: assigned ? `${waiting.plate} assigned ${assigned.id} in arrival order.` : releaseReason });
  } else {
    evidence.reason = "No active bay matches this departure. Staff review required.";
  }

  verifyParking(records);
  return { records, log: [...run.log, evidence] };
}
