"""Synthetic fixtures and domain policies for the Checkpoint Alpha scenario."""

from uuid import uuid4


NOTE = "Lab induction moved to Lab 2 and is running 20 minutes late. Guests are at Gate A."
SESSION_ID = "LAB-IND-04"
SESSION = {
    "id": SESSION_ID,
    "name": "Lab induction",
    "revision": "TT-018",
    "previous_room": "C-101",
    "room": "Lab 2",
    "previous_start": "14:00",
    "previous_end": "14:45",
    "start": "14:20",
    "end": "15:05",
    "arrival_window": "14:00–14:35",
    "overflow_opens_at": 0,
    "overflow_closes_at": 35 * 60,
}
ROOM_GUARD = {"min_vacant_seconds": 20, "max_sample_age": 12, "min_confidence": 0.9}
EQUIPMENT = {"kit": "KIT-05", "total": 6, "available": 4, "checked_out": False}
ACTIVE = {"Lights": "On", "Fans": "On", "Projector": "On"}
STANDBY = {"Lights": "Off", "Fans": "Off", "Projector": "Standby"}
ROLES = {"parking": "Parking attendant", "room": "Facilities supervisor"}


class ScenarioError(Exception):
    """A command conflicts with the current demo state or its policy."""


def identifier():
    return uuid4().hex


def fixture():
    bays = [
        {"id": "C-01", "kind": "Car", "policy": "General", "vehicle": "CAR-021"},
        {"id": "C-02", "kind": "Car", "policy": "General", "vehicle": "CAR-034"},
        {"id": "C-03", "kind": "Car", "policy": "General", "vehicle": "CAR-056"},
        {"id": "C-04", "kind": "Car", "policy": "Accessible", "vehicle": None},
        {"id": "C-05", "kind": "Car", "policy": "Reserved", "vehicle": None},
        {"id": "B-01", "kind": "Bike", "policy": "General", "vehicle": "BIKE-011"},
        {"id": "B-02", "kind": "Bike", "policy": "General", "vehicle": "BIKE-013"},
        {"id": "B-03", "kind": "Bike", "policy": "General", "vehicle": None},
        {"id": "OV-01", "kind": "Car", "policy": "Overflow", "vehicle": None},
    ]
    return {
        "id": identifier(),
        "clock": 0,
        "phase": "baseline",
        "session": None,
        "intake": None,
        "parking_version": 0,
        "room_version": 0,
        "bays": bays,
        "gate": [
            {"vehicle": bay["vehicle"], "kind": bay["kind"], "status": "Parked",
             "bay": bay["id"], "entered": -600 + index * 60, "exited": None}
            for index, bay in enumerate(bays) if bay["vehicle"]
        ],
        "events": [],
        "equipment": dict(EQUIPMENT),
        "room": {"samples": [], "hold": False, "booking": True, "devices": dict(ACTIVE)},
        "branches": {"parking": {"status": "idle"}, "room": {"status": "idle"}},
    }


def audit(entries, state, stage, title, detail, branch="incident"):
    entries.append({
        "time": state["clock"], "stage": stage, "branch": branch,
        "title": title, "detail": detail,
    })


def require(condition, reason):
    if not condition:
        raise ScenarioError(reason)


def inject_change(state, entries):
    require(state["phase"] == "baseline", "The schedule change has already arrived.")
    state["phase"] = "detected"
    audit(entries, state, "Sense", "Schedule change received", NOTE)
    arrival(state, entries, "GATE-ARR-078", "CAR-078", "Car")
    arrival(state, entries, "GATE-ARR-014", "BIKE-014", "Bike")


def arrival(state, entries, event, vehicle, kind):
    if event in state["events"]:
        return
    require(not any(record["vehicle"] == vehicle and record["status"] != "Departed"
                    for record in state["gate"]), "This vehicle already has an active gate entry.")
    state["events"].append(event)
    state["gate"].append({
        "vehicle": vehicle, "kind": kind, "status": "Waiting", "bay": None,
        "entered": state["clock"], "exited": None,
    })
    state["parking_version"] += 1
    audit(entries, state, "Sense", f"{vehicle} at Gate A",
          f"{event} · {kind} arrival recorded.", "parking")


def free_bays(state, kind, policy="General"):
    return sorted(
        (bay for bay in state["bays"]
         if bay["kind"] == kind and bay["policy"] == policy and bay["vehicle"] is None),
        key=lambda bay: bay["id"],
    )


def waiting(state, kind):
    return sorted(
        (event for event in state["gate"] if event["kind"] == kind and event["status"] == "Waiting"),
        key=lambda event: event["entered"],
    )


def park(state, record, bay):
    require(record["status"] == "Waiting" and bay["vehicle"] is None
            and record["kind"] == bay["kind"], "The vehicle or bay changed. Check capacity again.")
    bay["vehicle"] = record["vehicle"]
    record.update(bay=bay["id"], status="Parked")
    state["parking_version"] += 1


def assign_general(state, entries):
    for kind in ("Car", "Bike"):
        for record, bay in zip(waiting(state, kind), free_bays(state, kind)):
            park(state, record, bay)
            audit(entries, state, "Act", f"{record['vehicle']} assigned {bay['id']}",
                  f"First eligible {kind.lower()} arrival · general capacity.", "parking")


def propose(state, entries, branch, detail, **target):
    proposal = {
        "id": identifier(), "version": state[f"{branch}_version"],
        "status": "pending", "detail": detail, **target,
    }
    state["branches"][branch] = proposal
    title = "Temporary overflow proposed" if branch == "parking" else "Room standby proposed"
    audit(entries, state, "Plan", title, detail, branch)


def hold(state, entries, branch, reason, title):
    current = state["branches"][branch]
    if current["status"] == "held" and current["detail"] == reason:
        return
    blocked = current["status"] == "pending"
    state["branches"][branch] = {"status": "held", "detail": reason}
    audit(entries, state, "Adapt", title, reason, branch)
    if blocked and branch == "room":
        audit(entries, state, "Verify", "Pending standby blocked",
              "The proposal was revoked before any device write.", "room")


def parking_plan(state, entries):
    assign_general(state, entries)
    if state["branches"]["parking"]["status"] == "verified":
        return
    cars = waiting(state, "Car")
    if not cars:
        assigned = next((record for record in state["gate"]
                         if record["vehicle"] == "CAR-078" and record["status"] == "Parked"), None)
        if assigned:
            require(any(bay["id"] == assigned["bay"] and bay["vehicle"] == assigned["vehicle"]
                        for bay in state["bays"]), "Gate ledger and general bay disagree.")
            state["branches"]["parking"] = {
                "status": "verified", "vehicle": assigned["vehicle"], "bay": assigned["bay"],
                "detail": "Gate ledger and general bay agree.",
            }
            audit(entries, state, "Verify", f"{assigned['bay']} general assignment verified",
                  "The first eligible car used a regular bay after an exit.", "parking")
        return
    overflow = free_bays(state, "Car", "Overflow")
    session = state["session"]
    if not overflow or not session["overflow_opens_at"] <= state["clock"] < session["overflow_closes_at"]:
        hold(state, entries, "parking", "No eligible overflow in the current window. Parking staff review.",
             "Overflow unavailable")
        return
    propose(state, entries, "parking",
            "General car bays are full. Accessible and reserved bays stay protected. "
            "Offer the first eligible car the designated overflow bay until the arrival window closes.",
            vehicle=cars[0]["vehicle"], bay=overflow[0]["id"])


def room_problem(state):
    room = state["room"]
    samples = room["samples"]
    if room["hold"]:
        return "Facilities manual hold is active. Devices require staff review."
    if room["booking"]:
        return "The former room has a protected booking. Keep its devices on."
    if not samples or state["clock"] - samples[-1]["at"] > ROOM_GUARD["max_sample_age"]:
        return "Occupancy evidence is stale or missing. A fresh sequence is required."
    if samples[-1]["count"] > 0:
        return "A fresh occupancy event shows 1 person in C-101. Devices stay on."
    if samples[-1]["confidence"] < ROOM_GUARD["min_confidence"]:
        return "Occupancy confidence is below policy. Request a fresh reading."
    consecutive = []
    for sample in reversed(samples):
        if (sample["count"] or sample["confidence"] < ROOM_GUARD["min_confidence"]
                or (consecutive and consecutive[-1]["at"] - sample["at"] > ROOM_GUARD["max_sample_age"])):
            break
        consecutive.append(sample)
    if consecutive[0]["at"] - consecutive[-1]["at"] < ROOM_GUARD["min_vacant_seconds"]:
        return "The vacancy interval is incomplete. Wait for sustained vacancy."
    return None


def room_plan(state, entries):
    if state["branches"]["room"]["status"] == "verified":
        return
    reason = room_problem(state)
    if reason:
        hold(state, entries, "room", reason, "C-101 safety hold")
        return
    propose(state, entries, "room",
            "C-101 has 20 seconds of continuous synthetic vacancy. "
            "The calendar is clear and the manual override is off.", room="C-101")


def seed_vacancy(state):
    state["room"]["samples"] = [
        {"at": state["clock"] - age, "count": 0, "confidence": 0.98}
        for age in (20, 10, 0)
    ]
    state["room_version"] += 1


def run_agent(state, entries, choice):
    require(state["phase"] in {"detected", "clarification"}, "First trigger the schedule change.")
    state["intake"] = choice
    if choice["mode"] == "clarification":
        state["phase"] = "clarification"
        audit(entries, state, "Think", "Coordinator confirmation requested", choice["detail"])
        return
    state.update(phase="active", session=dict(SESSION))
    state["room"]["booking"] = False
    audit(entries, state, "Think", "Revised timetable verified",
          f"{choice['detail']} {SESSION['revision']} confirms a later start, 14:20–15:05 in Lab 2.")
    audit(entries, state, "Sense", "Capacity and former room checked",
          "Gate A shows separate car and bike capacity. The C-101 booking was released by this timetable revision.")
    seed_vacancy(state)
    parking_plan(state, entries)
    room_plan(state, entries)


def room_event(state, entries, action):
    require(state["phase"] == "active" and state["branches"]["room"]["status"] != "verified",
            "Room evidence is available while a room decision is open.")
    previous = state["branches"]["room"]["status"]
    if action == "vacant":
        state["clock"] += ROOM_GUARD["min_vacant_seconds"] + 1
        seed_vacancy(state)
        audit(entries, state, "Sense", "New vacancy sequence received",
              "Three fresh synthetic samples cover 20 seconds of continuous vacancy.", "room")
    elif action == "occupied":
        state["clock"] += 1
        state["room"]["samples"].append({"at": state["clock"], "count": 1, "confidence": 0.99})
        state["room_version"] += 1
        audit(entries, state, "Sense", "Someone returned to C-101",
              "Synthetic occupancy count increased from zero to one.", "room")
    elif action == "stale":
        state["clock"] += 13
        state["room_version"] += 1
    elif action == "override":
        state["room"]["hold"] = not state["room"]["hold"]
        state["room_version"] += 1
        audit(entries, state, "Sense", "Facilities override changed",
              "Manual hold activated." if state["room"]["hold"] else "Manual hold released.", "room")
    if previous == "rejected" and action != "vacant":
        return
    room_plan(state, entries)


def exit_vehicle(state, entries, event, vehicle):
    require(state["phase"] == "active", "Verify the schedule before using gate controls.")
    if event in state["events"]:
        return
    record = next((item for item in state["gate"] if item["vehicle"] == vehicle), None)
    require(record is not None and record["status"] == "Parked", "There is no matching active gate entry.")
    bay = next(item for item in state["bays"] if item["id"] == record["bay"])
    require(bay["vehicle"] == vehicle, "Bay and gate ledger disagree. Escalate to parking staff.")
    bay["vehicle"] = None
    record.update(status="Departed", exited=state["clock"])
    state["events"].append(event)
    state["parking_version"] += 1
    audit(entries, state, "Verify", f"{vehicle} exited and {bay['id']} reopened",
          f"{event} · the gate ledger and bay occupancy agree.", "parking")
    if state["branches"]["parking"]["status"] != "rejected":
        parking_plan(state, entries)


def expire_overflow(state, entries):
    require(state["phase"] == "active", "The arrival window has yet to be confirmed.")
    if state["clock"] >= SESSION["overflow_closes_at"]:
        return
    state["clock"] = SESSION["overflow_closes_at"]
    state["parking_version"] += 1
    audit(entries, state, "Adapt", "Overflow window closed",
          "No new overflow assignments. Occupied bays remain assigned until confirmed exit.", "parking")
    if state["branches"]["parking"]["status"] == "pending":
        parking_plan(state, entries)
    if state["branches"]["room"]["status"] == "pending":
        room_plan(state, entries)


def review(state, entries, branch, token, role, decision):
    require(role == ROLES[branch], "This proposal requires the designated reviewer role.")
    proposal = state["branches"][branch]
    require(proposal["status"] == "pending" and proposal["id"] == token,
            "This approval is no longer current. Review the newest evidence.")
    require(proposal["version"] == state[f"{branch}_version"],
            "Evidence changed. A fresh proposal is required.")
    if decision == "reject":
        proposal.update(status="rejected", detail=f"{role} declined the proposal. Staff review required.")
        audit(entries, state, "Explain", "Proposal declined", proposal["detail"], branch)
        return None

    if branch == "parking":
        targets = waiting(state, "Car")
        bays = free_bays(state, "Car", "Overflow")
        session = state["session"]
        require(session["overflow_opens_at"] <= state["clock"] < session["overflow_closes_at"],
                "The overflow window is closed.")
        require(targets and targets[0]["vehicle"] == proposal["vehicle"]
                and bays and bays[0]["id"] == proposal["bay"] and not free_bays(state, "Car"),
                "Parking evidence changed. Check eligibility and availability again.")
        park(state, targets[0], bays[0])
        title = f"{proposal['bay']} assigned to {proposal['vehicle']}"
        detail = "Overflow assignment verified in the synthetic gate and bay records."
    else:
        reason = room_problem(state)
        require(reason is None, reason)
        state["room"]["devices"] = dict(STANDBY)
        state["room_version"] += 1
        title = "C-101 standby applied"
        detail = "Mock readback confirms lights and fans off and projector on standby."
    proposal.update(status="verified", detail=detail, approved_by=role)
    audit(entries, state, "Act", title, f"{role} approved the current proposal.", branch)
    return branch


def verify(state, entries, branch):
    proposal = state["branches"][branch]
    if branch == "parking":
        confirmed = any(bay["id"] == proposal["bay"] and bay["vehicle"] == proposal["vehicle"]
                        for bay in state["bays"])
        confirmed = confirmed and any(
            record["vehicle"] == proposal["vehicle"] and record["bay"] == proposal["bay"]
            and record["status"] == "Parked" for record in state["gate"]
        )
        title = f"{proposal['bay']} readback verified"
    else:
        confirmed = state["room"]["devices"] == STANDBY
        title = "C-101 device readback verified"
    require(confirmed, "Readback failed. The change has been rolled back for staff review.")
    audit(entries, state, "Verify", title, proposal["detail"], branch)
    audit(entries, state, "Explain", "Decision recorded",
          f"{proposal['approved_by']} · proposal {proposal['id'][:8]} · "
          f"evidence revision {proposal['version']}.", branch)


def update_equipment(state, entries, checkout):
    item = state["equipment"]
    require(checkout != item["checked_out"], "Refresh the current kit availability.")
    if checkout:
        require(item["available"] > 0, "No synthetic kits are available.")
    item["available"] += -1 if checkout else 1
    item["checked_out"] = checkout
    verb = "checked out" if checkout else "returned"
    audit(entries, state, "Act", f"{item['kit']} {verb}",
          f"Sample inventory now has {item['available']} of {item['total']} kits available.", "resources")


def apply_command(state, command, entries, choice=None):
    """Apply a validated command to a snapshot inside the caller's write transaction."""
    require(state["id"] == command.run_id, "This demo was reset. Reload the current scenario.")
    action = command.action
    branch = None

    if action == "reset":
        return fixture(), branch
    if action == "trigger":
        inject_change(state, entries)
    elif action in {"run", "confirm"}:
        run_agent(state, entries, choice)
    elif action in {"occupied", "vacant", "stale", "override"}:
        room_event(state, entries, action)
    elif action == "expire":
        expire_overflow(state, entries)
    elif action == "exit":
        exit_vehicle(state, entries, "GATE-EXIT-021", "CAR-021")
    elif action == "exit_overflow":
        exit_vehicle(state, entries, "GATE-EXIT-078", "CAR-078")
    elif action in {"checkout_kit", "return_kit"}:
        update_equipment(state, entries, checkout=action == "checkout_kit")
    elif action == "review":
        require(all([command.branch, command.proposal, command.role, command.decision]),
                "Select a proposal and a review decision.")
        branch = review(state, entries, command.branch, command.proposal, command.role, command.decision)

    return state, branch
