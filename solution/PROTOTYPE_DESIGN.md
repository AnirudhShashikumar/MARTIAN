# CampusFlow · Checkpoint Alpha design

**Scope approved for implementation** based on team confirmation on November 25, 2026. The Open Innovation statement is “Coordinating Campus Parking and Shared Resources During Demand Changes.” The team confirmed organizer permission to start coding before Alpha. [Decision log](../strategy/DECISIONS.md)

The defining interaction is a late lab move that causes two independently approved changes. An occupied classroom invalidates its standby proposal while a verified overflow assignment remains in effect. The presenter follows one incident across the existing Vehicle Fleet Management and College Resource Allocation tabs.

## Presentation prototype

Run a local browser against FastAPI and SQLite. Vanilla HTML, CSS and JavaScript keep the UI offline-capable and avoid a frontend build. SQLite stores one resettable synthetic scenario, branch versions and the chronological audit. One optional model selects a read tool to disambiguate the fixed scenario note. The server validates the tool and session ID before reading the fixture. The local fallback uses the operator-confirmed structured schedule. Both modes share the same policy, approval, record mutation and readback code.

Use a 16:9 operations workspace with large status labels, a navy incident header, neutral work surfaces, orange approval controls, green verification and a clearly labeled red safety hold. Keep the incident ID and both branch statuses visible across tabs. A persistent operator panel shows the next action and the latest evidence. Tab-specific state makes the action visible without reading the audit.

**Roles and boundaries.** The demo presenter plays the timetabling coordinator, parking attendant and facilities supervisor. The server checks the simulated role and proposal token, then reloads current evidence in the same transaction as the mock write. The model selects only an allowlisted read/clarification tool. Synthetic vehicle IDs, counts, capture times, booking revisions and audit reasons are the application data. College integrations, physical devices, payments and personal records are outside the demo boundary.

**P0.** One incident, one gate, normal and overflow parking, one classroom, one lab, room replan, separate approvals, readback, reset and audit. The room uses explicitly labeled synthetic count events. Lab and library views expose sample availability. One sports-kit transaction illustrates inventory checkout and return. The build prioritizes the two permissioned writes and their readbacks.

## Proposed final product

Replace fixtures with separately authorized adapters for timetable, gate, room occupancy and abstract device commands. Normalize events before sending them to the same coordinator and policy checks. Bind approvals to authenticated campus roles with resource and building scope. Use a relational store with scoped state revisions, durable proposal expiry and an outbox for device or allocation requests. Reconcile acknowledgments and surface mismatches to operators. If vacancy or device readback is missing, escalate to facilities. Capture only occupancy aggregates at the edge, set retention limits and scope access to operational data. Use verified historical incident samples to test fairness and estimate actual impact before considering rollout.

This path preserves the prototype's typed tools, branch independence and audit contract while adding durable identity, event ingestion and operational verification.

## Technical decision rules

- The schedule record establishes the revised session window. An ambiguous or conflicting record requires a coordinator.
- Cars and bikes use separate eligibility pools. Accessible and reserved bays stay protected. Choose the first eligible arrival when only one allowed bay is available.
- Overflow is limited to a published synthetic window. An expired window closes new assignments and leaves an occupied bay assigned until a confirmed exit.
- Room standby requires an empty, refreshed feed, continuous vacancy for the labeled demo threshold, a free timetable interval, a clear manual override and current facilities approval. Fresh occupancy revokes an open proposal. A new vacancy interval needs a new decision.
- Verification reads the resulting synthetic bay assignment or device state from the transaction. A missing confirmation fails the transaction and surfaces an error. Audit records contain concise observable reasons and evidence, approvals and outcomes.

[Six technical diagrams](CAMPUSFLOW_DIAGRAMS.md) · [Storyboard](../presentation/DEMO_STORYBOARD.md)
