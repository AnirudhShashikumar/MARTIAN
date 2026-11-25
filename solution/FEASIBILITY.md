# CampusFlow feasibility and build sequence

**Minimum working scope.** One synthetic lab move and delay, gate arrival and exit events, deterministic class-based parking, one approved overflow assignment, one occupied-frame recheck, and one independently approved simulated room change. Use a local browser, Python API, SQLite and one validated model credential. Use fixtures for timetable, capacity, eligibility, occupied or vacant sequence, versions and device states. Facility, model and parking controls operate only against simulated state.

| Stage | Planned window · IST | Deliverable |
| --- | --- | --- |
| Scope and event contracts | 4:00–5:30 PM | Define fixture, tool schema, policy, approval state and success criteria. Confirm model access and quota. |
| Working vertical slice | 5:30–8:30 PM | Implement one real model-driven tool choice, validated parking and room actions, approvals and readback in the browser. |
| Integration and recovery | 8:30 PM–12:30 AM | Handle stale evidence, idempotency, manual override, escalation, model timeout and new occupancy. |
| Synthetic tests and demo | 12:30–6:15 AM | Replay the same cases, capture run results, rehearse timing and make any allowed fallback. Add simple catalog only after repeated demo success. |
| Freeze and judging buffer | 6:15–8:30 AM | Rehearse from fresh local state, verify readiness and preserve breaks and submission buffer. |

This is a 16.5-hour elapsed window from the published event flow. Account for organizer updates, breaks, team availability and actual cutoffs. The milestones are estimates, contingent on shortlisting and permission. An authorized early PoC should prioritize one genuinely model-driven path and repeatable local readback before adding the second branch. [Event schedule](../context/HACKATHON_CONTEXT.md)

**Test minimum.** Start with a normal overflow approval and fresh room vacancy. Test the occupied-frame race, duplicate exit, no available overflow, and model timeout. Compare against a structured rules baseline using the same fixture. Confirm that safe holds never change mock device state. Log time to verified resolution and correct/blocked actions. Report only observed timings or results.

**Enhancements.** Generic lab, library-seat and sports-equipment availability records, more fixture notes, and a standalone LED state indicator after the MVP is stable. Campus integrations, camera deployments and any physical equipment control require a future privacy and operating review.

**Fallback.** Use local data and a staff-entered structured change with the same validation and approval when a model call fails. If using a recorded walkthrough, label it and confirm presentation permission. Any unimplemented component remains marked planned. Assign real team names to the main lanes before inserting slide 7. Declare actual tools and versions, keep credentials private and confirm attribution.
