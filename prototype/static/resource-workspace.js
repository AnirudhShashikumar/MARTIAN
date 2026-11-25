const style = document.createElement("link");
style.rel = "stylesheet";
style.href = "/static/resource-workspace.css";
document.head.append(style);

const configs = {
  labs: {
    title: "Labs",
    copy: "Find a lab that fits the group, equipment and timetable.",
    source: "Lab timetable",
    targetLabel: "Preferred lab",
    sample: "Book Lab 2 from 14:20 to 15:05 for 24 students with computers.",
    cta: "Find lab options",
    confirm: "Approve booking",
  },
  library: {
    title: "Library seats",
    copy: "Match a seat to the right zone and protect access when demand rises.",
    source: "Seat ledger",
    targetLabel: "Seating zone",
    sample: "Find a quiet seat from 14:00 to 15:00.",
    cta: "Find a seat",
    confirm: "Place 10-minute hold",
  },
  equipment: {
    title: "Sports equipment",
    copy: "Reserve available equipment and track each item through its return.",
    source: "Item ledger",
    targetLabel: "Equipment type",
    sample: "Reserve two badminton rackets from 14:00 to 15:00.",
    cta: "Check stock",
    confirm: "Confirm reservation",
  },
};

const statuses = {
  pending: "Review needed", cancel_pending: "Cancellation review", unavailable: "Unavailable",
  booked: "Booked", held: "Held", offered: "Offer ready", checked_in: "Checked in",
  queued: "Waitlisted", released: "Released", checked_out: "Checked out", reserved: "Reserved",
  returned: "Returned", canceled: "Canceled", declined: "Declined", expired: "Expired",
  rescheduled: "Rescheduled",
};

const activeStatuses = {
  labs: ["booked", "cancel_pending"],
  library: ["offered", "held", "checked_in"],
  equipment: ["offered", "reserved", "checked_out"],
};

const origin = Date.UTC(2026, 10, 25);
let current;
let currentRun;
const drafts = new Map();

function esc(value) {
  return String(value ?? "").replace(/[&<>"']/g, (char) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  })[char]);
}

function clock(minutes) {
  const value = new Date(origin + minutes * 60000);
  return value.toISOString().slice(11, 16);
}

function dateLabel(day) {
  return new Intl.DateTimeFormat("en-IN", { day: "numeric", month: "short", timeZone: "UTC" })
    .format(new Date(day + "T00:00:00Z"));
}

function dateOf(minutes) {
  return new Date(origin + minutes * 60000).toISOString().slice(0, 10);
}

function range(start, end) {
  return dateLabel(dateOf(start)) + " · " + clock(start) + "–" + clock(end);
}

function minutes(day, time) {
  return (Date.parse(day + "T" + time + ":00Z") - origin) / 60000;
}

function overlaps(first, second) {
  return first.start < second.end && second.start < first.end;
}

function isCurrent(panel) {
  return current === panel && panel.root.dataset.resourceMode === panel.tab;
}

function rowsFor(panel) {
  return panel.state.requests.filter((row) => row.tab === panel.tab);
}

function options(values, selected) {
  return values.map(([value, label]) =>
    '<option value="' + esc(value) + '"' + (value === selected ? " selected" : "") + ">" + esc(label) + "</option>"
  ).join("");
}

function pill(label, tone = "") {
  return '<span class="resource-pill ' + tone + '">' + esc(label) + "</span>";
}

function button(label, action, properties = {}, primary = false, disabled = false) {
  const attrs = Object.entries(properties).map(([key, value]) =>
    ' data-' + key + '="' + esc(value) + '"'
  ).join("");
  return '<button type="button" class="button ' + (primary ? "primary" : "secondary") +
    '" data-resource-action="' + action + '"' + attrs + (disabled ? " disabled" : "") + ">" +
    esc(label) + "</button>";
}

function seed(tab, state) {
  const start = tab === "labs" && state.time <= "14:20" ? "14:20" : state.time;
  return {
    requester: "DEMO-01", day: state.day, start,
    end: clock(Math.min(minutes(state.day, start) + (tab === "labs" ? 45 : 60), minutes(state.day, "23:59"))),
    target: { labs: "LAB-2", library: "Quiet", equipment: "racket" }[tab],
    quantity: { labs: 24, library: 1, equipment: 2 }[tab],
    feature: tab === "labs" ? "Computers" : "Any", session: tab === "labs" ? state.lab_sessions[0] : null,
    protected: false, waitlist: false,
    note: "", replaces: null, intake: null, message: "",
  };
}

async function request(path, body, signal) {
  const settings = body ? {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body),
  } : {};
  const response = await fetch(path, { ...settings, signal, cache: "no-store" });
  const result = await response.json().catch(() => null);
  if (!response.ok || !result) {
    const message = typeof result?.detail === "string" ? result.detail : "Check the required fields and try again.";
    const error = new Error(message);
    error.status = response.status;
    throw error;
  }
  return result;
}

function mainSummary(panel) {
  const { state, tab } = panel;
  const config = configs[tab];
  const pending = rowsFor(panel).filter((row) => ["pending", "cancel_pending", "offered"].includes(row.status)).length;
  const verified = state.audit.filter((entry) => entry.tab === tab && entry.stage === "Verify").length;
  return '<header class="resource-hero"><div><p class="resource-source"><span></span>' + esc(config.source) +
    '</p><h2>' + esc(config.title) + '</h2><p class="resource-deck">' + esc(config.copy) +
    '</p></div><div class="resource-hero-meta"><div><span>Demo clock · IST</span><strong>' +
    esc(state.time) + '</strong></div><div><span>Awaiting action</span><strong>' + pending +
    '</strong></div><div><span>Verified writes</span><strong>' + verified + '</strong></div></div></header>';
}

function draftWindow(panel) {
  const { day, start, end } = panel.draft;
  return { start: minutes(day, start), end: minutes(day, end) };
}

function assetUsage(panel, asset) {
  const window = draftWindow(panel);
  return rowsFor(panel).find((row) =>
    activeStatuses[panel.tab].includes(row.status) && row.assets.includes(asset) && !row.returns[asset]
    && (row.status === "checked_out" || overlaps(row, window))
  );
}

function inventory(panel) {
  const { state, tab, draft } = panel;
  const window = draftWindow(panel);
  if (!Number.isFinite(window.start) || !(window.end > window.start)) {
    return '<p class="resource-empty">Choose a valid start and end time to see availability.</p>';
  }
  if (tab === "labs") {
    return '<ul class="resource-inventory">' + state.labs.map((lab) => {
      const block = state.lab_blocks.find((entry) => entry.asset === lab.id && overlaps(entry, window));
      const booking = assetUsage(panel, lab.id);
      const reason = block?.label ?? (booking ? booking.session ?? "Sample booking" : "");
      return '<li><div><strong>' + esc(lab.name) + '</strong><small>' + lab.capacity + " seats · " +
        esc(lab.features.join(" · ")) + '</small></div>' +
        pill(reason || "Open", reason ? "is-held" : "is-ready") + '</li>';
    }).join("") + '</ul>';
  }
  if (tab === "library") {
    const seats = state.seats.filter((seat) => seat.zone === draft.target);
    return '<div class="resource-seat-grid" aria-label="' + esc(draft.target) + ' seat availability">' +
      seats.map((seat) => {
        const busy = assetUsage(panel, seat.id) || state.seat_blocks.some((row) =>
          row.asset === seat.id && overlaps(row, window));
        const label = busy ? "Allocated" : seat.protected ? "Protected" : "Open";
        const tone = busy ? "is-used" : seat.protected ? "is-protected" : "is-ready";
        return '<span class="resource-seat ' + tone + '"><strong>' + esc(seat.id) + '</strong><small>' +
          label + '</small></span>';
      }).join("") + '</div><p class="resource-note">Protected seats are held for eligible requests and reviewed by library staff.</p>';
  }

  const items = state.items.filter((item) => item.type === draft.target);
  return '<ul class="resource-inventory">' + items.map((item) => {
    const usage = assetUsage(panel, item.id);
    const label = item.condition === "inspection" ? "Inspection" : item.borrowed ? "Sample loan" :
      usage ? (usage.status === "checked_out" && state.clock >= usage.end ? "Overdue" : statuses[usage.status]) : "Available";
    const clear = item.condition === "inspection"
      ? button("Clear inspection", "clear_inspection", { item: item.id }, false, panel.busy) : "";
    return '<li><strong>' + esc(item.id) + '</strong><div class="resource-asset-status">' +
      pill(label, label === "Available" ? "is-ready" : "is-held") + clear + '</div></li>';
  }).join("") + "</ul>";
}

function fields(panel) {
  const { draft, state, tab } = panel;
  const targets = tab === "labs" ? state.labs.map((lab) => [lab.id, lab.name]) :
    tab === "library" ? [["Quiet", "Quiet zone"], ["Group", "Group zone"]] : Object.entries(state.equipment_types);
  const requester = ["DEMO-01", "DEMO-02", "DEMO-03", "DEMO-04"].map((id) => [id, id]);
  const quantity = tab === "library" ? "" : '<label>' + (tab === "labs" ? "Group size" : "Quantity") +
    '<input type="number" name="quantity" min="1" max="' + (tab === "labs" ? 100 : 6) +
    '" required value="' + esc(draft.quantity) + '"></label>';
  const labFields = tab === "labs" ? '<label>Required equipment<select name="feature">' +
    options(["Any", "Computers", "Projector", "Electronics"].map((label) => [label, label]), draft.feature) +
    '</select></label><label>Session type<select name="session">' +
    options(state.lab_sessions.map((label) => [label, label]), draft.session) + '</select></label>' : "";
  return '<div class="resource-fields">' +
    '<label>Sample requester<select name="requester"' + (draft.replaces ? ' disabled' : '') +
    '>' + options(requester, draft.requester) + '</select></label>' +
    '<label>' + configs[tab].targetLabel + '<select name="target">' + options(targets, draft.target) + '</select></label>' +
    '<label>Date<input type="date" name="day" min="' + esc(state.day) + '" value="' + esc(draft.day) + '" required></label>' +
    quantity + '<label>Start time<input type="time" name="start" value="' + esc(draft.start) + '" required></label>' +
    '<label>End time<input type="time" name="end" value="' + esc(draft.end) + '" required></label>' + labFields + '</div>' +
    (tab === "library" ? '<label class="resource-check"><input type="checkbox" name="protected"' +
      (draft.protected ? " checked" : "") + '>Request a protected seat · simulated eligibility</label>' : "") +
    (tab !== "labs" ? '<label class="resource-check"><input type="checkbox" name="waitlist"' +
      (draft.waitlist ? " checked" : "") + (tab === "library"
        ? '>Join the waitlist for automatic assignment</label>' : '>Join the waitlist if this window is full</label>') : "");
}

function form(panel) {
  const { state, draft, tab, busy } = panel;
  const noteReady = Boolean(draft.note.trim().length >= 8);
  const agentMode = state.model_available ? "Gemini ready" : "Structured mode";
  return '<section class="resource-card resource-intake"><div class="resource-card-head"><div><h3>' +
    (draft.replaces ? "Reschedule lab" : "New request") +
    '</h3><p>Set the request, then review the agent’s options.</p></div>' + pill(agentMode, "is-ready") +
    '</div><form data-resource-form><fieldset' + (busy ? " disabled" : "") +
    '>' + fields(panel) + '<div class="resource-form-actions"><button type="submit" class="button primary">' +
    esc(draft.replaces ? "Find new slots" : configs[tab].cta) + '</button>' +
    (draft.replaces ? button("Cancel reschedule", "clear_reschedule") : "") +
    '</div></fieldset></form><details class="resource-note-intake"' +
    (draft.note || draft.message ? " open" : "") + '><summary>Interpret a synthetic note</summary>' +
    '<label class="resource-note-label">Sample note<textarea name="note" rows="2" maxlength="360" placeholder="' +
    esc(configs[tab].sample) + '"' + (busy ? " disabled" : "") + '>' + esc(draft.note) + '</textarea></label>' +
    '<div class="resource-form-actions">' + button("Use example", "sample_note", {}, false, busy) +
    button("Interpret note", "interpret", {}, false, busy || !noteReady) + '</div><p class="resource-note" aria-live="polite">' +
    esc(draft.message || (state.model_available ? "The model can select a read-only lookup or ask for clarification."
      : "Gemini is offline. The form provides the complete workflow.")) + '</p></details></section>';
}

function namedAssets(panel, assets) {
  return assets.map((id) => panel.state.labs.find((lab) => lab.id === id)?.name ?? id).join(", ");
}

function reviewButtons(panel, row) {
  const proposal = row.proposal;
  if (!proposal) return "";
  const choices = proposal.choices.map((choice, index) => {
    const label = index ? "Approve alternative" :
      row.tab === "library" && row.protected ? "Approve protected seat" : configs[panel.tab].confirm;
    const action = button(label, "review", {
      id: row.id, proposal: proposal.id, choice: choice.id, role: proposal.role, decision: "approve",
    }, !index, panel.busy);
    return '<li><div><strong>' + esc(namedAssets(panel, choice.assets)) + '</strong><small>' +
      esc(range(choice.start, choice.end)) + '</small></div>' + action + '</li>';
  }).join("");
  const attributes = { id: row.id, proposal: proposal.id, role: proposal.role };
  return (choices ? '<ul class="resource-options">' + choices + '</ul>' : "") +
    '<div class="resource-request-actions"><span class="resource-note">Simulated reviewer · ' + esc(proposal.role) + '</span>' +
    (row.status === "cancel_pending"
      ? button("Approve cancellation", "review", { ...attributes, decision: "approve" }, true, panel.busy) : "") +
    button("Decline", "review", { ...attributes, decision: "decline" }, false, panel.busy) +
    (row.status === "pending" && panel.state.clock <= row.start
      ? button("Refresh options", "replan", { id: row.id, role: "Requester" }, false, panel.busy) : "") +
    '</div>';
}

function rowActions(panel, row) {
  const action = (label, name, role = "Requester", primary = false, extra = {}, disabled = false) =>
    button(label, name, { id: row.id, role, ...extra }, primary, panel.busy || disabled);
  const staff = row.protected ? "Library staff" : "Requester";
  if (row.proposal) return reviewButtons(panel, row);
  if (row.status === "unavailable" || row.status === "expired") {
    return (panel.state.clock <= row.start ? action("Refresh options", "replan") : "") +
      (row.tab !== "labs" && row.status === "unavailable" && panel.state.clock < row.end
        ? action("Join waitlist", "queue", "Requester", true) : "");
  }
  if (row.status === "queued") return action("Leave waitlist", "cancel");
  if (row.tab === "labs" && row.status === "booked") {
    return action("Reschedule", "reschedule") + action("Request cancellation", "cancel", "Lab coordinator");
  }
  if (row.status === "offered" && row.tab === "equipment") {
    return action("Claim offer", "claim", staff, true) + action("Decline offer", "cancel");
  }
  if (row.status === "held" || (row.status === "offered" && row.tab === "library")) {
    return action("Check in", "check_in", staff, true, {}, panel.state.clock < row.start) +
    action("Release seat", "release", staff);
  }
  if (row.status === "checked_in") return action("Release seat", "release", staff);
  if (row.status === "reserved") return action("Confirm pickup", "checkout", "Sports desk", true, {}, panel.state.clock < row.start) +
    action("Cancel reservation", "cancel");
  if (row.status === "checked_out") {
    return '<ul class="resource-options resource-returns">' + row.assets.map((item) =>
      '<li><strong>' + esc(item) + '</strong><div class="resource-asset-status">' +
      (row.returns[item] ? pill(row.returns[item] === "damaged" ? "Under inspection" : "Returned", "is-ready") :
        action("Return good", "return", "Sports desk", false, { item, condition: "good" }) +
        action("Report damage", "return", "Sports desk", false, { item, condition: "damaged" })) +
      '</div></li>'
    ).join("") + "</ul>";
  }
  return "";
}

function requestRows(panel) {
  const list = rowsFor(panel);
  if (!list.length) return '<p class="resource-empty">Requests and verified outcomes will appear here.</p>';
  return '<ul class="resource-requests">' + list.map((row) => {
    const label = row.status === "checked_out" && panel.state.clock >= row.end ? "Overdue" :
      row.status === "offered" && row.tab === "library" ? "Held" : statuses[row.status];
    const tone = ["unavailable", "expired", "queued"].includes(row.status) || label === "Overdue"
      ? "is-held" : "is-ready";
    const hold = ["offered", "held"].includes(row.status) ? ' · Expires ' + clock(row.hold_until) : "";
    const asset = row.assets.length ? namedAssets(panel, row.assets) :
      panel.state.labs.find((lab) => lab.id === row.target)?.name ??
      panel.state.equipment_types[row.target] ?? row.target;
    return '<li class="resource-request" id="req-' + esc(row.id) + '" tabindex="-1"><div class="resource-request-head"><div><h4>' +
      esc(asset) + '</h4><p>' + esc([row.session, row.requester, range(row.start, row.end) + hold].filter(Boolean).join(" · ")) + '</p></div>' +
      pill(label, tone) + '</div>' + (row.reason ? '<p class="resource-reason">' + esc(row.reason) + '</p>' : "") +
      '<div class="resource-request-actions">' + rowActions(panel, row) + '</div>' +
      button("View request trace", "trace", { id: row.id }, false, panel.busy) + '</li>';
  }).join("") + "</ul>";
}

function audit(panel) {
  const entries = panel.state.audit.filter((event) => event.tab === panel.tab &&
    (!panel.trace || event.request_id === panel.trace));
  const rows = entries.slice().reverse().map((entry) => '<li><div><span>' + esc(entry.stage) + '</span><time>' +
    esc(clock(entry.time)) + '</time></div><div><strong>' + esc(entry.title) + '</strong><p>' +
    esc(entry.detail) + '</p><small>' + esc(entry.source + " · Revision " + entry.revision +
      (entry.role ? " · " + entry.role : "")) + '</small></div></li>').join("");
  return '<section class="resource-card resource-audit" id="resource-trace" tabindex="-1"><div class="resource-card-head">' +
    '<div><h3>Decision trace</h3><p>Evidence, policy decisions and SQLite readback.</p></div>' +
    (panel.trace ? button("Show all", "trace", {}, false, panel.busy) : "") + '</div>' +
    (rows ? '<ol>' + rows + '</ol>' : '<p class="resource-empty">No decisions recorded for this view.</p>') + '</section>';
}

function render(panel) {
  if (!isCurrent(panel)) return;
  panel.root.innerHTML = mainSummary(panel) +
    '<p class="resource-status" role="status">' + esc(panel.notice || "") + '</p>' +
    (panel.error ? '<p class="resource-error" role="alert">' + esc(panel.error) + '</p>' : "") +
    '<div class="resource-grid"><div class="resource-column"><section class="resource-card"><div class="resource-card-head">' +
    '<div><h3>Availability</h3><p id="resource-window"></p></div>' +
    button("Advance 10 min", "advance", {}, false, panel.busy) +
    '</div><div data-resource-inventory></div></section><section class="resource-card">' +
    '<div class="resource-card-head"><div><h3>Requests and allocations</h3><p>Current sample run</p></div></div>' +
    requestRows(panel) + '</section></div><div class="resource-column">' + form(panel) + audit(panel) + '</div></div>';
  renderInventory(panel);
  panel.root.oninput = (event) => edit(panel, event);
  panel.root.onchange = (event) => edit(panel, event);
  panel.root.onsubmit = (event) => {
    if (!event.target.matches("[data-resource-form]")) return;
    event.preventDefault();
    submit(panel);
  };
  panel.root.onclick = (event) => {
    const control = event.target.closest("[data-resource-action]");
    if (control) handle(panel, control);
  };
}

function renderInventory(panel) {
  const window = draftWindow(panel);
  panel.root.querySelector("#resource-window").textContent = Number.isFinite(window.start) && window.end > window.start
    ? range(window.start, window.end) + " IST" : "Select a time window";
  panel.root.querySelector("[data-resource-inventory]").innerHTML = inventory(panel);
}

function edit(panel, event) {
  const field = event.target;
  if (!field.name || !(field.name in panel.draft)) return;
  panel.draft[field.name] = field.type === "checkbox" ? field.checked :
    field.name === "quantity" ? Number(field.value) : field.value;
  if (panel.draft.intake) {
    panel.draft.message = "The draft changed. The next proposal will use the edited form.";
    panel.root.querySelector(".resource-note-intake [aria-live]").textContent = panel.draft.message;
  }
  panel.draft.intake = null;
  if (field.name === "note") {
    panel.root.querySelector('[data-resource-action="interpret"]').disabled = panel.draft.note.trim().length < 8;
  }
  if (["day", "start", "end", "target"].includes(field.name)) renderInventory(panel);
}

function key() {
  if (crypto.randomUUID) return crypto.randomUUID();
  return Array.from(crypto.getRandomValues(new Uint8Array(16)), (byte) => byte.toString(16).padStart(2, "0")).join("");
}

async function mutate(panel, command) {
  if (panel.busy) return;
  const oldBusyKey = panel.retry?.command;
  const fingerprint = JSON.stringify(command);
  const requestKey = oldBusyKey === fingerprint ? panel.retry.key : key();
  panel.busy = true;
  panel.error = "";
  panel.notice = "Checking the latest ledger…";
  render(panel);
  let focusId;
  try {
    const result = await request("/api/resources/command", {
      ...command, tab: panel.tab, run_id: panel.runId, key: requestKey,
    });
    panel.state = result.state;
    panel.retry = null;
    panel.notice = "SQLite readback verified · revision " + result.receipt.revision;
    if (command.action === "submit") {
      panel.draft.replaces = null;
      panel.draft.intake = null;
    }
    if (command.action === "advance" && draftWindow(panel).start < panel.state.clock) {
      const defaults = seed(panel.tab, panel.state);
      panel.draft.day = panel.state.day;
      panel.draft.start = panel.state.time;
      if (draftWindow(panel).end <= panel.state.clock) panel.draft.end = defaults.end;
      panel.draft.intake = null;
    }
    focusId = panel.state.requests.find((row) => row.id === result.receipt.subject)?.id;
  } catch (error) {
    panel.notice = "";
    panel.error = error.message;
    panel.retry = error.status ? null : { command: fingerprint, key: requestKey };
    if (error.status === 409) {
      const result = await request("/api/resources").catch(() => null);
      if (result?.state.run_id === panel.runId) panel.state = result.state;
      if (result && result.state.run_id !== panel.runId) panel.error = "The demo was reset. Reload to start again.";
    }
  } finally {
    panel.busy = false;
    render(panel);
    if (isCurrent(panel)) {
      if (focusId) panel.root.querySelector("#req-" + focusId)?.focus({ preventScroll: true });
      else panel.root.querySelector('[data-resource-action="' + command.action + '"]')?.focus({ preventScroll: true });
    }
  }
}

function submit(panel) {
  const { requester, day, start, end, quantity, target, feature, session, protected: protectedSeat, waitlist, replaces, intake } = panel.draft;
  mutate(panel, {
    action: "submit", requester, day, start, end, quantity, target, feature, session, protected: protectedSeat,
    waitlist, replaces, intake_id: intake,
  });
}

async function interpret(panel) {
  if (panel.busy) return;
  const note = panel.draft.note.trim();
  if (note.length < 8) return;
  panel.draft.intake = null;
  panel.busy = true;
  panel.error = "";
  panel.draft.message = "Checking the request note…";
  render(panel);
  const abort = new AbortController();
  const deadline = setTimeout(() => abort.abort(), 5500);
  try {
    const response = await request("/api/resources/interpret", { run_id: panel.runId, tab: panel.tab, note }, abort.signal);
    if (response.fields) {
      const { tab, ...fields } = response.fields;
      Object.assign(panel.draft, fields, { intake: response.intake_id });
    }
    panel.draft.message = response.message;
    const result = await request("/api/resources", null, abort.signal);
    if (result.state.run_id === panel.runId) panel.state = result.state;
  } catch (error) {
    panel.draft.message = error.name === "AbortError" ? "Gemini timed out. Continue using the form." : error.message;
  } finally {
    clearTimeout(deadline);
    panel.busy = false;
    render(panel);
    if (isCurrent(panel)) panel.root.querySelector('[data-resource-action="interpret"]')?.focus();
  }
}

function handle(panel, control) {
  if (panel.busy) return;
  const { resourceAction: action, id, role, proposal, choice, decision, item, condition } = control.dataset;
  if (action === "sample_note") {
    panel.draft.note = configs[panel.tab].sample;
    panel.draft.intake = null;
    panel.draft.message = "";
    render(panel);
    panel.root.querySelector('[name="note"]').focus();
  } else if (action === "interpret") {
    interpret(panel);
  } else if (action === "trace") {
    panel.trace = id ?? null;
    render(panel);
    panel.root.querySelector("#resource-trace").focus();
  } else if (action === "reschedule") {
    const row = rowsFor(panel).find((candidate) => candidate.id === id);
    Object.assign(panel.draft, {
      requester: row.requester, target: row.assets[0], quantity: row.quantity,
      day: dateOf(row.start), start: clock(row.start), end: clock(row.end), feature: row.feature,
      session: row.session ?? panel.state.lab_sessions[0],
      replaces: row.id, intake: null,
    });
    render(panel);
    panel.root.querySelector('[name="start"]').focus();
  } else if (action === "clear_reschedule") {
    panel.draft.replaces = null;
    render(panel);
    panel.root.querySelector('[name="target"]').focus();
  } else if (action === "clear_inspection") {
    mutate(panel, { action, item, role: "Sports desk" });
  } else if (action === "review") {
    mutate(panel, { action, request_id: id, proposal_id: proposal, choice_id: choice ?? null, decision, role });
  } else if (action === "return") {
    mutate(panel, { action, request_id: id, item, condition, role });
  } else if (action === "advance") {
    mutate(panel, { action });
  } else {
    mutate(panel, { action, request_id: id, role });
  }
}

async function load(panel) {
  panel.root.innerHTML = '<section class="resource-card"><p role="status">Reading campus resources…</p></section>';
  try {
    const result = await request("/api/resources");
    if (!isCurrent(panel)) return;
    if (result.state.run_id !== panel.runId) throw new Error("The demo changed. Reload this dashboard.");
    panel.state = result.state;
    panel.draft = drafts.get(panel.tab) ?? seed(panel.tab, panel.state);
    drafts.set(panel.tab, panel.draft);
    render(panel);
  } catch (error) {
    if (!isCurrent(panel)) return;
    panel.root.innerHTML = '<section class="resource-card"><p class="resource-error" role="alert">' +
      esc(error.message) + '</p>' + button("Try again", "retry", {}, true) + '</section>';
    panel.root.onclick = (event) => {
      if (event.target.closest('[data-resource-action="retry"]')) load(panel);
    };
  }
}

export function mount(root, tab, runId) {
  if (current?.root === root && current.tab === tab && current.runId === runId) return;
  if (currentRun !== runId) drafts.clear();
  currentRun = runId;
  current = { root, tab, runId };
  load(current);
}

export function unmount(root) {
  if (!current || current.root !== root) return;
  root.onclick = null;
  root.onsubmit = null;
  root.oninput = null;
  root.onchange = null;
  current = null;
}
