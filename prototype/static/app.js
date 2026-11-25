"use strict";

const $ = (selector) => document.querySelector(selector);
const roles = { parking: "Parking attendant", room: "Facilities supervisor" };
const stages = {
  idle: "Monitoring", pending: "Approval needed", verified: "Verified",
  held: "Safety hold", rejected: "Staff review",
};
let state;
let view = "fleet";
let busy = false;
const sections = {
  fleet: [["parking", "Parking overview"], ["gate", "Gate ledger"], ["overflow", "Overflow approvals"]],
  resources: [["rooms", "Rooms & devices"], ["labs", "Labs"], ["library", "Library seats"], ["equipment", "Sports equipment"]],
};
const selected = { fleet: "parking", resources: "rooms" };

function escape(value) {
  return String(value ?? "").replace(/[&<>"']/g, (char) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  })[char]);
}

function clock(seconds, precise = true) {
  const total = 14 * 3600 + seconds;
  const part = (number) => String(number).padStart(2, "0");
  const hhmm = part(Math.floor(total / 3600)) + ":" + part(Math.floor(total / 60) % 60);
  return precise ? hhmm + ":" + part(total % 60) : hhmm;
}

function badge(label, cls = "idle") {
  return `<span class="badge ${cls}">${escape(label)}</span>`;
}

function action(name, label, tone = "secondary", extra = "") {
  return `<button type="button" class="button ${tone}" data-action="${name}" ${extra}${busy ? " disabled" : ""}>${label}</button>`;
}

function linkView(target, label) {
  return `<button type="button" class="button primary" data-view="${target}">${label}</button>`;
}

function branchDescription(branch) {
  const result = state.branches[branch];
  if (branch === "parking" && result.status === "verified") {
    const active = state.bays.some((bay) => bay.id === result.bay && bay.vehicle === result.vehicle);
    return `${result.vehicle} · ${result.bay}${active ? "" : " · released"}`;
  }
  const descriptions = {
    parking: { idle: "Gate A · separate car and bike capacity", pending: "Gate A · temporary overflow", held: "Gate A · capacity review", rejected: "Gate A · request declined" },
    room: { idle: "C-101 · room and device state", pending: "C-101 · standby proposed", verified: "C-101 · mock standby confirmed", held: "C-101 · power change blocked", rejected: "C-101 · request declined" },
  };
  return descriptions[branch][result.status] ?? "";
}

function renderIncident() {
  const id = state.phase === "baseline" ? "" : `<span class="incident-id">CF-${escape(state.id.slice(0, 6).toUpperCase())}</span>`;
  let title = "Campus operations";
  let description = "Gate A and classroom C-101 are operating on the current timetable.";
  let context = `<span>Scenario clock ${clock(state.clock)}</span><span>Original timetable · 14:00–14:45</span>`;

  if (state.phase === "detected" || state.phase === "clarification") {
    title = "Late schedule change";
    description = `&ldquo;${escape(state.note)}&rdquo;`;
    context = "<span>Staff note received</span><span>Two new arrivals</span>";
  }
  if (state.session) {
    title = "Lab induction moved to Lab 2";
    description = `<strong>14:20–15:05 in Lab 2.</strong> The revised timetable changes arrivals at Gate A and frees classroom C-101.`;
    context = `<span>Timetable ${escape(state.session.revision)}</span><span>Scenario clock ${clock(state.clock)}</span>`;
  }

  const summary = [["parking", "Vehicle fleet"], ["room", "College resources"]].map(([key, label]) => {
    const status = state.branches[key].status;
    const statusLabel = status === "idle" && state.phase !== "baseline" ? "Checking evidence" : stages[status];
    return `<div><div><strong>${label}</strong><small>${escape(branchDescription(key))}</small></div>
       ${badge(statusLabel, status)}</div>`;
  }).join("");

  $("#incident").innerHTML = `<div class="incident-left">
      <p class="eyebrow">${state.phase === "baseline" ? "Operations overview" : "Shared incident"}${id}</p>
      <h1>${title}</h1><p class="incident-desc">${description}</p>
      <div class="context-line">${context}</div></div><div class="branch-summary">${summary}</div>`;
}

function capacity(kind) {
  const bays = state.bays.filter((bay) => bay.kind === kind && bay.policy !== "Overflow");
  const general = bays.filter((bay) => bay.policy === "General");
  const available = general.filter((bay) => !bay.vehicle).length;
  const spots = bays.map((bay) =>
    `<span class="spot ${bay.policy !== "General" ? "safe" : bay.vehicle ? "taken" : ""}" title="${escape(bay.id + " · " + (bay.vehicle || bay.policy))}"></span>`
  ).join("");
  const note = kind === "Car" ? "2 protected bays" : "General bike bays";
  return `<div class="capacity"><h3>${kind === "Car" ? "Car parking" : "Bike parking"}</h3>
    <strong class="data">${available} / ${general.length} free</strong><p class="capacity-note">${note}</p>
    <div class="spots" aria-hidden="true">${spots}</div></div>`;
}

function parkingOverview() {
  const proposal = state.branches.parking;
  const overflow = state.bays.find((bay) => bay.policy === "Overflow");
  const windowLabel = state.session ? state.session.arrival_window : "Opens by approval";
  const closed = state.session && state.clock >= state.session.overflow_closes_at;
  let overflowState = overflow.vehicle ? "Assigned" : "Available";
  if (closed) overflowState = overflow.vehicle ? "Closed · occupied" : "Window closed";
  else if (proposal.status === "pending") overflowState = "Approval needed";
  const arrivalsWaiting = state.gate.filter((event) => event.status === "Waiting").length;

  return `<section class="panel">
    <div class="panel-head"><div><h2>Parking capacity</h2><p>Gate A · eligibility checked by vehicle class</p></div>
      ${badge(arrivalsWaiting ? `${arrivalsWaiting} waiting` : "Gate clear", arrivalsWaiting ? "pending" : "clear")}</div>
    <div class="capacity-grid">
      ${capacity("Car")}${capacity("Bike")}
      <div class="capacity ${overflow.vehicle ? "checked" : proposal.status === "pending" ? "callout" : ""}">
        <h3>Overflow · OV-01</h3><strong class="data">${overflowState}</strong><p class="capacity-note">${escape(windowLabel)}</p>
      </div>
    </div>
  </section>
  ${gateLedger(false)}`;
}

function gateLedger(full = true) {
  const picked = ["CAR-078", "BIKE-014", "CAR-021"];
  const records = full ? [...state.gate].reverse() : state.phase === "baseline"
    ? state.gate.slice(-3).reverse()
    : picked.map((id) => state.gate.find((item) => item.vehicle === id)).filter(Boolean);
  const rows = records.map((event) => {
    const status = event.status === "Waiting" ? "pending" : "verified";
    return `<tr><td>${escape(event.vehicle)}</td><td>${escape(event.bay ?? "—")}</td>
      <td>${clock(event.entered)}</td><td>${event.exited === null ? "—" : clock(event.exited)}</td>
      <td>${badge(event.status, status)}</td></tr>`;
  }).join("");
  const description = full ? "All synthetic vehicle entries and exits at Gate A" :
    state.phase === "baseline" ? "Recent synthetic arrivals" : "Vehicles in the demo sequence";
  return `<section class="panel">
    <div class="panel-head"><div><h2>${full ? "Gate ledger" : "Gate activity"}</h2><p>${description}</p></div></div>
    <div class="table-scroll"><table class="fleet-table"><thead><tr>
      <th scope="col">Vehicle</th><th scope="col">Bay</th><th scope="col">Entry</th>
      <th scope="col">Exit</th><th scope="col">Status</th>
    </tr></thead><tbody>${rows}</tbody></table></div>
  </section>`;
}

function overflowPanel() {
  const proposal = state.branches.parking;
  const bay = state.bays.find((item) => item.policy === "Overflow");
  const closed = state.session && state.clock >= state.session.overflow_closes_at;
  const windowState = closed ? "Closed" : state.session ? "In window" : "Awaiting timetable";
  return `<section class="panel">
    <div class="panel-head"><div><h2>Temporary overflow</h2><p>Gate A · designated car parking</p></div>
    ${badge(stages[proposal.status], proposal.status)}</div>
    <div class="detail-grid">
      <div><span>Overflow bay</span><strong>${escape(bay.id)}</strong></div>
      <div><span>Assigned vehicle</span><strong>${escape(bay.vehicle || "Unassigned")}</strong></div>
      <div><span>${windowState}</span><strong>${escape(state.session?.arrival_window || "—")}</strong></div>
    </div>
    <p class="panel-note">${escape(proposal.detail || "Parking staff approve temporary use after general car capacity is filled.")}</p>
  </section>`;
}

function roomsPanel() {
  const room = state.room;
  const last = room.samples[room.samples.length - 1];
  const roomStatus = state.branches.room.status;
  const old = last !== undefined && state.clock - last.at > 12;
  let presence = "Occupancy awaiting scenario";
  if (last) presence = old ? "Occupancy feed stale" : last.count ? "1 person detected" : "0 people detected";
  const devices = Object.entries(room.devices).map(([name, status]) =>
    `<div class="device ${status === "On" ? "" : "confirmed"}"><span>${name}</span>
       <strong>${escape(status)}</strong>
       <small>${roomStatus === "verified" ? "Mock readback" : "Simulated state"}</small></div>`
  ).join("");

  return `<section class="panel">
    <div class="panel-head"><div><h2>Classroom C-101</h2>
       <p>${last ? `Synthetic occupancy · last sample ${clock(last.at)}` : "Original location · device state simulated"}</p></div>
       ${badge(stages[roomStatus], roomStatus)}</div>
    <div class="room-evidence">
      <span class="evidence ${old || last?.count ? "alert" : ""}">${presence}</span>
      <span class="evidence">${room.booking ? "Booking active" : "Calendar clear"}</span>
      <span class="evidence ${room.hold ? "alert" : ""}">Manual hold ${room.hold ? "on" : "off"}</span>
    </div>
    <div class="device-grid">${devices}</div>
  </section>
  <section class="panel">
    <div class="panel-head"><div><h2>Shared resources</h2><p>Sample availability</p></div></div>
    <div class="catalog">
      <div><strong>Lab 2</strong><span>${state.session ? "Booked · 14:20–15:05" : "Open · afternoon"}</span></div>
      <div><strong>Library quiet zone</strong><span>12 of 24 seats free</span></div>
      <div><strong>Sports equipment</strong><span>${state.equipment.available} of ${state.equipment.total} kits available</span></div>
    </div>
  </section>`;
}

function labsPanel() {
  const booked = Boolean(state.session);
  return `<section class="panel">
    <div class="panel-head"><div><h2>Lab 2</h2><p>Afternoon timetable · synthetic booking</p></div>
    ${badge(booked ? "Booked" : "Available", booked ? "verified" : "idle")}</div>
    <div class="detail-grid">
      <div><span>Session</span><strong>${booked ? "Lab induction" : "Unassigned"}</strong></div>
      <div><span>Booking window</span><strong>${booked ? "14:20–15:05" : "—"}</strong></div>
      <div><span>Timetable revision</span><strong>${escape(state.session?.revision || "—")}</strong></div>
    </div>
    <p class="panel-note">${booked ? "The timetable moved this session from C-101 to Lab 2." : "The current timetable keeps lab induction in C-101."}</p>
  </section>`;
}

function libraryPanel() {
  return `<section class="panel">
    <div class="panel-head"><div><h2>Library seating</h2><p>Quiet zone · synthetic availability snapshot</p></div>
    ${badge("12 seats available", "clear")}</div>
    <div class="detail-grid">
      <div><span>Total seats</span><strong>24</strong></div>
      <div><span>Occupied</span><strong>12</strong></div>
      <div><span>Available</span><strong>12</strong></div>
    </div>
    <div class="seat-meter" aria-hidden="true"><span></span></div>
  </section>`;
}

function equipmentPanel() {
  const item = state.equipment;
  return `<section class="panel">
    <div class="panel-head"><div><h2>Sports equipment</h2><p>Sample inventory · multi-sport kits</p></div>
    ${badge(`${item.available} of ${item.total} available`, "clear")}</div>
    <div class="detail-grid">
      <div><span>Demo kit</span><strong>${escape(item.kit)}</strong></div>
      <div><span>Kit status</span><strong>${item.checked_out ? "Checked out" : "Available"}</strong></div>
      <div><span>Available kits</span><strong>${item.available}</strong></div>
    </div>
    <div class="actions inline-actions">
      ${item.checked_out ? action("return_kit", "Return sample kit") : action("checkout_kit", "Check out sample kit")}
    </div>
  </section>`;
}

const renderSections = {
  parking: parkingOverview, gate: gateLedger, overflow: overflowPanel, rooms: roomsPanel,
  labs: labsPanel, library: libraryPanel, equipment: equipmentPanel,
};

function reviewActions(key, approveTone = "primary") {
  const label = key === "room" ? "Approve standby" : "Approve overflow";
  return action("approve", label, approveTone, `data-branch="${key}"`) +
    action("reject", "Decline", "secondary", `data-branch="${key}"`);
}

function scenarioOptions() {
  if (state.phase !== "active") return "";
  const options = [];
  if (state.branches.room.status !== "verified") {
    options.push(action("stale", "Age occupancy feed"));
    options.push(action("override", state.room.hold ? "Release manual hold" : "Set manual hold"));
  }
  if (state.clock < state.session.overflow_closes_at) options.push(action("expire", "Close overflow window"));
  if (state.bays.some((bay) => bay.policy === "Overflow" && bay.vehicle)) {
    options.push(action("exit_overflow", "Exit overflow car"));
  }
  return options.length
    ? `<details class="scenario-options"><summary>Scenario options</summary><div class="actions">${options.join("")}</div></details>`
    : "";
}

function currentControl() {
  if (busy) return ["Running", "Checking scenario state", "Reading evidence and validating the next action.", ""];
  if (state.phase === "baseline") return [
    "Sense", "Start the incident", "Deliver a synthetic staff note and two Gate A arrivals.",
    action("trigger", "Trigger schedule change", "primary"),
  ];
  if (state.phase === "detected") return [
    "Think", "Confirm what moved", "Does “20 minutes late” change the start or end? Use the authoritative timetable.",
    state.model_available ? action("run", "Run agent", "primary") :
      action("confirm", "Confirm timetable lookup", "primary"),
  ];
  if (state.phase === "clarification") return [
    "Think", "Coordinator confirmation", state.intake.detail,
    action("confirm", "Confirm synthetic schedule", "primary"),
  ];

  const key = view === "fleet" ? "parking" : "room";
  const branch = state.branches[key];
  if (branch.status === "pending") {
    const firstRoomProposal = key === "room" && !state.audit.some((log) => log.title === "Pending standby blocked");
    const decisions = reviewActions(key, firstRoomProposal ? "secondary" : "primary");
    return [
      "Plan", key === "parking" ? "Authorize temporary overflow" : "Review room standby", branch.detail,
      (firstRoomProposal ? action("occupied", "Inject occupied reading", "primary") : "") + decisions,
      roles[key],
    ];
  }
  if (branch.status === "held" || branch.status === "rejected") {
    const buttons = key === "room" ? action("vacant", "Recheck sustained vacancy", "primary") :
      linkView("resources", "Open resource view");
    return ["Adapt", key === "room" ? "Standby on hold" : "Parking staff review", branch.detail, buttons];
  }
  if (key === "parking") {
    const exitDone = state.events.includes("GATE-EXIT-021");
    return [
      "Verify", `${branch.bay} assignment verified`, branch.detail,
      exitDone ? linkView("resources", "Open resource view") : action("exit", "Confirm regular car exit", "primary"),
    ];
  }
  return ["Explain", "Device state verified", branch.detail, action("audit", "View decision audit", "primary")];
}

function consolePanel() {
  const [stage, title, detail, buttons, role] = currentControl();
  const intakeMode = busy ? "Local simulation" : state.intake?.label ??
    (state.model_available ? "Gemini configured · synthetic input" : "Structured intake · offline");
  const recent = [...state.audit].reverse().slice(0, 3);
  const recentRows = recent.map((log) => `<li><span class="stage">${escape(log.stage)}</span>
    <strong>${escape(log.title)}</strong></li>`).join("");
  return `<section class="panel control">
    <div class="panel-head"><h2>Demo control</h2>${badge(stage, busy ? "working" : "idle")}</div>
    <p class="mode">${escape(intakeMode)}</p>
    <h3>${escape(title)}</h3><p class="control-copy">${escape(detail)}</p>
    ${role ? `<span class="review-label">Simulated reviewer · ${escape(role)}</span>` : ""}
    <div class="actions">${buttons}</div>
    ${scenarioOptions()}
    </section>
    <section class="panel activity">
      <div class="panel-head"><h2>Recent activity</h2></div>
      ${recentRows ? `<ol class="stage-log">${recentRows}</ol>` : '<p class="empty">Awaiting the first event.</p>'}
    </section>`;
}

function renderAudit() {
  const branches = Object.values(state.branches);
  const verified = branches.filter((branch) => branch.status === "verified").length;
  const held = state.audit.filter((entry) => entry.title === "Pending standby blocked").length;
  const released = state.gate.filter((event) => event.status === "Departed").length;
  const rows = [...state.audit].reverse().map((entry) => `<li>
    <time>${clock(entry.time)}</time><span class="stage">${escape(entry.stage)}</span>
    <div><strong>${escape(entry.title)}</strong><p>${escape(entry.detail)}</p></div></li>`).join("");
  $("#audit-body").innerHTML = `<div class="audit-metrics">
    <div><strong>${verified} / 2</strong><span>Verified branches</span></div>
    <div><strong>${held}</strong><span>Unsafe proposals blocked</span></div>
    <div><strong>${released}</strong><span>Bays released on exit</span></div>
  </div>${rows ? `<ol class="full-log">${rows}</ol>` : '<p class="empty">No scenario actions yet.</p>'}`;
}

function render() {
  renderIncident();
  const section = selected[view];
  const subnav = $("#subtabs");
  subnav.setAttribute("aria-label", view === "fleet" ? "Vehicle fleet views" : "College resource views");
  subnav.innerHTML = sections[view].map(([key, label]) =>
    `<button type="button" data-section="${key}"${key === section ? ' aria-current="page"' : ""}>${label}</button>`
  ).join("");
  $("#operation").innerHTML = renderSections[section]();
  $("#console").innerHTML = consolePanel();
  if ($("#audit-dialog").open) renderAudit();
  document.querySelectorAll(".tabs [data-view]").forEach((tab) => {
    if (tab.dataset.view === view) tab.setAttribute("aria-current", "page");
    else tab.removeAttribute("aria-current");
  });
  $(".reset").disabled = busy;
}

async function api(path, options) {
  const response = await fetch(path, { cache: "no-store", ...options });
  const data = await response.json();
  if (!response.ok) throw new Error(typeof data.detail === "string" ? data.detail : "The demo command was rejected.");
  return data;
}

function notify(message = "") {
  const box = $("#error");
  box.hidden = !message;
  box.textContent = message;
}

async function execute(name, key) {
  const body = { action: name, run_id: state.id };
  if (name === "approve" || name === "reject") {
    Object.assign(body, { action: "review", decision: name, branch: key, proposal: state.branches[key].id, role: roles[key] });
  }
  busy = true;
  notify();
  render();
  try {
    state = await api("/api/command", {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body),
    });
    if (name === "reset") {
      view = "fleet";
      selected.fleet = "parking";
      selected.resources = "rooms";
    }
    $("#announcements").textContent = state.audit.at(-1)?.title ?? "Demo reset.";
  } catch (error) {
    notify(error.message || "CampusFlow could not complete the command.");
    try {
      state = await api("/api/state");
    } catch {
      notify("CampusFlow could not connect to the local server. Reload after the server is available.");
    }
  } finally {
    busy = false;
    render();
    if (name.endsWith("_kit")) $("#operation .actions button")?.focus({ preventScroll: true });
    else if (name !== "reset") $(".control .actions button")?.focus({ preventScroll: true });
  }
}

document.addEventListener("click", (event) => {
  const button = event.target.closest("button");
  if (!button || !state) return;
  if (button.dataset.view) {
    view = button.dataset.view;
    const inConsole = button.closest("#console");
    if (inConsole && view === "resources") selected.resources = "rooms";
    render();
    if (inConsole) $(".control .actions button")?.focus({ preventScroll: true });
    return;
  }
  if (button.dataset.section) {
    selected[view] = button.dataset.section;
    render();
    $("#subtabs [aria-current]").focus({ preventScroll: true });
    return;
  }
  const name = button.dataset.action;
  if (name === "audit") {
    renderAudit();
    $("#audit-dialog").showModal();
  } else if (name && !busy) {
    execute(name, button.dataset.branch);
  }
});

api("/api/state").then((initial) => {
  state = initial;
  render();
}).catch(() => notify("CampusFlow could not connect to the local server. Check that it is running and reload."));
