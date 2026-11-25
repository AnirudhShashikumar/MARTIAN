# CampusFlow · Campus Capacity and Resource Management

**MARTIAN 1.0 · Management Track 4 · Open Innovation · Agentic AI for Campus Wellness**

## Organizer-ready problem statement

### Coordinating Campus Parking and Shared Resources During Demand Changes

When classes, lab sessions and campus activities start, end or move, demand for parking and shared resources can change within minutes. Parking attendants need to know which car and two-wheeler spaces are occupied, when vehicles enter or leave, and when a designated overflow area should open. Academic and facilities staff need current availability for classrooms, labs, library seats and shared sports equipment. A vacated classroom can also leave lights, fans and projectors running. The campus needs a way to interpret schedule changes and current occupancy together, allocate available spaces and resources under clear policies, and verify that each action took effect. When occupancy is uncertain, capacity runs out, or a sensitive action is needed, the system should escalate the case to an authorized staff member and record the decision.

**People affected.** Students and staff who need parking, study space or equipment. Parking attendants manage allocations, resource custodians manage availability, and facilities staff approve room power actions.

**Proposed solution.** CampusFlow is an operations agent that reacts to changes in campus demand. It reads a calendar change or staff note, checks gate events and availability, and proposes a coordinated plan. Separate car and two-wheeler capacity is tracked using sample entry and exit timestamps. The agent can assign eligible spaces, release them on exit and request time-limited allocation from designated overflow areas. It checks lab bookings, library seating and sports-equipment loans against sample inventories and policies. For an unoccupied classroom, it uses a feed of synthetic room frames to establish sustained vacancy, checks the schedule and supervisor override, then proposes an approved simulated switch-off for lights and fans and standby for the projector.

## Sense → Think → Act → Explain

| Capability | CampusFlow behavior |
| --- | --- |
| **Sense** | Read a synthetic schedule change, timestamped vehicle entry and exit events, space and inventory availability, and timestamped classroom occupancy counts derived from synthetic frames. |
| **Think** | Use one AI model to interpret a free-text change, identify affected locations and time windows, choose which data to check and propose a plan. A full car lot and a vacant classroom may call for different actions after the same schedule change. Replan when an expected space becomes unavailable or an occupancy signal goes stale. |
| **Act** | Apply normal car or bike allocations under fixed rules, release spots when sample exits arrive, stage resource reservations where policy permits, and request human approval before opening temporary overflow or changing simulated room devices. Server-side rules protect capacity, eligibility, reservations, expiry and manual overrides. |
| **Explain and verify** | Explain each decision with the evidence used, show why another option was ruled out and read back the sample parking, reservation and device states. If the room becomes occupied, feed confidence drops or a protected booking conflicts, hold the power action and alert facilities staff. |

The model handles ambiguity and chooses the next verification step. Application rules enforce hard constraints and prevent over-allocation. Use existing policy for accessible and reserved spaces and first-come ordering among equally eligible requests. Log timestamps, synthetic IDs, decision reasons, approvals and outcomes. Convert frames to occupancy counts and confidence, then discard them. Identity recognition, real vehicle plates and real student records are outside the prototype scope.

## Round 1 demo and scope

**Opening hook.** “A class moves to a lab. The car lot is full, bike spots are still available, and the classroom it left behind is still powered. Can one campus operator recover all three in time?”

1. **Sense the change.** Enter a synthetic note stating that an afternoon class moved from C-101 to Lab 2 and that a visiting group is arriving. The agent checks the lab booking and gate state, then shows where demand has changed.
2. **Allocate and verify parking.** A car arrival finds the normal car lot full. The model recommends a designated temporary overflow bay with a time limit. After the attendant approves, a synthetic car is assigned the bay. A bike uses a regular bike spot. An exit event releases a spot and updates the displayed capacity.
3. **Release the empty room’s resources.** As the synthetic feed shows C-101 vacant across the demo’s configured observation window, the agent checks the room calendar and a manual hold. It requests facilities approval and then changes the mock light, fan and projector states. Show the audit log and a separate replay where stale or uncertain video keeps the devices on.
4. **Show the remaining resource types.** Use the same availability and reservation interface for a free lab slot, available library seats and a sports kit in stock. One sample reservation or checkout is enough to demonstrate that availability changes when the transaction succeeds.

Keep the first working slice to one schedule change, one gate, one normal lot per vehicle type, one approved overflow area and one simulated classroom. Include small sample records for labs, library seats and sports inventory. A prerecorded synthetic feed processed during the live demo can represent room occupancy. An optional standalone tabletop simulator can show device states with LEDs. Every state change stays in the mock system.

## Round 1 rubric and track alignment

| Criterion | What to show |
| --- | --- |
| **Proof of Concept** | Working sample events update parking and room/device state. Show one safe no-action path for stale or uncertain occupancy. |
| **Technical Research** | Explain structured model output, allowed tools, separate car and bike capacity, duplicate entry/exit handling, reservation conflicts, freshness checks, human approval and audit records. Measure actual latency and test fallback behavior before presenting results. |
| **Market & Industry** | Compare T2’s parking entry and exit capabilities, CollegeNET 25Live’s room scheduling and conventional occupancy controls. Explain that CampusFlow’s proposed advantage is coordinating responses to the same demand change across these functions. Campus-specific prevalence and market size still need validation. [T2 Systems](https://www.t2systems.com/parcs-parking-access/) · [Mississippi State on 25Live](https://www.registrar.msstate.edu/faculty-staff/resources/25live-room-scheduling-software) · [U.S. Department of Energy](https://betterbuildingssolutioncenter.energy.gov/resources/wireless-occupancy-sensors-lighting-controls) |
| **Feasibility & Execution** | Build fixture and typed events first, then rules and transaction state, then the model decision and approval UI. Rehearse event playback and device readback. Treat hardware as a final enhancement after the browser demo is reliable. |

Universities already publish parking availability and provide equipment checkout. Those examples support the workflow categories and do not establish a specific local problem or measured savings. [Penn State parking availability](https://www.psu.edu/news/university-park/story/transportation-services-announces-real-time-parking-deck-capacity-website) · [UC Davis equipment checkout](https://campusrecreation.ucdavis.edu/equipment-room)

**Proposed measures.** Valid parking assignments, overflow approvals and expiry, time to resolve a capacity exception, device-on minutes in verified-vacant rooms, and incorrect shutdowns. Compare against separate availability screens and manual coordination using the same synthetic scenario. Claim measured results only after testing.

**Seven-slide mapping.** 1 team and formal statement. 2 demand shift, affected operators and consequences. 3 how the model chooses evidence and proposes actions. 4 architecture from sample events to constraints, approvals and verified state. 5 walkthrough and roadmap. 6 scope, execution sequence, tests and optional hardware. 7 team and tools actually used.

**Organizer requirements.** This is campus operations rather than sports-event, canteen or club management. Use original work, team-created data, synthetic video, human escalation, fair allocation, audit records and tool disclosures. Keep the prototype free of real campus-system connections, real payments and personal data. Request organizer approval for this problem and confirmation of the Round 1 build window. [Official Management rules](../context/RULES_AND_CONSTRAINTS.md#problem-statement-domain-rules) · [Official rubric](../context/JUDGING_CRITERIA.md) · [Seven-slide reference](../presentation/SLIDE_PLAN.md)
