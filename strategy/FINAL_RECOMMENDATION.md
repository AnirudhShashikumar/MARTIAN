# Checkpoint Alpha decision package

The latest recommendation is the [integrated AccessRelay statement](INTEGRATED_PROBLEM_STATEMENT.md) for practical-assessment continuity. This research package preserves the comparison that preceded that synthesis.

## 1. Executive recommendation

**Approve AccessRelay for Management Track 4 · Open Innovation.** The proposed problem is **Accessible Classroom Continuity After Campus Access Outages**. When a lift or step-free route fails, AccessRelay identifies teaching sessions that lose access, proposes an available and reachable replacement, and verifies the booking and instructor acknowledgment after registrar approval.

**Projected 17/20 under the official rubric, with moderate confidence.** This is a comparative target conditional on a permitted, working PoC. The hook is easy to grasp, publicly documented university workflows establish the problem class, and the smallest end-to-end demo needs one laptop and synthetic records. The biggest risk is the rubric’s live-code requirement conflicting with the earlier PPT-only schedule. Local disruption frequency and adoption remain unverified. The decision is pending the team’s approval and organizer approval of the statement. [Official rubric and conflict](../context/JUDGING_CRITERIA.md)

## 2. Verified winning-project research

The database contains 22 projects from Google Cloud ADK, Microsoft AI Agents and Agent Academy, AWS AI Agent Global, Berkeley AgentX, Imagine Cup, Google Solution Challenge, IBM Call for Code, NASA Space Apps, Smart India Hackathon and TreeHacks. Award types and evidence appear alongside the mechanism and transfer hypothesis. [Winner database](../references/research/HACKATHON_WINNERS.md) · [Source registry](../references/research/SOURCE_REGISTRY.md)

## 3. Innovation patterns

Use meaningful model judgment to interpret a messy trigger, make constraints explicit, stage an action, and verify the resulting state. Replanning under a visible surprise distinguishes the demo from a scripted recommendation. Human authority and audit records keep the action defensible. [Patterns](WINNING_PATTERNS.md) · [Campus evidence](CAMPUS_PROBLEM_DISCOVERY.md)

## 4. Ranked opportunity matrix

Fifteen shortlist candidates are scored on the official PoC, Technical Research, Market & Industry, and Feasibility & Execution criteria. AccessRelay leads at 17/20, followed by BenchShift and ExamRelay at 15/20. BenchShift wins that tie on PoC readiness. [Full rubric matrix](PROBLEM_SELECTION.md#management-open-innovation) · [Competitive analysis](COMPETITIVE_ANALYSIS.md)

## 5. Top five detailed concepts

AccessRelay, BenchShift, ExamRelay, DormPivot and ReUse Dispatch each have a formal problem, agent loop, human oversight, 90-second demo, technical scope, fallback, metric, pitch hook and main rejection risk. Five simulated judge perspectives compared the concepts and challenged their weakest claims. [Five concepts](OPEN_INNOVATION_IDEAS.md#top-five-detailed-concepts) · [Judge tournament](../evaluation/JUDGE_TOURNAMENT.md)

## 6. Final top three comparison

| Criterion | AccessRelay | BenchShift | ExamRelay |
| --- | --- | --- | --- |
| Significance | Access to timetabled instruction | Continuity of scarce practical resources | Access to an exam under approved conditions |
| Originality | A route outage becomes an acknowledged academic recovery | Equipment substitution constrained by capabilities and operators | Exam relocation preserves accommodation and proctor coverage |
| Agent necessity | Interpret ambiguous outage scope and select the next evidence source | Interpret a service note and distinguish potential capability matches | Interpret an unexpected change and identify a missing verification |
| Technical sophistication | Route reachability, schedule guards and versioned approval | Equipment capability and staffing rules with transactional reservations | Multiple hard constraints and privacy-preserving exam state |
| Implementation complexity | Low-to-medium with one class and a small campus fixture | Medium, especially the equipment taxonomy | Medium-to-high because of rules, privacy and simultaneous staffing |
| Demo quality | Fastest visual cause and effect | Clear when the audience understands instrument compatibility | High stakes, with more scenario setup |
| PPT and memorability | “The lift is down. Can everyone still attend?” | “One broken instrument. Three practicals at risk.” | “Moving the exam can change who can sit it.” |
| Main risk | Looks like scheduling unless an unsafe or stale option is rejected visibly | Unverified substitution assumptions | Sensitive workflow and too many constraints for a short PoC |
| Overall | **17/20 · recommend** | **15/20 · best fallback** | **15/20 · stronger policy burden** |

## 7. Organizer-ready problem statement

### Accessible Classroom Continuity After Campus Access Outages

When an elevator or step-free route becomes temporarily unavailable, a scheduled class may remain on the timetable even though its room can no longer be reached by everyone. Coordinating a response can require the facilities team to establish the scope of the outage, the timetable office to find a suitable replacement, and the instructor to confirm and share the change. The campus needs a way to identify affected classes, verify that an alternative room has an available step-free route and sufficient capacity, and keep each incident open until a responsible staff member acknowledges the revised plan. When the outage details are incomplete or no suitable room is available, the case should go to a coordinator for review. The workflow should preserve an auditable record without revealing students’ identities or accommodation details.

- **Stakeholders.** Registrar or timetable office, facilities, accessibility staff, instructors and students who rely on step-free access.
- **Proposed solution.** AccessRelay will use a model to interpret sample facilities notices and decide which evidence to check. It will propose a rule-validated relocation for registrar approval and confirm the resulting booking and instructor acknowledgment in a simulated campus environment.
- **Agentic workflow.** Sense the incident and candidate state. Think about scope, conflicting evidence and the next check. Act by staging a validated plan and applying the approved change to sample state. Explain decisions and unresolved uncertainty. Verify the outcome and replan when availability or access changes.
- **Campus impact.** Preserve access to scheduled instruction and make responsibility for each recovery visible. Evaluate successful recovery, invalid changes blocked and time to an acknowledged plan on synthetic cases.
- **Management Open Innovation alignment.** This is a campus academic operations workflow, distinct from the predefined sports, food and clubs tracks. It uses team-created sample data, human review, explainable policy checks and a decision log. All changes occur in the prototype’s local state, with no real college integration or financial action. The team will declare tools and request organizer approval before work begins.

## 8. Winning pitch preview

**15-second opening.** “The lift goes down twenty minutes before class. The timetable still says Room 302. An empty room might have the same access problem. AccessRelay helps the registrar find, approve and confirm a move that keeps the class reachable.”

**30-second elevator pitch.** “When a campus route goes out of service, facilities can report it, but a coordinator still has to work out which classes are affected, which rooms are reachable and who has confirmed the move. AccessRelay reads the outage, pulls the evidence it needs, and checks candidates against access, capacity and schedule rules. If the first option changes, it replans before anything is committed. The registrar approves the move and the incident stays open until the booking and instructor acknowledgment are verified.”

**Value proposition.** Keep classes reachable when campus access changes.

**Central innovation.** A confirmed disruption changes which sessions can run in their existing rooms. The agent works out the incident’s scope and selects the missing evidence. The server protects the rules that determine whether a plan can be committed. The case remains visible until the responsible instructor acknowledges it.

**Live story · 90 seconds within the three-minute walkthrough.**

1. **0–15s.** Enter a synthetic incident note about a lift out of service. The model links the location and time to the affected session.
2. **15–35s.** Show a free room rejected because its only step-free route uses the same lift. The system stages a feasible alternative.
3. **35–55s.** Add a fixture booking that makes the proposed room unavailable. The version check refuses the stale plan. The agent uses current state to stage the next eligible option.
4. **55–75s.** Registrar approves the new version. The mock schedule changes atomically. The instructor sees and acknowledges the synthetic notice.
5. **75–90s.** Read back the active booking, chosen route status and logged approval. Show elapsed time and hard-constraint status for this run. Benchmark claims wait for testing.

**Technical plan.** Use a local browser page, FastAPI and SQLite. Evaluate a team-approved model with schema-constrained function calls such as Gemini, conditional on organizer rules, an existing authorized credential and a connectivity test. The server owns allowed tools, schema and ID validation, room capacity and compatibility, time overlap and route reachability. Model output can request lookups or stage a proposal. Only a role-checked human action can authorize a write. Match the plan to the current availability and route version before committing a booking and an audit event transactionally. Use idempotency on approvals, a bounded model timeout, at most two model turns per planning attempt, one replan after changed state and one retry for transient failures where time permits. Acknowledge in a mock inbox. Record structured decisions, evidence IDs and timestamps, with no identity or free-text personal data in outward notices. Validate provider request latency, rate limits and failure behavior with measured runs before presenting them. [FastAPI](https://fastapi.tiangolo.com/tutorial/response-model/) · [SQLite](https://sqlite.org/lang_transaction.html) · [Model function calling](https://aistudio.google.com/docs/function-calling)

**Build sequence, conditional on approval.** A pre-Alpha PoC, only if explicitly authorized with enough time, would need a 45–60 minute estimate, separate from deck preparation. Keep it to a single incident, the smallest fixture, a model decision, deterministic checks, one approved database write and confirmation. For the published finale window, reserve 4:00–5:30 PM for data and contracts, 5:30–8:30 PM for the core slice, 8:30 PM–12:30 AM for integration and edge cases, 12:30–6:15 AM for repeatable fixture tests, instrumentation and presentation materials, and 6:15–8:30 AM for the freeze, fallback rehearsal, breakfast and judging buffer. Honor breaks and the actual cutoff. MVP is a laptop-only web app and synthetic schedule. Add more sessions only after the narrow demo is stable. Production integrations and campus-wide scale are future work.

**Provisional deck.** Use the seven supplied sections in order: team submission, problem, solution, architecture, demo and roadmap, feasibility, team details. Budget 30 seconds for problem and market, 30 for solution and architecture, 90 for the working flow if authorized, and 30 for feasibility and close. The cover and team fields stay available for submission. [Template mapping](../presentation/SLIDE_PLAN.md)

**Why shortlist us.** Judges can see a precise before-and-after outcome: an affected class moves to an available room with a verified step-free route, and the new booking is acknowledged. They can inspect the evidence, reject a stale approval and determine where AI improved the result.

## 9. Critical risks and rejection analysis

| Risk | Response |
| --- | --- |
| PoC not permitted or unavailable before Alpha | Get organizer clarification immediately. With no working demo, the rubric allocates 0–1 on PoC. A clearly labeled storyboard can explain the plan, with no claim of implementation. |
| Generic room scheduling pitch | Demo an empty room with an invalid access route, then a stale booking. Show verification of an updated accessible booking and acknowledgment. |
| Weak market quantification | Cite university policies and named incumbent capabilities. Seek permission to verify the handoff with a campus coordinator. Report results from the proposed 12-case synthetic test with their sample size and limitations. Never treat a synthetic test as market validation. |
| AI guesses about accessibility | Require confirmed route data, use deterministic reachability and capacity rules, and escalate unknowns. Apply access requirements to the whole session. |
| Unsafe or stale administrative action | Proposal-only model tools. Human approval, version checks and atomic commit. Show one rejected stale proposal and replan. |
| Model or network failure | Enter a structured incident manually and use the same validator, approval and verification path. Disclose when AI is unavailable. If a recording is permitted, label it and show the actual live portion accurately. |

## 10. Final verdict

**Choose AccessRelay and take Section 7 to the organizers for approval.** It leads the rubric assessment because its welfare consequence is immediately visible and its smallest credible demo is an auditable, state-changing workflow. Confirm whether a working PoC is permitted before Alpha. BenchShift is the reserve if organizers decline the classroom continuity scope.
