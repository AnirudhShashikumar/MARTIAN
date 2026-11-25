# College Resource Allocation build plan

Build three complete workflows in the existing local `/resources` dashboard. Each tab should take a synthetic staff or student request through availability, a policy decision, confirmation or staff approval, and a verified SQLite update. Keep the existing Gate A and C-101 incident as the main demonstration. It becomes the first Labs example, and Library seats and Sports equipment can each run from a fresh demo without triggering that incident.

## What exists today

| Tab | Current app | Final local build |
| --- | --- | --- |
| Labs | Shows one timetable fixture after the schedule-change incident. | A small timetable with selectable lab slots, a booking request, conflict-aware alternatives, staff approval, cancellation and a verified calendar. |
| Library seats | Shows fixed quiet-zone counts. | A seat map and time picker, short holds, check-in, release, expiry and a waitlist when eligible seats run out. |
| Sports equipment | Checks one sample kit out and back in. | An item catalog and inventory ledger with reservations, checkout, due times, returns, condition checks and a queue for unavailable equipment. |

Reuse the existing [transactional SQLite store](../prototype/app.py), [dashboard sections](../prototype/static/app.js), and [Gemini adapter](../prototype/agent.py). The development target is [the local resources dashboard](http://127.0.0.1:8766/resources). Staff roles, capacity, schedules and eligibility use team-created sample records.

## One workflow across all three tabs

1. **Observe.** Record a structured request or a short synthetic note. Attach a request ID, requested window, current resource revision and input mode. Show the matching authoritative source with its timestamp, such as the local timetable, seat ledger or item ledger.
2. **Understand.** Use the structured fields directly. For a synthetic note, let the optional model choose one typed lookup or ask for clarification. If a time, quantity, group size or resource is ambiguous, keep the request editable and ask for that field.
3. **Plan.** The server searches eligible inventory and stages the best option plus up to two eligible alternatives. Show what was checked, why the preferred option was blocked, and the exact effect of approving a proposal. If nothing fits, offer a waitlist where supported.
4. **Act.** An explicit requester confirmation or designated simulated staff review submits a versioned proposal. In the SQLite write transaction, check the role, run, proposal expiry, affected records and current policy before applying the command.
5. **Verify.** Read the changed booking, seat assignment or item ledger rows back from SQLite and check the expected state. Commit the effect and its audit together. On a mismatch, roll back the effect and record the failure separately if the store is available.
6. **Adapt.** A conflict, arrival, expiry or return triggers a fresh policy decision. An expired or superseded proposal needs a fresh review. When capacity opens, offer the first eligible waitlisted request a new time-limited hold. Record who was offered capacity and why.

## Tab workflows

| Tab | Operator journey and rules | Acceptance example |
| --- | --- | --- |
| **Labs** | Show a timetable for Lab 2 and two synthetic alternatives with capacity and equipment. Accept a session, date, start/end time, group size and equipment requirement. Match by capacity and equipment, block overlapping bookings and maintenance, and rank by requested window, then earliest matching slot and stable lab ID. Require **Lab coordinator** approval for booking, rescheduling and cancellation. Reschedule atomically by validating and replacing the old booking in one transaction. | Lab 2 is unavailable for a 24-person slot. The agent shows a lab with enough capacity and the required equipment, with the original conflict explained. Approve it, refresh, then cancel it. An overlapping approval from a second browser tab produces a conflict and leaves one booking. The existing Lab 2 incident and C-101 approval run still work. |
| **Library seats** | Show seat status by zone and requested window. Accept an explicit hold, check in and release the same reservation. A configurable demo hold defaults to 10 minutes. Protected seats require a synthetic eligibility flag and stay out of general allocation. Use first eligible request order for the same zone/window, with a stable submission sequence for ties. Claiming an offered seat requires confirmation. Route protected-seat exceptions to **Library staff**. | Reserve the last general seat, then add a second synthetic request to the waitlist. Advance the demo clock past the hold. The next eligible request receives an offer, and after check-in and release the seat is free. The two users never hold the same seat at the same time and protected capacity stays eligible for the intended users. |
| **Sports equipment** | Show several equipment types and individual item IDs with reservations and due times. Accept item type, quantity and pickup/return window. Respect existing reservations, checked-out stock and stock under inspection. Offer verified alternatives or a waitlist. **Sports desk staff** confirm checkout and return. Support partial returns and a condition flag. Damaged items go to inspection until cleared by staff. Overdue items stay checked out. | Reserve two rackets, check both out, then return one in good condition and one damaged. The ledger shows one free and one under inspection after refresh. A second request cannot take a checked-out, reserved or damaged item. Retrying a return does not increase available stock. |

The first cut can use one representative demand case per tab. Seed overlapping timetable slots, a nearly full library, and a sports catalog with unavailable and checked-out items so the agent has decisions to make.

## Implementation order and interfaces

| Work | Changes and exit check | Estimate |
| --- | --- | --- |
| **1. Shared state and commands** | Add a `resources` module for fixtures, typed commands and pure policy checks. Extend the local store with additive initialization of resource state under the current demo run. Reuse the SQLite transaction and audit path. Preserve the active timetable session and kit state when initializing a prior local database. Expose `GET /api/resources` and `POST /api/resources/command` locally. Typed commands include run ID, action, request ID and an idempotency key for mutations. Review also includes proposal ID and the simulated reviewer. Verify that a previous demo DB opens and can be reset. | 50 min |
| **2. Labs end to end** | Implement availability, request, review, cancellation and timetable UI. Treat the existing Lab 2 timetable window as a protected booking so the legacy incident and the new actions agree. Verify request → alternative → approve → reload → cancel in the browser. | 75 min |
| **3. Library seats end to end** | Build the seat map, eligibility, hold transitions, check-in and ordered waitlist. Use an injectable demo clock to drive expiry and make tests repeatable. Reconcile expiry and queue offers atomically before allocation. Show a visible countdown and offer status. | 70 min |
| **4. Sports end to end** | Migrate the sample kit into a small item ledger and add stock filtering, reserves, pickup, due and return actions. Verify availability counts derive from persisted item state after a partial or damaged return. | 65 min |
| **5. Optional Gemini adapter** | Extend the existing server adapter for variable synthetic notes. Add typed lookups, response validation and a labeled fallback. Keep all three workflows usable with `GEMINI_API_KEY` absent. Smoke-test with a team-approved key only after structured mode passes. | 45 min |
| **6. Integration and release checks** | Run the existing suite and new API scenarios, rehearse the three tabs from a clean launch and re-run the Gate A/C-101 journey. Verify desktop and narrow layout, export a short evidence table, and freeze. | 75 min |

**Estimated implementation and verification** is 6 h 20 min. The 10:40 PM IST planning snapshot leaves 7 h 5 min before the planned 6:00 AM freeze after the scheduled snack break, with 45 minutes of buffer. An earlier submission cutoff takes precedence. Start with Labs so the core competition journey and first functional tab can be proven together. Run the live Gemini smoke test after the structured journeys pass. If the organizer moves the cutoff forward, defer live provider verification, cosmetic polish and additional fixture types first. [Beta execution plan](ROUND_2_EXECUTION_PLAN.md)

### State and UI details

- Persist the catalog, availability markers, requests, proposals, allocations and queue position in the demo run. Keep one active allocation per item or seat per applicable window. Model reservations as half-open time windows so an adjacent booking is valid. Display times in IST. Use a disposable persistent `CAMPUSFLOW_DB` path for rehearsal and verify state survives a server restart. Reset restores all sample resource fixtures and invalidates old proposal IDs.
- Guard competing writes with the existing `BEGIN IMMEDIATE` lock and recalculate availability inside it. Scope proposal versions to their relevant resource or evidence records. Reject stale, expired and wrong-role reviews with an actionable conflict message. A retry with the same idempotency key and payload returns the original action receipt, with current availability refreshed separately. A reused key with a different payload returns a conflict.
- For each tab, put date/time and current availability next to the request controls. Display request status, proposed choice, latest evidence and action in the same panel. Keep the existing navigation and add direct links to each tab using the `section` query parameter. Show loading, empty, full, conflict and problem states. Reuse the decision audit with resource filters and a verified receipt ID for each effect.
- Audit request ID, source/version, chosen policy rule, alternative or hold reason, simulated role, and verification outcome. Treat free-text input as untrusted, escape it in the browser and keep credentials out of prompts, UI and logs. Use synthetic identifiers and avoid storing raw provider responses.

## When the LLM is used

- **Structured request.** Use the existing deterministic path for a filled form, known resource ID, approval, checkout, return or cancellation. The server computes capacity, fairness, inventory and every final change.
- **Synthetic natural-language note.** An operator chooses **Interpret note**. Reuse server-side `GEMINI_API_KEY` and `CAMPUSFLOW_GEMINI_MODEL`. Send a bounded note plus synthetic catalog identifiers, with `store: false`. Allow exactly one of `lookup_lab_schedule`, `lookup_seat_availability`, `lookup_equipment_stock`, or `request_clarification`. Offer just the relevant lookup and clarification on each tab. The server validates all arguments and corroborates them against the exact input and the source. Use a model ID confirmed on the presenting machine. [Gemini function calling](https://aistudio.google.com/docs/function-calling) · [Interactions storage settings](https://aistudio.google.com/docs/interactions-overview#data-storage-retention) · [Gemini API keys](https://aistudio.google.com/docs/api-key)
- **Provider failure or ambiguous result.** Set a five-second deadline for the operator to see structured fallback. Keep the model request outside the SQLite transaction, deduplicate a pending call by run/request revision, and discard late results after a reset or edit. A missing key, timeout, rate limit or malformed response preserves the draft and offers the form or a focused clarifying question. Display **Gemini**, **Structured**, or **Needs clarification** in the trace according to the path that ran.

## Release gates

| Check | Required evidence |
| --- | --- |
| Functional | Finish each tab’s acceptance example with model access disabled. Verify counts after reload, one persisted example after restart, and reset across all three. |
| Correctness | Cover competing approvals, stale and expired offers, duplicate submissions, wrong simulated reviewer, protected seats, overlapping bookings, partial returns, damaged or overdue equipment and readback rollback. Zero unauthorized or duplicate allocations in the test cases. |
| Agent | With a stub provider, test a grounded note and a clarification per tab, one invalid tool call and a timeout. If a team-approved key is available, run one valid synthetic note per tab and one ambiguous note on the demo laptop. Record correct sources, correct holds, request latency and input mode. Label live Gemini as verified only after that run. |
| Regression | Run `python -m unittest discover -s prototype -t .` and `node --check prototype/static/app.js`. Rehearse the original incident through both independent approvals, the occupied-room hold, recovery and audit. |

For the final presentation, lead with the Lab 2 schedule change and the linked parking and classroom outcomes. Keep two short follow-up runs ready, a library hold expiring into the next eligible request and a damaged sports return going to inspection. Show the verified state and the decision audit in each run.
