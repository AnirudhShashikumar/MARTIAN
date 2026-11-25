# CampusFlow final round execution plan

**MARTIAN 1.0 · Checkpoint Beta · Top 10 confirmed by the team**

## What to build

Finish one incident from a new schedule notice to two verifiable operational outcomes. CampusFlow should identify the correct timetable record or ask for clarification, then stage the eligible actions. Parking and facilities retain their own approval authority. A new occupied reading withdraws the room proposal while the verified parking assignment remains visible in the shared incident.

The final-round improvement is **evidence choice on unfamiliar wording**. The Round 1 prototype already proved the mock writes, independent approvals, occupancy hold, recovery, and audit. Its verified intake used a fixed note and a structured lookup. The finale should show why a model improves intake when more than one timetable record could match. [Round 1 verification](../evaluation/PROTOTYPE_VERIFICATION.md)

| Priority | Build choice | Why it earns the time |
| --- | --- | --- |
| **P0** | Variable note intake, typed timetable tools, two verified outcomes, independent recovery and a readable audit. | Makes the AI contribution visible and builds on a tested workflow. |
| **P1** | One separate mock acknowledgment failure after approval, with a visible escalation. | Shows what the system does when a downstream write lacks confirmation. Add it after all P0 gates pass. |
| **Final local build** | Working Labs, Library seats and Sports equipment workflows under College Resource Allocation. | Start with Labs to reinforce the main incident. Use Library and Sports as independent demos of the same approval and verification flow. [Resource allocation build plan](RESOURCE_ALLOCATION_BUILD_PLAN.md) |
| **Defer** | Additional resource categories, new devices, campus-system connections and infrastructure rewrites. | Keep the final build focused on the synthetic demo and its verified workflows. |

## Time and ownership

The latest schedule in the workspace has Beta judging at **8:30 AM IST on November 26**. The official team slot, submission cutoff, demo length, required files and final rubric are pending. Use the organizer's latest instructions as soon as they arrive. The Round 1 rubric is an internal planning reference for coverage, pending the Beta rubric. [Event flow](../context/HACKATHON_CONTEXT.md) · [Round 1 rubric](../context/JUDGING_CRITERIA.md)

**Planning snapshot at 6:25 PM IST on November 25.** There are **14 hours 5 minutes** to scheduled judging. Budget **30 minutes for dinner at 8:30 PM**, **15 minutes for the 1:30 AM snack break**, and **30 minutes for breakfast at 7:00 AM**. That leaves about **12 hours 50 minutes of shared work and rehearsal time** before Beta, subject to the actual cutoff. Freeze the candidate at **6:00 AM or 90 minutes before the actual submission deadline, whichever comes first**. If the deadline moves forward, drop P1 and bring packaging forward.

Assign a named owner to each lane. Team members can cover more than one lane.

| Lane | Owns | Handoff |
| --- | --- | --- |
| Integration lead | Shared base, release candidate, organizer deadlines, scope calls | One runnable build and one manifest of what shipped |
| Agent and fixtures | Authoritative timetable fixtures, note interpretation, validated tools, offline fallback | Contract tests and a live tool-selection trace or a documented fallback |
| Workflow and UI | Versioned proposals, policy checks, readback, incident screen and controls | Browser demo with one visually obvious safety hold and recovery |
| Verification and presentation | Case matrix, baseline, outcome counts, screenshots, pitch and package | Evidence sheet, judge answers and a clean-launch rehearsal |

The working branch is ahead of and behind its remote at planning time. The integration lead should verify the shared base and preserve uncommitted local evidence before combining work. Assign visible contributions by name in the submission.

| IST window | Team outcome | Exit check |
| --- | --- | --- |
| **Now–6:50 PM** | Confirm organizer logistics in parallel. Preserve the working Alpha build, assign owners and agree on two timetable records and the API contract. | Everyone can run the Alpha demo and state the supported outcomes. |
| **6:50–8:30 PM** | Implement variable synthetic notes, validated session lookup or clarification, and a provider smoke test with a team-authorized credential if available. Start the incident trace UI in parallel. | One new note maps to the right record and one ambiguous note holds. At 8:30 PM, decide whether model access is viable. |
| **8:30–9:00 PM** | Dinner. Record handoff and open defects before the break. | Team resumes from the same ownership list. |
| **9:00–11:45 PM** | Integrate the agent path with both policy branches. Preserve the verified offline path. Implement the exact scenario controls and independent approval refresh. | Complete the main journey from a reset in the browser. An occupied reading invalidates only the room approval. |
| **11:45 PM–1:30 AM** | Run existing and new regression cases, including provider failure, duplicate events, stale approvals and failed readback. Prepare the evaluation matrix and compare modes. | Every safety invariant passes. End-to-end verified runs use the same releasable build. |
| **1:30–1:45 AM** | Scheduled snack break. | Log run counts and resume at the highest-priority failing case. |
| **1:45–4:30 AM** | Complete evaluation and recovery. Use rotating rest while one owner stays available for merges. Add P1 only after the main browser run and tests pass. | Outcomes and timing have raw run records. Repeated browser resets work. |
| **4:30–6:00 AM** | Rehearse, capture the final build, prepare source disclosure, assemble submission files and freeze. | Fresh local launch passes. Each claim has evidence or is marked planned. |
| **6:00–8:30 AM** | Verify the package on the presenting laptop, eat breakfast around 7:00 AM, submit by the actual cutoff, and rehearse slot-specific handoffs. | Confirm submission receipt and keep the build and authorized fallback ready. |

## P0 technical contract

Keep one agent, one existing backend and one shared incident. Use the current FastAPI, Pydantic and SQLite boundaries. The two existing browser tabs show separate resource states and the same incident evidence. [Prototype design](../solution/PROTOTYPE_DESIGN.md) · [Architecture diagrams](../solution/CAMPUSFLOW_DIAGRAMS.md)

1. **Sense.** Accept a small set of team-created synthetic note variants and typed gate or occupancy events. Give each input an event ID and keep timestamps, source references and the current branch evidence version.
2. **Think.** Give the model a constrained choice between reading an allowed timetable record and asking the coordinator for clarification. Use two plausible timetable records so the lookup has a meaningful choice. Validate the tool name and arguments before reading. The authoritative timetable establishes the window and whether the former room was released. Corroborate the match against concrete note details, or require coordinator confirmation when multiple records remain plausible or the sources conflict.
3. **Plan.** Let the server derive the actions from the timetable, parking capacity and room evidence. A change with the same room creates no standby proposal. Protect accessible and reserved bays, keep separate car and bike capacity, and apply arrival order among equally eligible vehicles. Hold an uncertain branch and identify its reviewer.
4. **Act.** Simulated parking staff approve overflow. Simulated facilities staff approve standby. Each approval names a proposal and branch evidence version. Reload and validate that branch in the same write transaction.
5. **Verify.** Compare the bay assignment with the gate record and read back the mock device state. Commit the successful state and audit together. Roll back on a mismatch. Show the last checked evidence, outcome and owner.
6. **Adapt.** A fresh occupied or stale reading revokes the room token. Facilities can approve again after a fresh eligible vacancy window. The parking assignment remains verified. Duplicate or expired events leave the state consistent.

**Provider contract.** Cap the initial design at one model choice per new note. Deduplicate in-flight choices by run and note ID. Keep model time outside the SQLite write transaction and discard any result whose note or run changed. Target a visible operator fallback within **5 seconds** if the provider times out, returns malformed arguments or is rate-limited. Use the same policy path when the coordinator confirms a structured lookup. Show **Live model** or **Structured intake** in the audit according to what ran. Provider choice, deadline and escalation behavior are final-round implementation and test targets. [Current model adapter](../prototype/agent.py) · [Current transaction boundary](../prototype/app.py)

**Minimum fixtures**

| Fixture | Input | Expected result |
| --- | --- | --- |
| Lab moved and delayed | A visitor note mentions Lab 2 and “20 minutes late.” | The selected record confirms the move and revised times. The case supports the main overflow and room recovery demonstration. |
| Session ends late in the same room | A second synthetic reference names a different session and an end-time delay. | The correct record changes the relevant demand window. The occupied or booked room produces no standby proposal. |
| Ambiguous session | A note could match either record or supplies contradictory details. | Ask for coordinator confirmation. Show why actions remain on hold. |

## Prove the results

Keep the existing 12 tests green. Before testing, write the expected source, proposal and outcome for **12 synthetic cases**. Cover three straightforward notes, three ambiguous notes, two occupancy or stale-evidence cases, two capacity or concurrency cases, and two source or provider failure cases.

Run the same notes through two paths. In the baseline, an operator reads the note and selects the structured session. In the candidate, the model selects a lookup or asks the operator. Both use the same data, rules, approvals and verification. Alternate run order where practical. Record every result, including a correct hold or a provider failure.

| Measure | Release or presentation rule |
| --- | --- |
| Valid source and clarification decisions | Count correct lookups and correct holds separately. Show how much operator input each mode required. |
| Unsafe or unauthorized writes | **Zero across the tested cases** is the P0 release gate. A single failure blocks release until it is corrected and retested. |
| Main browser journey | Three consecutive reset-to-audit runs on the presentation laptop. For live model mode, include two distinct note patterns in addition to three runs of the planned demo. |
| Latency and overhead | Record model request time, local processing, and operator decision time separately. Report median, range and sample size. The Alpha in-process measurement was 0.97 ms median and 1.06 ms p95 across 210 offline requests. Remeasure on the final build before making a Beta claim. |
| Repeatability | Confirm one verified effect under competing approvals, safe rollback after readback failure, and structured intake with provider access disabled. |

Export the case table with expected and actual decisions, the input mode, human touches, outcome, and timing. Report improvements only if the comparison measures them. Use the synthetic outcome counts as evidence about the prototype. Campus-wide impact would require a separate pilot. [Alpha benchmark methodology](../evaluation/PROTOTYPE_VERIFICATION.md)

## Judge walkthrough and release

Use a **three-minute core** until the organizer confirms the format.

| Time | Show | What judges should see |
| --- | --- | --- |
| **0:00–0:20** | One late timetable note and the two people who need a decision | One cause across parking and teaching space |
| **0:20–0:40** | One diagram with the model, server policy, versioned approvals and audit | Exactly what the model can choose and what staff control |
| **0:40–2:05** | Select a fresh note, show the source lookup, approve overflow, inject occupancy, recheck, approve standby and open the audit | A grounded model decision, verified state changes, and recovery without undoing parking |
| **2:05–2:40** | Show paired baseline results and the strongest failure test | Measured evidence, including sample size and operating mode |
| **2:40–3:00** | Close on the incident and the lawful next pilot | A credible deployment path with authenticated staff and verified data sources |

**Fallback order.** Use the live model only when it passes the readiness gate on the presenting laptop. If the provider fails during the demo, switch to labeled structured intake and finish the workflow. If the browser or server fails, use labeled captures from a verified run. When permitted, use an authorized recording as another fallback. [Existing verified captures](../presentation/DEMO_STORYBOARD.md)

**Review before freeze.** Ask one technical reviewer to reproduce the demo from the README. Ask a skeptical judge, an operations reviewer, an AI reviewer, and a feasibility reviewer to each name the strongest objection. Resolve blocking claims before freezing. In Q&A, be ready to show a trace proving the model selected the source, the exact check that revoked the stale approval, and the baseline comparison.

**Submission package.** Follow Beta instructions for the deck, source and run guide, test results, available diagrams and any fallback. Record team contributions, open-source dependencies, AI model use and any mock integrations. Verify the exact submitted version and receipt. Keep the installed environment and one safe copy of the verified build on the presenting laptop. [Rules and constraints](../context/RULES_AND_CONSTRAINTS.md)
