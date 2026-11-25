"use strict";

const $ = (selector) => document.querySelector(selector);
const roles = { parking: "Parking attendant", room: "Facilities supervisor" };
const stages = {
  idle: "Monitoring", pending: "Approval needed", verified: "Verified",
  held: "Safety hold", rejected: "Staff review",
};
let state;
let busy = false;
const view = "resources";
const workspace = {
  title: "College Resource Allocation",
  path: "/resources",
  area: "Campus facilities",
  description: "Manage classrooms, labs, library seats, and shared equipment.",
  sections: [["rooms", "Rooms & devices"], ["labs", "Labs"], ["library", "Library seats"], ["equipment", "Sports equipment"]],
};
const resourceTabs = new Set(["labs", "library", "equipment"]);
const linkedSection = new URLSearchParams(window.location.search).get("section");
let section = resourceTabs.has(linkedSection) ? linkedSection : workspace.sections[0][0];
let resourceWorkspace;
let cctv = {
  active: false,
  connecting: false,
  has_frame: false,
  source: "http://10.110.18.80:4747/video",
  backend: "idle",
  state: "EMPTY",
  manual_override: null,
  person_count: 0,
  confidence: 0,
  hold_remaining: 0,
  fps: 0,
  infer_ms: 0,
  devices: { Lights: "Off", Fans: "Off", Projector: "Off" },
  status_message: "CCTV inactive — click Initialize CCTV Cam or use Manual Override.",
  error: null,
  events: [],
};
let cctvBusy = false;
let cctvPollTimer = null;
let cctvStreamToken = 0;

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
  let title = "No active incident";
  let description = "Gate A and C-101 are following the current timetable.";
  let context = `Scenario clock · ${clock(state.clock, false)}`;

  if (state.phase === "detected" || state.phase === "clarification") {
    title = "Late schedule change";
    description = `&ldquo;${escape(state.note)}&rdquo;`;
    context = "Staff note received · Gate A arrivals";
  }
  if (state.session) {
    const session = state.session;
    title = `${session.name} moved to ${session.room}`;
    description = `<strong>${escape(session.start)}–${escape(session.end)} in ${escape(session.room)}.</strong> The revised timetable changes arrivals at Gate A and frees ${escape(session.previous_room)}.`;
    context = `Timetable ${escape(session.revision)} · ${clock(state.clock, false)}`;
  }

  const summary = [["parking", "Vehicle fleet"], ["room", "College resources"]].map(([key, label]) => {
    const status = state.branches[key].status;
    const statusLabel = status === "idle" && state.phase !== "baseline" ? "Checking evidence" : stages[status];
    return `<div><div><strong>${label}</strong><small>${escape(branchDescription(key))}</small></div>
       ${badge(statusLabel, status)}</div>`;
  }).join("");

  const incident = $("#incident");
  incident.innerHTML = `
    <p class="eyebrow">Shared incident${id}</p>
    <h2>${escape(title)}</h2><p class="incident-desc">${description}</p>
    <p class="incident-context">${context}</p><div class="branch-summary">${summary}</div>`;
  incident.hidden = false;
}

function cctvBannerClass() {
  if (cctv.manual_override === "on") return "occupied";
  if (cctv.manual_override === "off") return "empty";
  if (!cctv.active) return "idle";
  if (!cctv.has_frame) return "connecting";
  return cctv.state === "OCCUPIED" ? "occupied" : "empty";
}

function cctvBannerMeta() {
  if (cctv.manual_override) return "Manual Override active — click Return to Auto to follow live CCTV again";
  if (!cctv.active) return "Phone 1 DroidCam stream + YOLOv8n person detection (RAM-only, no video saved)";
  if (cctv.error) return `Stream notice: ${cctv.error}`;
  if (!cctv.has_frame) return `Connecting to ${cctv.source}…`;
  return `${cctv.person_count} ${cctv.person_count === 1 ? "person" : "people"} in frame · YOLOv8n ${cctv.infer_ms} ms · ${cctv.fps} FPS`;
}

function isClassroomView() {
  return view === "resources" && section === "rooms";
}

function classroomAllOn() {
  const devs = state?.local_resource_workflows ? cctv.devices : (state?.room?.devices || {});
  return Object.values(devs).some((val) => val === "On");
}

function syncCctvDom() {
  const banner = $("#cctv-banner");
  if (banner) {
    banner.className = `cctv-banner ${cctvBannerClass()}`;
    const msgEl = $("#cctv-msg");
    const metaEl = $("#cctv-meta");
    if (msgEl) msgEl.textContent = cctv.status_message;
    if (metaEl) metaEl.textContent = cctvBannerMeta();
  }

  const headBadge = $("#classroom-head-badge");
  if (headBadge) {
    let text = "Idle";
    let cls = "idle";
    if (cctv.manual_override === "on") { text = "Override · All On"; cls = "verified"; }
    else if (cctv.manual_override === "off") { text = "Override · All Off"; cls = "held"; }
    else if (cctv.active) {
      text = cctv.state === "OCCUPIED" ? "Live · Occupied" : "Live · Empty";
      cls = cctv.state === "OCCUPIED" ? "verified" : "idle";
    }
    headBadge.className = `badge ${cls}`;
    headBadge.textContent = text;
  }

  const ovSwitch = $("#manual-override-switch");
  if (ovSwitch) {
    const isOn = classroomAllOn();
    ovSwitch.setAttribute("aria-checked", String(isOn));
    ovSwitch.classList.toggle("on", isOn);
    const label = ovSwitch.querySelector(".switch-state");
    if (label) label.textContent = isOn ? "ALL ON" : "ALL OFF";
  }

  if (state?.local_resource_workflows) {
    const subLabel = cctv.manual_override
      ? "Manual override"
      : (cctv.active ? "Live CCTV auto" : "Ready");
    Object.entries(cctv.devices).forEach(([name, val]) => {
      const card = document.querySelector(`[data-device-card="${name}"]`);
      if (!card) return;
      card.classList.toggle("is-on", val === "On");
      card.classList.toggle("is-off", val !== "On");
      card.classList.toggle("confirmed", val !== "On");
      const strong = card.querySelector("strong");
      const small = card.querySelector("small");
      if (strong) strong.textContent = val;
      if (small) small.textContent = subLabel;
    });
  }

  if (isClassroomView()) {
    $("#activity").innerHTML = activityPanel();
  }
}

function stopCctvPolling() {
  if (cctvPollTimer) {
    clearInterval(cctvPollTimer);
    cctvPollTimer = null;
  }
}

function startCctvPolling() {
  stopCctvPolling();
  if (!cctv.active || view !== "resources" || section !== "rooms") return;
  cctvPollTimer = setInterval(async () => {
    if (!cctv.active || view !== "resources" || section !== "rooms") {
      stopCctvPolling();
      return;
    }
    try {
      const latest = await api("/api/cctv/status");
      const activeChanged = latest.active !== cctv.active;
      cctv = { ...cctv, ...latest };
      if (activeChanged) renderSection();
      else syncCctvDom();
    } catch {
      // ignore transient poll hiccup
    }
  }, 500);
}

async function handleCctvAction(mode) {
  if (cctvBusy) return;
  const input = $("#cctv-source");
  if (input && input.value.trim()) cctv.source = input.value.trim();

  // Manual Override toggle updates in-place so the live MJPEG <img> never flickers/reloads
  if (mode === "toggle_override" || mode === "override_auto") {
    const nextMode = mode === "override_auto" ? "auto" : (classroomAllOn() ? "off" : "on");
    try {
      cctv = await api("/api/cctv/override", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ mode: nextMode }),
      });
      if (cctv.active) {
        syncCctvDom();
        const autoBtn = $("#manual-override-auto");
        if (autoBtn) autoBtn.hidden = !cctv.manual_override;
      } else {
        render();
      }
      $("#announcements").textContent = cctv.status_message;
    } catch (error) {
      notify(error.message || "Could not update manual override.");
    }
    return;
  }

  cctvBusy = true;
  notify();
  renderSection();
  try {
    if (mode === "start") {
      cctv = await api("/api/cctv/start", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ source: cctv.source, hold_seconds: 3.0 }),
      });
      cctvStreamToken = Date.now();
      $("#announcements").textContent = "Classroom CCTV initialized.";
    } else {
      stopCctvPolling();
      cctv = await api("/api/cctv/stop", { method: "POST" });
      $("#announcements").textContent = "Classroom CCTV disabled.";
    }
  } catch (error) {
    notify(error.message || "Could not update CCTV camera state.");
  } finally {
    cctvBusy = false;
    render();
    if (cctv.active) startCctvPolling();
  }
}

function roomsPanel() {
  const room = state.room;
  const roomStatus = state.branches.room.status;
  const localMode = Boolean(state.local_resource_workflows);
  const liveCctv = Boolean(localMode && cctv.active);

  const activeDevices = localMode ? cctv.devices : room.devices;
  const subLabel = cctv.manual_override
    ? "Manual override"
    : (liveCctv ? "Live CCTV auto" : "Ready");

  const devices = Object.entries(activeDevices).map(([name, status]) =>
    `<div class="device ${status === "On" ? "is-on" : "is-off confirmed"}" data-device-card="${escape(name)}"><span>${escape(name)}</span>
       <strong>${escape(status)}</strong>
       <small>${localMode ? subLabel : "Classroom appliance"}</small></div>`
  ).join("");

  const isOn = classroomAllOn();
  const cctvControls = localMode ? `
    <div class="cctv-bar">
      <label class="cctv-field">
        <span>Phone 1 DroidCam URL (or <code>0</code> for laptop webcam)</span>
        <input id="cctv-source" type="text" value="${escape(cctv.source)}" ${cctv.active || cctvBusy ? "disabled" : ""} placeholder="http://10.110.18.80:4747/video">
      </label>
      <div class="cctv-actions">
        ${cctv.active
          ? `<button type="button" class="button secondary cctv-stop" data-cctv="stop" ${cctvBusy ? "disabled" : ""}>Disable CCTV</button>`
          : `<button type="button" class="button primary" data-cctv="start" ${cctvBusy ? "disabled" : ""}>${cctvBusy ? "Starting…" : "Initialize CCTV Cam"}</button>`}
      </div>
    </div>
    <div class="override-bar">
      <div class="override-copy">
        <strong>Manual Override · Master Power</strong>
        <span>Turn Lights, Fans &amp; Projector all On or Off at once</span>
      </div>
      <div class="override-controls">
        <button id="manual-override-auto" type="button" class="button ghost btn-auto" data-cctv="override_auto" ${cctv.manual_override ? "" : "hidden"}>Return to Auto</button>
        <button id="manual-override-switch" type="button" role="switch" aria-checked="${isOn}" class="master-switch ${isOn ? "on" : ""}" data-cctv="toggle_override">
          <span class="switch-track"><span class="switch-thumb"></span></span>
          <span class="switch-state">${isOn ? "ALL ON" : "ALL OFF"}</span>
        </button>
      </div>
    </div>` : "";

  const liveStreamBlock = liveCctv ? `
    <div class="cctv-stage">
      <figure class="overview-media cctv-media">
        <img id="cctv-feed" src="/api/cctv/stream?t=${cctvStreamToken}" alt="Live Classroom C-101 CCTV stream with YOLOv8 person bounding boxes">
        <figcaption class="media-caption">Live Phone 1 DroidCam · YOLOv8n bounding boxes</figcaption>
      </figure>
      <div id="cctv-banner" class="cctv-banner ${cctvBannerClass()}" role="status" aria-live="polite">
        <strong id="cctv-msg">${escape(cctv.status_message)}</strong>
        <span id="cctv-meta">${escape(cctvBannerMeta())}</span>
      </div>
    </div>` : (localMode && cctv.manual_override ? `
    <div id="cctv-banner" class="cctv-banner ${cctvBannerClass()}" role="status" aria-live="polite" style="margin-bottom:14px;">
      <strong id="cctv-msg">${escape(cctv.status_message)}</strong>
      <span id="cctv-meta">${escape(cctvBannerMeta())}</span>
    </div>` : "");

  let headBadgeHtml = badge(stages[roomStatus], roomStatus);
  if (localMode) {
    let bText = "Idle";
    let bCls = "idle";
    if (cctv.manual_override === "on") { bText = "Override · All On"; bCls = "verified"; }
    else if (cctv.manual_override === "off") { bText = "Override · All Off"; bCls = "held"; }
    else if (liveCctv) {
      bText = cctv.state === "OCCUPIED" ? "Live · Occupied" : "Live · Empty";
      bCls = cctv.state === "OCCUPIED" ? "verified" : "idle";
    }
    headBadgeHtml = `<span id="classroom-head-badge" class="badge ${bCls}">${escape(bText)}</span>`;
  }

  return `<section class="panel">
    <div class="panel-head"><div><h2>Classroom C-101</h2>
       <p>${liveCctv ? "Live DroidCam CCTV · Person detected turns all On · Empty turns all Off" : "Initialize CCTV Cam for auto-detection or flip Manual Override"}</p></div>
       ${headBadgeHtml}</div>
    ${cctvControls}
    ${liveStreamBlock}
    <div class="device-grid classroom-devices">${devices}</div>
  </section>
  <section class="panel">
    <div class="panel-head"><div><h2>Shared resources</h2><p>Sample availability</p></div></div>
    <div class="catalog">
      <button type="button" data-section="labs"><strong>Lab 2</strong><span>${state.session ? `Booked · ${escape(state.session.start)}–${escape(state.session.end)}` : "Open · afternoon"}</span></button>
      <button type="button" data-section="library"><strong>Library quiet zone</strong><span>12 of 24 seats free</span></button>
      <button type="button" data-section="equipment"><strong>Sports equipment</strong><span>${state.equipment.available} of ${state.equipment.total} kits available</span></button>
    </div>
  </section>`;
}

function labsPanel() {
  const booking = state.session?.room === "Lab 2" ? state.session : null;
  return `<section class="panel">
    <div class="panel-head"><div><h2>Lab 2</h2><p>Afternoon timetable · synthetic booking</p></div>
    ${badge(booking ? "Booked" : "Available", booking ? "verified" : "idle")}</div>
    <div class="detail-grid">
      <div><span>Session</span><strong>${escape(booking?.name ?? "Unassigned")}</strong></div>
      <div><span>Booking window</span><strong>${booking ? escape(`${booking.start}–${booking.end}`) : "—"}</strong></div>
      <div><span>Timetable revision</span><strong>${escape(booking?.revision ?? "—")}</strong></div>
    </div>
    <p class="panel-note">${booking ? `Previous location · ${escape(booking.previous_room)}` : "No sample booking for Lab 2."}</p>
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
  rooms: roomsPanel,
  labs: labsPanel,
  library: libraryPanel,
  equipment: equipmentPanel,
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

  const key = "room";
  const branch = state.branches[key];
  if (branch.status === "pending") {
    const firstRoomProposal = !state.audit.some((log) => log.title === "Pending standby blocked");
    const decisions = reviewActions(key, firstRoomProposal ? "secondary" : "primary");
    return [
      "Plan", "Review room standby", branch.detail,
      (firstRoomProposal ? action("occupied", "Inject occupied reading", "primary") : "") + decisions,
      roles[key],
    ];
  }
  if (branch.status === "held" || branch.status === "rejected") {
    return ["Adapt", "Standby on hold", branch.detail, action("vacant", "Recheck sustained vacancy", "primary")];
  }
  return ["Explain", "Device state verified", branch.detail, action("audit", "View decision audit", "primary")];
}

function consolePanel() {
  const [stage, title, detail, buttons, role] = currentControl();
  const intakeMode = state.intake?.label ??
    (state.model_available ? "Gemini configured · synthetic input" : "Structured intake · offline");
  return `<section class="panel control">
    <div class="panel-head"><h2>Demo control</h2>${badge(stage, busy ? "working" : "idle")}</div>
    <p class="mode">${escape(intakeMode)}</p>
    <h3>${escape(title)}</h3><p class="control-copy">${escape(detail)}</p>
    ${role ? `<span class="review-label">Simulated reviewer · ${escape(role)}</span>` : ""}
    <div class="actions">${buttons}</div>
    ${scenarioOptions()}
    </section>`;
}

function activityPanel() {
  if (isClassroomView()) {
    const cctvEvents = (cctv.events || []).map((ev) => ({
      time: ev.time,
      stage: ev.stage,
      title: ev.title,
      detail: ev.detail,
    }));
    const scenarioEvents = [...state.audit].reverse().map((log) => ({
      time: clock(log.time),
      stage: log.stage,
      title: log.title,
      detail: log.detail,
    }));
    const allLogs = [...cctvEvents, ...scenarioEvents];
    const rows = allLogs.map((log) => `<li class="incident-log-item">
      <div class="incident-log-meta"><span class="stage">${escape(log.stage)}</span><time>${escape(log.time)}</time></div>
      <strong>${escape(log.title)}</strong>
      ${log.detail ? `<p>${escape(log.detail)}</p>` : ""}
    </li>`).join("");
    return `<section class="panel activity incident-log-panel">
      <div class="panel-head"><div><h2>Incident log</h2><p>Every classroom change recorded</p></div>${badge(`${allLogs.length}`, allLogs.length ? "verified" : "idle")}</div>
      ${rows ? `<ol class="incident-log-list">${rows}</ol>` : '<p class="empty">No classroom changes yet. Click Initialize CCTV Cam to start logging live events.</p>'}
    </section>`;
  }

  const recentRows = state.audit.slice(-3).reverse().map((log) => `<li>
    <span class="stage">${escape(log.stage)}</span><strong>${escape(log.title)}</strong></li>`).join("");
  return `<section class="panel activity">
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

function renderSection() {
  $("#subtabs").querySelectorAll("button").forEach((tab) => {
    if (tab.dataset.section === section) tab.setAttribute("aria-current", "true");
    else tab.removeAttribute("aria-current");
  });
  const operation = $("#operation");
  const localResource = state.local_resource_workflows && view === "resources" && resourceTabs.has(section);
  const grid = operation.parentElement;
  grid.classList.toggle("resource-workspace-mode", Boolean(localResource));
  if (localResource) {
    const selected = section;
    const runId = state.id;
    operation.dataset.resourceMode = selected;
    if (resourceWorkspace) {
      resourceWorkspace.mount(operation, selected, runId);
      return;
    }
    operation.innerHTML = '<p class="panel" role="status">Loading resource workspace…</p>';
    import("/static/resource-workspace.js").then((module) => {
      resourceWorkspace = module;
      if (section === selected && state.id === runId) module.mount(operation, selected, runId);
    }).catch(() => {
      if (section === selected && state.id === runId) {
        operation.innerHTML = '<p class="error" role="alert">The resource workspace could not load. Refresh this page.</p>';
      }
    });
    return;
  }
  delete operation.dataset.resourceMode;
  resourceWorkspace?.unmount(operation);
  operation.innerHTML = renderSections[section]();
  if (view === "resources" && section === "rooms" && cctv.active) startCctvPolling();
  else stopCctvPolling();
}

function updateResourceLink() {
  if (view !== "resources" || !state.local_resource_workflows) return;
  const url = new URL(window.location.href);
  if (resourceTabs.has(section)) url.searchParams.set("section", section);
  else url.searchParams.delete("section");
  history.replaceState(history.state, "", url);
}

function renderSidebar() {
  const classroomOnlyLog = isClassroomView();
  const consoleEl = $("#console");
  const incidentEl = $("#incident");
  if (classroomOnlyLog) {
    consoleEl.innerHTML = "";
    consoleEl.hidden = true;
    incidentEl.hidden = true;
  } else {
    consoleEl.hidden = false;
    renderIncident();
    consoleEl.innerHTML = consolePanel();
  }
  $("#activity").innerHTML = activityPanel();
}

function render() {
  renderSection();
  renderSidebar();
  if ($("#audit-dialog").open) renderAudit();
  $(".reset").disabled = busy;
  $(".header-actions [data-action=audit]").disabled = busy;
}

async function api(path, options) {
  const response = await fetch(path, { cache: "no-store", ...options });
  const data = await response.json().catch(() => null);
  if (!response.ok || !data) {
    throw new Error(typeof data?.detail === "string" ? data.detail : "CampusFlow could not complete the request. Try again.");
  }
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
      section = workspace.sections[0][0];
      updateResourceLink();
    }
    $("#announcements").textContent = state.audit.at(-1)?.title ?? "Demo reset.";
  } catch (error) {
    notify(error.message || "CampusFlow could not complete the command.");
    try {
      state = await api("/api/state");
    } catch {
      notify("CampusFlow could not refresh the demo. Reload after the server is available.");
    }
  } finally {
    busy = false;
    render();
    if (name.endsWith("_kit")) $("#operation .actions button")?.focus({ preventScroll: true });
    else if (name !== "reset") $(".control .actions :is(button, a)")?.focus({ preventScroll: true });
  }
}

document.addEventListener("click", (event) => {
  const button = event.target.closest("button");
  if (!button || !state) return;
  if (button.dataset.section) {
    section = button.dataset.section;
    updateResourceLink();
    renderSection();
    renderSidebar();
    $("#subtabs [aria-current]").focus({ preventScroll: true });
    return;
  }
  const cctvAction = button.dataset.cctv;
  if (cctvAction) {
    handleCctvAction(cctvAction);
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

async function loadState() {
  const previousState = state;
  try {
    const latest = await api("/api/state");
    if (busy || state !== previousState) return;
    state = latest;
    if (state.local_resource_workflows && view === "resources") {
      try {
        const live = await api("/api/cctv/status");
        cctv = { ...cctv, ...live };
        if (cctv.active && !cctvStreamToken) cctvStreamToken = Date.now();
      } catch {
        // ignore if CCTV unavailable
      }
    }
    notify();
    render();
  } catch (error) {
    if (!busy && state === previousState) {
      notify(error instanceof TypeError ? "CampusFlow could not connect to the server. Reload to try again." : error.message);
      if (!state) $("#operation").replaceChildren();
    }
  }
}

document.title = `${workspace.title} · CampusFlow`;
$("#dashboard-area").textContent = workspace.area;
$("#dashboard-title").textContent = workspace.title;
$("#dashboard-description").textContent = workspace.description;
$("#subtabs").innerHTML = workspace.sections.map(([key, label]) =>
  `<button type="button" aria-controls="operation" data-section="${key}">${label}</button>`
).join("");
document.querySelector(`.workspaces-nav a[href="${workspace.path}"]`).setAttribute("aria-current", "page");
window.addEventListener("pageshow", (event) => {
  if (event.persisted && !busy) loadState();
});
loadState();
