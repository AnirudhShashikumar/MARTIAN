# Problem selection

1. Preserve every official statement and extract requirements in [problem statements](../context/PROBLEM_STATEMENTS.md).
2. Screen for explicit eligibility and mandatory requirements. Record exclusions with the source clause. For uncertain constraints, record evidence needed and an assumption to verify.
3. Apply the official rubric when available and applicable. Otherwise score each eligible option on the internal framework below. For each score, record one reason, the main uncertainty and a potential demonstration moment.
4. Recommend the strongest option and rank the top three when available. Include likely overused approaches as hypotheses, technical and data risks, bottlenecks, demo potential and where genuine agency matters. Explain why the recommendation improves the chance of advancing and can be defended and built overnight.
5. Request user approval before committing. Apply organizer assignment and approval rules and record the outcome in [decisions](DECISIONS.md).

| Internal criterion | Weight |
| --- | ---: |
| Innovation and originality | 20% |
| Genuine agentic AI relevance | 20% |
| Competitive differentiation | 15% |
| Final-round implementation feasibility | 15% |
| Campus relevance and practical impact | 10% |
| Round 1 presentation potential | 10% |
| Live demonstration potential | 5% |
| Data and infrastructure availability | 5% |

Use scores from 1 to 10. A score of 1 signals a severe weakness, 5 signals a plausible case with significant gaps, and 10 requires strong supporting evidence. Weighted points for a criterion equal its weight times its score divided by 10. Sum to a score out of 100. For a close call, surface the feasibility and agentic fit trade-off, plus any fact that could reverse the ranking.

## Round 1 ranking · November 25

**Recommend Security Track 3, Life-Support Watchdog.** Lead with a campus operator facing contradictory readings. Show two simulated situations with the same initial sensor spike: one corroborated by independent readings and one contradicted by the rest of the fleet. The agent chooses a cross-check, updates its assessment with the results, and proposes a proportionate action. An operator approves any isolation of a simulated data feed. The demo verifies the resulting monitoring state and shows the evidence trail. Use a fixed-threshold alert as a baseline and measure false interventions and appropriate escalations on replayed sample cases.

The ranking assumes a small simulated fleet and a model setup compatible with the organizer’s lab-isolation requirements. If the team cannot confirm those quickly, choose **Management Track 3, Crew Sync**. Keep the Round 1 pitch anchored to one visible incident and the required Round 2 deliverables.

| Rank and official track | Originality 20 | Agent fit 20 | Differentiation 15 | Feasibility 15 | Campus impact 10 | Pitch 10 | Demo 5 | Resources 5 | Weighted /100 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1. Life-Support Watchdog · Security 3 | 9 | 9 | 9 | 8 | 9 | 9 | 10 | 8 | 88.5 |
| 2. Crew Sync · Management 3 | 7 | 8 | 8 | 9 | 8 | 9 | 9 | 9 | 81.5 |
| 3. Galley Control · Management 2 | 6 | 7 | 7 | 7 | 9 | 9 | 9 | 8 | 73.5 |
| 4. Mission Portal Shield · Security 2 | 6 | 7 | 6 | 7 | 8 | 8 | 9 | 8 | 70.0 |
| 5. Comms Guardian · Security 1 | 6 | 8 | 6 | 6 | 8 | 7 | 7 | 6 | 67.5 |
| 6. Arena Command · Management 1 | 6 | 7 | 6 | 6 | 7 | 7 | 7 | 8 | 65.5 |

These internal scores are planning estimates. No official rubric or competitor submissions have been received. Familiar approaches below are hypotheses.

| Track | Strongest demo moment | Main shortlist or delivery risk |
| --- | --- | --- |
| Watchdog | The same first alert leads to two defensible decisions after corroboration, with an operator-approved response and a verified monitoring state. | A scripted alert timeline could pass for a fixed rule. Demonstrate the model choosing a follow-up check in response to evidence. The model and synthetic fleet must fit the isolated demo environment. |
| Crew Sync | A room drops out and the agent finds a replacement or joint event, checks accessibility and volunteer constraints, and verifies the revised schedule before presenting it for approval. | A calendar with AI summaries may feel familiar. The brief also expects collaboration, volunteer matching, activity signals and reports, so cover these with lightweight sample workflows. |
| Galley Control | Show order, simulated payment and QR collection, then a disputed cancellation or refund that the agent reviews against order and outlet records. | Payment, refund and redemption states add build work. Deterministic service rules enforce ledger state and QR validity. Keep agent reasoning for ambiguous exceptions and escalation. |
| Portal Shield | Compare the same harmless simulated incident without and with defensive triage on a fake campus portal. | A block-alert pitch may feel familiar. A credible baseline, portal and safe isolated demo all take time. |
| Comms Guardian | Turn several synthetic network signals into one prioritized case with a traceable recommendation and human review. | A realistic simulated campus network and useful telemetry are significant overnight dependencies. Alert dashboards are a plausible common pitch. |
| Arena Command | Resolve a tournament disruption while showing its effect on fixtures, approvals and reports. | Registrations, permissions, funding, achievements and reporting make it easy to promise more than the team can integrate. |

### Open Innovation decision

Keep both Open Innovation tracks as fallbacks. They require organizer approval of a specific statement before work begins, so a scored comparison needs a concrete candidate. Revisit only if the team can identify a better-evidenced campus pain point, a sharper end-to-end demo using sample data, and a fast path to approval. The predefined Watchdog and Crew Sync tracks already offer a distinctive scenario.

Decision pending user approval. [Official tracks and requirements](../context/PROBLEM_STATEMENTS.md)

## Management Open Innovation

The team selected Management Track 4, superseding the predefined-track recommendation above. The [official Round 1 rubric](../context/JUDGING_CRITERIA.md) replaces the earlier internal ranking weights for this decision. The [15 opportunities](OPEN_INNOVATION_IDEAS.md) passed a design-stage eligibility screen. A working PoC and organizer approval are pending for every option.

Each row estimates an attainable score under the official rubric **if** the proposed evidence and a working authorized PoC are delivered. These are comparative planning estimates. PoC, Technical Research, Feasibility, then Market break ties in that order. Scores out of 100 are the same totals scaled by five.

| Rank | Problem | Core innovation | Agent strength / pitch | PoC /5 | Tech /5 | Market /5 | Execution /5 | Weighted score |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: |
| 1 | AccessRelay · accessible class continuity | Verified recovery of access after a route outage | High / High | 4 | 4 | 4 | 5 | **17/20 · 85/100** |
| 2 | BenchShift · unavailable instruments | Substitute eligibility with evidence | High / High | 4 | 4 | 3 | 4 | 15/20 · 75/100 |
| 3 | ExamRelay · disrupted exam conditions | Accommodation constraints survive rebooking | High / High | 3 | 4 | 4 | 4 | 15/20 · 75/100 |
| 4 | DormPivot · hostel outage | Coverage and confirmation by affected unit | Medium / High | 4 | 3 | 3 | 4 | 14/20 · 70/100 |
| 5 | ReUse Dispatch · surplus transfer | Condition evidence through recipient receipt | High / Medium | 3 | 4 | 3 | 4 | 14/20 · 70/100 |
| 6 | RoomFit · AV disruption | Verified capability recovery | Medium / Medium | 4 | 3 | 2 | 4 | 13/20 · 65/100 |
| 7 | PermitPath · fragmented approvals | Policy-driven blocker verification | High / Medium | 3 | 4 | 2 | 4 | 13/20 · 65/100 |
| 8 | CareLoop · bounced referrals | Owner acceptance after guided clarification | High / Medium | 3 | 4 | 2 | 3 | 12/20 · 60/100 |
| 9 | QueueReturn · canceled lab slots | Eligibility-aware slot refill | Medium / Medium | 3 | 3 | 2 | 4 | 12/20 · 60/100 |
| 10 | WaterHandoff · ambiguous utility loss | Corroboration to owner acknowledgment | Medium / Medium | 3 | 3 | 3 | 3 | 12/20 · 60/100 |
| 11 | RouteReserve · inaccessible shuttle stop | Evidence-backed pickup alternative | Medium / High | 3 | 3 | 2 | 3 | 11/20 · 55/100 |
| 12 | StockSub · teaching lab shortage | Explainable specification substitution | Medium / Medium | 3 | 2 | 2 | 4 | 11/20 · 55/100 |
| 13= | FixOnce · duplicate facilities tickets | Human-confirmed contextual grouping | Medium / Low | 3 | 2 | 1 | 4 | 10/20 · 50/100 |
| 13= | DeskCover · sudden staff absence | Verified qualifications and shift balance | Medium / Medium | 3 | 2 | 1 | 4 | 10/20 · 50/100 |
| 15 | PolicyReturn · ambiguous intake owner | Version-aware ownership decision | Medium / Low | 2 | 3 | 2 | 3 | 10/20 · 50/100 |

AccessRelay leads on feasibility and has direct operational evidence. It projects 4/5 on PoC because a single scenario and API dependency still need reliability testing, 4/5 on Tech because model contract and latency are unmeasured, and 4/5 on Market because documented workflows and named incumbents support the wedge while local frequency and willingness to adopt remain unknown. Its narrow fixture, single actor for approval and explicit fallback support the 5/5 Execution target. Absent a live PoC, the rubric’s PoC band is 0–1, so scoring the three other categories at the targets above would yield **13–14/20**, with a weak first tie-breaker. No score has been earned.

Confidence is **moderate** for AccessRelay and BenchShift, supported by direct documentation of the institutional workflow, and moderate for ExamRelay on problem reality with lower confidence on delivery. DormPivot through PolicyReturn have low-to-moderate confidence. We penalized a narrow conventional rules-only role, unsupported market assumptions, broader integration dependencies, privacy-sensitive workflows and concepts whose first demo could look like existing scheduling or case tools. Designs and risks appear in the [opportunity catalog](OPEN_INNOVATION_IDEAS.md). The [judge tournament](../evaluation/JUDGE_TOURNAMENT.md) gives the strongest objections.
