"""Policies and sample data for the three local resource workflows."""

from datetime import date, datetime, timedelta
from typing import Annotated, Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

from prototype import scenario


Tab = Literal["labs", "library", "equipment"]
Role = Literal["Requester", "Lab coordinator", "Library staff", "Sports desk"]
ClockTime = Annotated[str, Field(pattern=r"^(?:[01]\d|2[0-3]):[0-5]\d$")]
Ref = Annotated[str, Field(min_length=1, max_length=48)]
DAY = date(2026, 11, 25)
ORIGIN = datetime.combine(DAY, datetime.min.time())
HOLD_MINUTES = 10
ACTIVE_SEATS = {"offered", "held", "checked_in"}
ACTIVE_STOCK = {"offered", "reserved", "checked_out"}
REVIEWERS = {"labs": "Lab coordinator", "library": "Requester", "equipment": "Requester"}
SOURCES = {"labs": "Lab timetable", "library": "Seat ledger", "equipment": "Item ledger"}
LABS = (
    {"id": "LAB-2", "name": "Lab 2", "capacity": 32, "features": ["Computers", "Projector"]},
    {"id": "LAB-1", "name": "Lab 1", "capacity": 28, "features": ["Computers", "Projector"]},
    {"id": "LAB-3", "name": "Lab 3", "capacity": 40, "features": ["Projector", "Electronics"]},
)
SEATS = tuple(
    {"id": f"{prefix}{number:02d}", "zone": zone, "protected": number in protected}
    for prefix, zone, count, protected in (
        ("Q", "Quiet", 12, {11, 12}), ("G", "Group", 8, {8}),
    )
    for number in range(1, count + 1)
)
EQUIPMENT_TYPES = {"racket": "Badminton racket", "ball": "Football", "kit": "Multi-sport kit"}
LAB_SESSIONS = ("Practical session", "Lab induction", "Workshop", "Project work")
LAB_BLOCKS = (
    {"id": scenario.SESSION_ID, "asset": "LAB-2", "start": 860, "end": 905,
     "label": "Lab induction", "source": scenario.SESSION["revision"]},
    {"id": "TT-LAB-1", "asset": "LAB-1", "start": 930, "end": 990,
     "label": "Maintenance", "source": "TT-018"},
)
SEAT_BLOCKS = tuple(
    {"asset": seat["id"], "start": 840, "end": 1020, "label": "Sample reservation"}
    for seat in SEATS
    if seat["id"] in {*(f"Q{i:02d}" for i in range(1, 10)), "G01", "G02"}
)


class ResourceError(Exception):
    """A request conflicts with resource availability or policy."""


class CommandBase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: Ref
    key: Ref
    tab: Tab


class Submit(CommandBase):
    action: Literal["submit"]
    requester: Literal["DEMO-01", "DEMO-02", "DEMO-03", "DEMO-04"]
    day: date
    start: ClockTime
    end: ClockTime
    quantity: int = Field(ge=1, le=100)
    target: Ref
    feature: Literal["Any", "Computers", "Projector", "Electronics"] = "Any"
    session: Literal["Practical session", "Lab induction", "Workshop", "Project work"] | None = None
    protected: bool = False
    waitlist: bool = False
    replaces: Ref | None = None
    intake_id: Ref | None = None


class Review(CommandBase):
    action: Literal["review"]
    request_id: Ref
    proposal_id: Ref
    choice_id: Ref | None = None
    decision: Literal["approve", "decline"]
    role: Role


class Transition(CommandBase):
    action: Literal["replan", "cancel", "queue", "claim", "check_in", "release", "checkout"]
    request_id: Ref
    role: Role


class Return(CommandBase):
    action: Literal["return"]
    request_id: Ref
    item: Ref
    condition: Literal["good", "damaged"]
    role: Role


class Inspection(CommandBase):
    action: Literal["clear_inspection"]
    item: Ref
    role: Role


class Advance(CommandBase):
    action: Literal["advance"]


Command = Annotated[Submit | Review | Transition | Return | Inspection | Advance, Field(discriminator="action")]


def require(condition, reason):
    if not condition:
        raise ResourceError(reason)


def identifier():
    return uuid4().hex


def clock_parts(minutes):
    current = ORIGIN + timedelta(minutes=minutes)
    return current.date().isoformat(), current.strftime("%H:%M")


def minutes_for(day, time):
    hour, minute = map(int, time.split(":"))
    return (day - DAY).days * 1440 + hour * 60 + minute


def overlaps(first, second):
    return first["start"] < second["end"] and second["start"] < first["end"]


def fixture(legacy_kit):
    items = {}
    for kind, prefix, total, unavailable in (
        ("racket", "RKT", 5, 2),
        ("ball", "BAL", 3, 0),
        ("kit", "KIT", legacy_kit["total"], legacy_kit["total"] - legacy_kit["available"]),
    ):
        if kind == "kit":
            kit_id = legacy_kit["kit"]
            ids = [kit_id] if legacy_kit["checked_out"] else []
            ids += [f"{prefix}-{i:02d}" for i in range(1, total + 1) if f"{prefix}-{i:02d}" != kit_id]
            if not legacy_kit["checked_out"]:
                ids.append(kit_id)
        else:
            ids = [f"{prefix}-{i:02d}" for i in range(1, total + 1)]
        for index, item_id in enumerate(ids):
            items[item_id] = {
                "id": item_id, "type": kind, "condition": "ready",
                "borrowed": index < unavailable,
            }

    return {"clock": 840, "revision": 0, "requests": {}, "items": items,
            "audit": [], "receipts": {}, "intakes": {}}


def record(data, tab, stage, title, detail, request_id=None, role=None):
    data["audit"].append({
        "tab": tab, "stage": stage, "title": title, "detail": detail,
        "request_id": request_id, "role": role, "time": data["clock"],
        "source": SOURCES[tab], "revision": data["revision"],
    })


def event(data, request, stage, title, detail, role=None):
    record(data, request["tab"], stage, title, detail, request["id"], role)


def requests(data, tab):
    return [request for request in data["requests"].values() if request["tab"] == tab]


def find(data, command):
    request = data["requests"].get(command.request_id)
    require(request and request["tab"] == command.tab, "This request is no longer in the current demo.")
    return request


def active_assets(request):
    return [asset for asset in request.get("assets", []) if asset not in request.get("returns", {})]


def conflicts(data, request, asset):
    tab = request["tab"]
    if tab == "labs":
        if any(block["asset"] == asset and overlaps(block, request) for block in LAB_BLOCKS):
            return "Timetable booking or maintenance"
        statuses = {"booked", "cancel_pending"}
    elif tab == "library":
        if any(block["asset"] == asset and overlaps(block, request) for block in SEAT_BLOCKS):
            return "Seat already reserved"
        statuses = ACTIVE_SEATS
    else:
        item = data["items"][asset]
        if item["condition"] == "inspection":
            return "Item awaiting inspection"
        if item["borrowed"]:
            return "Item already checked out"
        statuses = ACTIVE_STOCK

    exclusion_ids = {request.get("id"), request.get("replaces")}
    for other in requests(data, tab):
        if (other["id"] in exclusion_ids or other["status"] not in statuses
                or asset not in active_assets(other)):
            continue
        if tab == "equipment" and other["status"] == "checked_out":
            return "Item already checked out"
        if overlaps(other, request):
            return {"labs": "Lab already booked", "library": "Seat already allocated",
                    "equipment": "Item already reserved"}[tab]
    return None


def lab_reason(data, request, lab):
    if request["quantity"] > lab["capacity"]:
        return f"Capacity {lab['capacity']} is below the requested {request['quantity']}"
    if request["feature"] != "Any" and request["feature"] not in lab["features"]:
        return f"{request['feature']} unavailable"
    return conflicts(data, request, lab["id"])


def option(assets, window):
    return {"id": identifier(), "assets": assets, "start": window["start"], "end": window["end"]}


def lab_options(data, request):
    labs = sorted(LABS, key=lambda lab: (lab["id"] != request["target"], lab["id"]))
    preferred = next(lab for lab in labs if lab["id"] == request["target"])
    reason = lab_reason(data, request, preferred)
    choices = []
    for offset in (0, 30, 60, 90):
        window = {**request, "start": request["start"] + offset, "end": request["end"] + offset}
        if window["end"] // 1440 != request["start"] // 1440:
            break
        for lab in labs:
            if not lab_reason(data, window, lab):
                choices.append(option([lab["id"]], window))
                if len(choices) == 3:
                    return choices, reason
    return choices, reason


def seat_options(data, request):
    previous, blocked = seat_transfer(data, request)
    if blocked:
        return [], blocked
    eligible = [
        seat["id"] for seat in SEATS
        if seat["zone"] == request["target"] and seat["protected"] == request["protected"]
        and not conflicts(data, request, seat["id"])
    ]
    choices = [option([asset], request) for asset in eligible[:3]]
    if previous:
        for choice in choices:
            choice["releases_seat"] = previous["id"]
    return choices, None


def seat_transfer(data, request):
    existing = [
        other
        for other in requests(data, "library")
        if other["id"] != request.get("id") and other["requester"] == request.get("requester")
        and other["status"] in ACTIVE_SEATS and overlaps(other, request)
    ]
    if not existing:
        return None, None

    previous = existing[0]
    if (len(existing) == 1 and request["protected"] and not previous["protected"]
            and request["start"] <= max(previous["start"], data["clock"])
            and request["end"] >= previous["end"]):
        return previous, None
    return None, "This requester already has an overlapping seat. Choose another window or release that seat."


def release_for_protected_seat(data, previous, role=None):
    previous.update(status="released", reason="Released when the requester moved to a protected seat.")
    event(data, previous, "Act", "General seat released", previous["reason"], role)


def stock_options(data, request):
    available = sorted(
        item["id"] for item in data["items"].values()
        if item["type"] == request["target"] and not conflicts(data, request, item["id"])
    )
    quantity = request["quantity"]
    groups = [
        available[index:index + quantity]
        for index in range(0, min(len(available) - quantity + 1, quantity * 3), quantity)
    ]
    return [option(group, request) for group in groups], None


FIND_OPTIONS = {"labs": lab_options, "library": seat_options, "equipment": stock_options}


def role_for(request):
    if request["tab"] == "library" and request["protected"]:
        return "Library staff"
    return REVIEWERS[request["tab"]]


def stage(data, request):
    choices, preferred_block = FIND_OPTIONS[request["tab"]](data, request)
    if not choices:
        request["proposal"] = None
        request["status"] = "unavailable"
        request["reason"] = preferred_block or {
            "labs": "No matching lab within 90 minutes of the requested slot.",
            "library": "No eligible seat for that zone and time.",
            "equipment": "Not enough eligible items for that window.",
        }[request["tab"]]
        event(data, request, "Plan", "Capacity unavailable", request["reason"])
        return

    request["status"] = "pending"
    request["reason"] = f"Preferred lab blocked. {preferred_block}." if preferred_block else {
        "labs": "Matched capacity, equipment and open timetable windows.",
        "library": "Matched zone, eligibility and an unclaimed seat window.",
        "equipment": "Matched type, quantity, condition and open stock windows.",
    }[request["tab"]]
    if previous_id := choices[0].get("releases_seat"):
        seat = data["requests"][previous_id]["assets"][0]
        request["reason"] = f"Approval will assign a protected seat and release {seat} in the same step."
    request["proposal"] = {
        "id": identifier(), "revision": data["revision"], "expires": data["clock"] + HOLD_MINUTES,
        "role": role_for(request), "choices": choices,
    }
    event(data, request, "Plan", "Proposal ready", request["reason"])


def queue(data, request):
    require(request["tab"] in {"library", "equipment"} and request["status"] == "unavailable",
            "Only unavailable seat or equipment requests can join the waitlist.")
    previous = None
    if request["tab"] == "library":
        previous, blocked = seat_transfer(data, request)
        require(not blocked, blocked)
    require(not any(other["status"] == "queued" and other["requester"] == request["requester"]
                    and other["target"] == request["target"] and overlaps(other, request)
                    for other in requests(data, request["tab"])),
            "This sample requester already has a waitlist position for that window.")
    request["status"] = "queued"
    request["queued_at"] = len(data["audit"])
    request["reason"] = "Waiting in submission order for the first eligible allocation."
    if previous:
        request["reason"] += f" The agent will release {previous['assets'][0]} when it assigns a protected seat."
    event(data, request, "Adapt", "Waitlist joined", request["reason"])


def submit(data, command):
    start = minutes_for(command.day, command.start)
    end = minutes_for(command.day, command.end)
    require(data["clock"] <= start < end and end <= data["clock"] + 14 * 1440,
            "Choose a future window on one date within the next 14 demo days.")
    require(not command.protected or command.tab == "library", "Protected eligibility applies to library seats.")
    require(not command.replaces or command.tab == "labs", "Only lab bookings support rescheduling.")
    require(command.feature == "Any" or command.tab == "labs", "Equipment requirements apply to lab bookings.")
    require(command.session is None or command.tab == "labs", "Session types apply to lab bookings.")
    targets = {
        "labs": {lab["id"] for lab in LABS},
        "library": {seat["zone"] for seat in SEATS},
        "equipment": EQUIPMENT_TYPES,
    }
    require(command.target in targets[command.tab], "Choose a resource from the catalog.")
    if command.tab == "library":
        require(command.quantity == 1, "Each library request is for one seat.")
    if command.tab == "equipment":
        require(command.quantity <= 6, "Request up to six items at a time.")
    original = data["requests"].get(command.replaces)
    if command.replaces:
        require(original and original["tab"] == "labs" and original["status"] == "booked"
                and original["requester"] == command.requester,
                "Choose an active lab booking from the same sample requester.")

    # Bind a model trace to the exact fields the operator reviewed.
    intake = data["intakes"].pop(command.intake_id, None)
    fields = command.model_dump(mode="json", include={"tab", "day", "start", "end", "target", "quantity", "feature"})
    mode = "Gemini" if intake and intake == fields else "Structured"
    request_id = identifier()
    request = {
        "id": request_id, "tab": command.tab, "requester": command.requester,
        "start": start, "end": end, "target": command.target, "quantity": command.quantity,
        "feature": command.feature, "protected": command.protected, "replaces": command.replaces,
        "session": (command.session or LAB_SESSIONS[0]) if command.tab == "labs" else None,
        "mode": mode, "assets": [], "returns": {}, "proposal": None,
    }
    data["requests"][request_id] = request
    event(data, request, "Observe", "Request received",
          f"{command.requester} requested {command.target} from {command.start} to {command.end}.")
    event(data, request, "Understand", f"{mode} intake",
          f"Confirmed request fields against the {SOURCES[command.tab].lower()}.")
    stage(data, request)
    queue_eligible = command.tab == "equipment" or (command.tab == "library" and not seat_transfer(data, request)[1])
    if request["status"] == "unavailable" and command.waitlist and queue_eligible:
        queue(data, request)
    return request_id


def deadline(data, request, status):
    initial = data["clock"] if status == "offered" and request["tab"] == "equipment" else max(
        data["clock"], request["start"],
    )
    return min(request["end"], initial + HOLD_MINUTES)


def assign(data, request, choice, status):
    request.update(start=choice["start"], end=choice["end"], assets=choice["assets"],
                   status=status, proposal=None, reason=None)
    if status in {"held", "offered"}:
        request["hold_until"] = deadline(data, request, status)


def check_choice(data, request, choice):
    window = {**request, **{key: choice[key] for key in ("start", "end")}}
    require(data["clock"] <= window["start"], "This slot has started. Choose a new window.")
    previous = None
    if request["tab"] == "labs":
        lab = next(lab for lab in LABS if lab["id"] == choice["assets"][0])
        available = not lab_reason(data, window, lab)
    else:
        available = all(not conflicts(data, window, asset) for asset in choice["assets"])
        if request["tab"] == "library":
            previous, blocked = seat_transfer(data, window)
            available = (available and not blocked
                         and (previous["id"] if previous else None) == choice.get("releases_seat"))
    require(available, "Availability changed. Refresh this request to get a new proposal.")
    return previous


def review(data, command):
    request = find(data, command)
    proposal = request["proposal"]
    require(request["status"] in {"pending", "cancel_pending"} and proposal
            and proposal["id"] == command.proposal_id and data["clock"] < proposal["expires"],
            "This proposal is stale or expired. Refresh it before reviewing.")
    require(command.role == proposal["role"], f"Review requires {proposal['role']}.")
    if command.decision == "decline":
        status = "booked" if request["status"] == "cancel_pending" else "declined"
        request.update(status=status, proposal=None, reason="The reviewer declined this proposal.")
        event(data, request, "Act", "Proposal declined", request["reason"], command.role)
        return request["id"]

    if request["status"] == "cancel_pending":
        request.update(status="canceled", proposal=None, reason="The calendar booking was released.")
        event(data, request, "Act", "Lab booking canceled", request["reason"], command.role)
        return request["id"]

    choice = next((choice for choice in proposal["choices"] if choice["id"] == command.choice_id), None)
    require(choice is not None, "Choose one of the proposed options.")
    if request["replaces"]:
        old = data["requests"].get(request["replaces"])
        require(old and old["status"] == "booked", "The original booking changed. Refresh the schedule.")
    previous_seat = check_choice(data, request, choice)
    if request["replaces"]:
        old.update(status="rescheduled", reason="Replaced by the newly approved booking.")
    if previous_seat:
        release_for_protected_seat(data, previous_seat, command.role)
    status = {"labs": "booked", "library": "held", "equipment": "reserved"}[request["tab"]]
    assign(data, request, choice, status)
    event(data, request, "Act", {"booked": "Lab booked", "held": "Seat held", "reserved": "Items reserved"}[status],
          ", ".join(request["assets"]), command.role)
    return request["id"]


def seat_transition(data, request, action):
    if action == "claim":
        require(request["status"] == "offered", "There is no active offer to claim.")
        request["status"] = "held"
    elif action == "check_in":
        require(request["status"] in {"held", "offered"} and request["start"] <= data["clock"] < request["hold_until"],
                "Check in during your active hold window.")
        request["status"] = "checked_in"
    else:
        require(request["status"] in ACTIVE_SEATS, "There is no active seat to release.")
        request["status"] = "released"


def stock_transition(data, request, action):
    if action == "claim":
        require(request["status"] == "offered", "There is no active offer to claim.")
        request["status"] = "reserved"
    elif action == "checkout":
        require(request["status"] == "reserved" and request["start"] <= data["clock"] < request["end"],
                "Confirm checkout after pickup time and before the reservation ends.")
        require(all(not conflicts(data, request, asset) for asset in active_assets(request)),
                "An item is no longer eligible for checkout.")
        request["status"] = "checked_out"
    else:
        require(request["status"] in {"offered", "reserved"}, "Checked-out items must be returned at the sports desk.")
        request["status"] = "canceled"


def transition(data, command):
    request = find(data, command)
    action = command.action
    tab = request["tab"]

    if action == "replan":
        require(command.role == "Requester", "Refresh the request as its simulated requester.")
        require(request["status"] in {"pending", "unavailable", "expired"} and data["clock"] <= request["start"],
                "This request can no longer be refreshed. Create a new request.")
        stage(data, request)
        return request["id"]

    if action == "queue":
        require(command.role == "Requester", "Join the waitlist as its simulated requester.")
        require(data["clock"] < request["end"], "This request window ended.")
        queue(data, request)
        return request["id"]

    if action == "cancel" and tab == "labs":
        require(command.role == "Lab coordinator", "Cancellation requires Lab coordinator.")
        require(request["status"] in {"booked", "cancel_pending"}, "Only an active lab booking can be canceled.")
        request.update(status="cancel_pending", proposal={
            "id": identifier(), "revision": data["revision"], "role": command.role,
            "expires": data["clock"] + HOLD_MINUTES, "choices": [],
        }, reason="Approve to release this lab booking.")
        event(data, request, "Plan", "Cancellation awaiting review", request["reason"], command.role)
        return request["id"]

    if action == "cancel" and request["status"] == "queued":
        require(command.role == "Requester", "Leave the waitlist as its simulated requester.")
        request["status"] = "canceled"
    elif tab == "library" and action in {"claim", "check_in", "release"}:
        require(command.role == role_for(request), f"This seat action requires {role_for(request)}.")
        seat_transition(data, request, action)
    elif tab == "equipment" and action in {"claim", "checkout", "cancel"}:
        required_role = "Sports desk" if action == "checkout" else "Requester"
        require(command.role == required_role, f"This stock action requires {required_role}.")
        stock_transition(data, request, action)
    else:
        raise ResourceError("This action does not apply to the resource.")
    request["reason"] = None
    titles = {
        "claim": "Offer claimed", "check_in": "Seat check-in confirmed", "release": "Seat released",
        "checkout": "Pickup confirmed", "cancel": "Request canceled",
    }
    event(data, request, "Act", titles[action], ", ".join(request["assets"]) or "Waitlist spot released.", command.role)
    return request["id"]


def return_item(data, command):
    request = find(data, command)
    require(command.tab == "equipment" and command.role == "Sports desk", "Returns require Sports desk.")
    require(request["status"] == "checked_out" and command.item in active_assets(request),
            "That item is not part of an active checkout.")
    request["returns"][command.item] = command.condition
    if not active_assets(request):
        request["status"] = "returned"
    event(data, request, "Act", "Return recorded", f"{command.item} returned · {command.condition}.", command.role)
    if command.condition == "damaged":
        data["items"][command.item]["condition"] = "inspection"
        for reservation in requests(data, "equipment"):
            if reservation["status"] in {"offered", "reserved"} and command.item in reservation["assets"]:
                reservation.update(status="queued", queued_at=len(data["audit"]), assets=[],
                                   reason="The allocated item needs inspection. Rechecking stock.")
                event(data, reservation, "Adapt", "Reservation needs new stock", reservation["reason"])
    return request["id"]


def clear_inspection(data, command):
    item = data["items"].get(command.item)
    require(command.tab == "equipment" and command.role == "Sports desk", "Inspection requires Sports desk.")
    require(item and item["condition"] == "inspection", "Only items under inspection can be cleared.")
    item["condition"] = "ready"
    record(data, "equipment", "Act", "Inspection cleared", command.item, role=command.role)
    return command.item


def expire_and_offer(data):
    for request in data["requests"].values():
        status = request["status"]
        timed_hold = status in {"offered", "held"} and data["clock"] >= request["hold_until"]
        ended = status in {"queued", "checked_in", "reserved"} and data["clock"] >= request["end"]
        if timed_hold or ended:
            request["status"] = "expired"
            request["reason"] = "The hold or resource window ended."
            event(data, request, "Adapt", "Capacity window expired", request["reason"])
        elif status in {"pending", "cancel_pending"} and data["clock"] >= request["proposal"]["expires"]:
            request.update(status="booked" if status == "cancel_pending" else "expired", proposal=None,
                           reason="Review window ended. Request a fresh proposal.")
            event(data, request, "Adapt", "Proposal expired", request["reason"])

    queued = sorted(
        (request for request in data["requests"].values() if request["status"] == "queued"),
        key=lambda request: request["queued_at"],
    )
    allocate_library_waitlist(data, [request for request in queued if request["tab"] == "library"])
    for request in queued:
        if request["tab"] != "equipment":
            continue
        window = {**request, "start": max(request["start"], data["clock"])}
        choices, _ = FIND_OPTIONS[request["tab"]](data, window)
        if choices:
            assign(data, request, choices[0], "offered")
            request["reason"] = "The first eligible waitlisted request received this offer."
            event(data, request, "Adapt", "Waitlist offer ready", f"{', '.join(request['assets'])} · {request['reason']}")


def allocate_library_waitlist(data, queued):
    # Restart in FIFO order after an assignment, since a protected-seat switch can free a general seat.
    while queued:
        for index, request in enumerate(queued):
            window = {**request, "start": max(request["start"], data["clock"])}
            choices, _ = seat_options(data, window)
            if not choices:
                continue
            choice = choices[0]
            if previous_id := choice.get("releases_seat"):
                release_for_protected_seat(data, data["requests"][previous_id], "CampusFlow agent")
            assign(data, request, choice, "held")
            request["reason"] = "Automatically assigned to the first eligible requester on the waitlist."
            event(data, request, "Adapt", "Waitlist seat assigned", f"{request['assets'][0]} · {request['reason']}",
                  "CampusFlow agent")
            event(data, request, "Verify", "Assigned seat read back", f"{request['assets'][0]} held for {request['requester']}.")
            queued.pop(index)
            break
        else:
            break


def apply(data, command):
    expire_and_offer(data)
    if isinstance(command, Advance):
        day, _ = clock_parts(data["clock"])
        require(day < (DAY + timedelta(days=14)).isoformat(), "The demo clock reached its 14-day limit.")
        data["clock"] += HOLD_MINUTES
        record(data, command.tab, "Observe", "Demo clock advanced", "Ten simulated minutes elapsed.")
        subject = "clock"
    elif isinstance(command, Submit):
        subject = submit(data, command)
    elif isinstance(command, Review):
        subject = review(data, command)
    elif isinstance(command, Return):
        subject = return_item(data, command)
    elif isinstance(command, Inspection):
        subject = clear_inspection(data, command)
    else:
        subject = transition(data, command)

    expire_and_offer(data)
    return subject


def verify(data):
    """Verify capacity and item condition against the state read back inside the transaction."""
    for tab, statuses in (
        ("labs", {"booked", "cancel_pending"}), ("library", ACTIVE_SEATS), ("equipment", ACTIVE_STOCK),
    ):
        allocations = {}
        for request in requests(data, tab):
            if request["status"] not in statuses:
                continue
            require(request["start"] < request["end"], "Readback failed. Allocation window is invalid.")
            for asset in active_assets(request):
                slots = allocations.setdefault(asset, [])
                require(not any(overlaps(slot, request) for slot in slots),
                        "Readback failed. Two allocations overlap.")
                slots.append(request)
                if tab == "library":
                    seat = next((seat for seat in SEATS if seat["id"] == asset), None)
                    require(seat and seat["zone"] == request["target"] and seat["protected"] == request["protected"],
                            "Readback failed. Seat is outside the requested eligibility.")
                if tab == "equipment":
                    item = data["items"].get(asset)
                    require(item and item["type"] == request["target"] and not item["borrowed"],
                            "Readback failed. Item assignment and stock ledger disagree.")
                    require(item["condition"] == "ready", "Readback failed. An allocation contains a damaged item.")


def snapshot(run_id, data, model_available):
    day, time = clock_parts(data["clock"])
    return {
        "run_id": run_id, "clock": data["clock"], "day": day, "time": time,
        "revision": data["revision"], "model_available": model_available,
        "labs": LABS, "lab_blocks": LAB_BLOCKS, "lab_sessions": LAB_SESSIONS,
        "seats": SEATS, "seat_blocks": SEAT_BLOCKS,
        "items": sorted(data["items"].values(), key=lambda item: (item["type"], item["id"])),
        "equipment_types": EQUIPMENT_TYPES, "requests": list(reversed(data["requests"].values())),
        "audit": data["audit"][-180:],
    }
