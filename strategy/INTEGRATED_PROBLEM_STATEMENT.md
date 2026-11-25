# AccessRelay · Academic Continuity

**Management Track 4 · Open Innovation.** Recommended for team acceptance and organizer approval.

## Organizer-ready problem statement

### Preserving Accessible Practical Assessments During Campus Disruptions

When a teaching lab or its accessible route becomes unavailable shortly before a practical assessment, the scheduled session is at risk. Restoring it requires a reachable room with enough capacity, compatible equipment and supervision, while preserving approved assessment conditions. Facilities staff, lab custodians, assessment coordinators and instructors hold different parts of that information. If a resource changes while a move is being arranged, one cohort may be left without a valid plan. The campus needs a way to identify affected groups, verify alternate rooms and equipment, secure staff approval for loans or schedule changes, and confirm that instructors receive the revised plan. Unresolved constraints should be escalated with their evidence, while student identities and accommodation details stay private.

**Proposed solution.** AccessRelay interprets disruption reports, chooses what to verify and proposes a recovery plan. It checks each cohort against room access, capacity, equipment and assessment requirements. After staff approval it commits the plan to a synthetic schedule, verifies equipment readiness and tracks instructor acknowledgment. It records why each candidate was accepted, rejected or escalated.

**Target users.** The assessment coordinator owns the case. Facilities confirms access, the lab custodian verifies equipment or approves a loan, and the instructor acknowledges the new arrangement. Students are the beneficiaries. Set conditions at the whole-cohort or anonymous requirement level and retain the approved conditions during replanning.

**Evidence.** Columbia describes classroom relocations after facilities issues and the registrar-to-instructor handoff. Bath directs facilities staff to identify alternate instruments after breakdowns and documents instrument training requirements. Auckland describes arranging approved assessment conditions, rooms and invigilators. These sources establish the separate workflows. Their intersection is the opportunity we are proposing. BMSITM’s incident frequency and local process remain unverified. [Columbia Registrar](https://registrar.columbia.edu/content/protocol-classroom-relocations) · [University of Bath](https://www.bath.ac.uk/legal-information/research-facilities-user-agreement-for-staff-and-students/) · [University of Auckland](https://www.auckland.ac.nz/en/about-us/about-the-university/policy-hub/education-student-experience/assessment/special-conditions-in-test-and-examinations-procedures.html)

## Five mechanisms in one recovery workflow

| Source concept | Mechanism applied to a practical assessment |
| --- | --- |
| AccessRelay | Verify a usable step-free route to the proposed replacement. Read back the booking and require staff acknowledgment. |
| BenchShift | Check equipment capability and technician readiness before recommending a substitute. Use explicit, custodian-verified compatibility. |
| ExamRelay | Carry forward approved time, capacity, setup and invigilation conditions through a move. Preserve anonymous requirements. |
| DormPivot | Track coverage by affected cohort. If a valid plan covers one cohort only, keep the other visible with an owner and an escalation reason. |
| ReUse Dispatch | Find an eligible spare across departments and verify its condition, loan approval and receiving handoff. Treat a proposed loan as pending until confirmed. |

Each mechanism answers one question in the same incident record. The visible output is an assessment marked **ready**, with a verified booking, required equipment and staff acknowledgment, or **unresolved**, with the missing requirement and owner.

## One incident and one working flow

**Hook.** “The lift goes out twenty minutes before a practical exam. The ground-floor lab is free. It only has half the working kits. Can every cohort still sit the exam under the same conditions?”

| Demo time | Show |
| --- | --- |
| 0–20s · Sense | Enter an ambiguous synthetic facilities note. Optional simulator supplies an out-of-service event. The model requests a scope lookup and identifies the affected assessment and cohorts. |
| 20–40s · Think | The nearby room fails the step-free route check. The ground-floor lab passes on access and has sufficient room capacity, but needs one compatible spare kit. Show the evidence for the shortfall and the proposed loan. |
| 40–65s · Adapt and act | The first spare kit becomes unavailable before approval. The system refuses the stale proposal. The agent checks the remaining candidate and requests confirmation of its condition. A lab custodian confirms the loan and the coordinator approves the revised booking. |
| 65–90s · Explain and verify | Apply the booking and loan reservation together to the mock ledger. Record separate mock equipment receipt and instructor acknowledgment. The cohort coverage view becomes ready only when both confirmations exist. Show the rejected option, revised decision and audit trail. |

Use one incident, one assessment, two synthetic cohorts, two alternate rooms, and two possible spare kits. The two cohorts can share the recovered session if its verified capacity allows. The coverage check still evaluates each cohort. If no compatible confirmed kit remains, preserve current records and escalate the blocked cohort to the assessment coordinator.

### Architecture and safeguards

- **Model judgment.** Interpret the free-text report, decide whether scope or equipment evidence is missing, request allowlisted lookups and propose the next action with evidence IDs. Demonstrate two notes that lead to different next checks.
- **Deterministic validation.** Use a small local data store and explicit checks for route status, capacity, booking overlap, equipment compatibility, technician availability and approved assessment conditions. Unknown critical facts fail validation. Apply the same conditions to both cohorts. Use a fixed, visible priority if both cannot be recovered.
- **Approval and verification.** Keep changes in proposed state until authorized staff approve the current version. Recheck availability and permissions at commit. After writing, read back both reservations and track receipt and instructor acknowledgment. Log the input, evidence IDs, timing, approval and outcome. Use stable synthetic IDs and no student records.
- **Stability.** Set a bounded model timeout and test one model outage and one stale proposal. Keep manual incident entry with the same validation and approval guards as a fallback. Declare actual libraries, models and hardware in the final submission. Keep all operations local or on approved synthetic-data services with no connections to real campus systems or financial accounts.

### Optional hardware cue

Use a standalone switch or simulated status panel to publish a timestamped **lift unavailable** event into the same synthetic input as the browser’s incident button. It supplies one observation. The agent still needs the report and campus fixture to establish impact. Use the browser button whenever hardware would slow or weaken live reliability. Keep the setup disconnected from real campus equipment.

## What earns rubric marks

| Criterion | Planned evidence |
| --- | --- |
| **PoC · 5** | Show the live sequence ending in a real change to the mock schedule and equipment ledger. Show an uncovered cohort stay unresolved when the missing requirement cannot be verified. The prior score for the narrower AccessRelay concept was conditional and does not transfer automatically to this scope. |
| **Technical Research · 5** | Diagram model tool requests, policy checks, human approval, transaction and verification. Explain how the system handles stale state, uncertain inputs and API failure. Record timings for the working flow and any dependency limits once tested. |
| **Market & Industry · 5** | Identify the assessment coordinator as the operator. Compare the existing combination of room scheduling, instrument reservations and assessment administration with this cross-office recovery flow. Include the campus sources above and the verified competitor capabilities. Local workload and market size are open questions. [Competitor research](COMPETITIVE_ANALYSIS.md) |
| **Feasibility & Execution · 5** | Prioritize an incident, an alternate room, one loan and an approved write and readback. Add the unavailable-kit replan and acknowledgment next. Use a single local fixture and one model. Add optional hardware only after the workflow passes repeat runs. Confirm the coding window with organizers. |

**Proposed evaluation.** Replay the same synthetic scenarios against a coordinator using a schedule and equipment list. Compare time to an acknowledged plan, cohorts with all hard requirements preserved, and invalid or stale changes blocked. Include compatible loan, stale kit, inaccessible room and no feasible option. Report sample size, timings and results only after running the tests.

**Seven-slide mapping.** 1 team and formal problem. 2 one disruption and the three documented handoffs. 3 what an assessment needs to be ready and where the agent chooses a next step. 4 model, checks, approval and verified state change. 5 90-second scenario, demo and roadmap. 6 minimum working flow, test cases, freeze point and optional simulator. 7 team and declared tools. [Template requirements](../presentation/SLIDE_PLAN.md)

**Approval step.** Submit the statement above for organizer approval. Confirm whether a working PoC is required at Checkpoint Alpha and when it may be built. The first engineering priority, once approved, is a repeatable laptop-only flow.
