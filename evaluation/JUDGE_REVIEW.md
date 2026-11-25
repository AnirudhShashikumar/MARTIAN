# Adversarial judge review

## Checkpoint Alpha · three finalists

Simulated reviewer judgments. Comparative scores and the real judging criteria are in the [final ranking](../strategy/PROBLEM_SELECTION.md#final-round-1-comparison).

| Reviewer | CampusFlow | AccessRelay | BenchShift |
| --- | --- | --- | --- |
| Innovation | Two unrelated automations are easy to dismiss. Use one incident and show how the revised session changes both operational decisions. | A room scheduler is an obvious comparator. Show a vacant room rejected because it depends on the same blocked route. | A reservation system already knows equipment availability. Show a superficially compatible device rejected for a verified capability or staffing reason. |
| Agentic AI | Typed data could drive fixed rules. Demonstrate the model resolving whether a delayed session starts or ends later and choosing a verification or escalation. | The model must resolve unclear outage scope. Keep accessibility eligibility deterministic. | The model interprets a note and selects the next evidence source. Lab staff retain authority over equivalence. |
| Technical architecture | Two actions can conflict or change independently. Recheck the evidence per branch and verify the transaction and resulting state. | Versioned route and booking checks must survive an approval race. | Check capability and technician readiness in the same transaction before changing a booking. |
| Campus administration | Protect eligible and reserved spaces, personal privacy and role ownership. Position the campus problem as a hypothesis grounded in public workflows. | Keep names and accommodation reasons out of the workflow. Registrar approves. | No inferred method approval. Use explicit fixture capability and lab custodian signoff. |
| Feasibility | A full campus dashboard is risky. One gate, one room, one incident and no required hardware create a plausible PoC. | A small route graph works. Reliable, verified route data become a dependency beyond the fixture. | Compatibility taxonomy and operators can grow rapidly. Limit the prototype to two explicit profiles. |

| Finalist | Three shortlist reasons | Three plausible rejections | Decisive defense or revision |
| --- | --- | --- | --- |
| CampusFlow | Recognizable consequence, visible approval and recovery, small local fixture | Weak coupling, rules-only appearance, absent working code | Strongest advantage is two verified outcomes from one confirmed incident. Most vulnerable claim is coordination. Show why the revised window changes overflow and why fresh evidence can hold only the room branch. Weakest assumption is measurable local need. Main delivery risk is testing both branches before the cutoff. |
| AccessRelay | Human access stakes, direct university procedures, visible rerouting | Generic scheduler, incomplete route data, overclaiming accessibility | Strongest advantage is access-aware revalidation. Most vulnerable claim is guaranteeing access. Show verified fixture routes and a safe escalation. Weakest assumption is adequate route inventory. Main delivery risk is creating realistic route evidence. |
| BenchShift | Clear operational cost, verified reservation fallback, good human ownership | Booking overlap, unverifiable equipment equivalence, jargon-heavy pitch | Strongest advantage is compatibility-aware recovery after an outage. Most difficult question is who vouches for the substitute. Use a custodian-approved fixture. Weakest assumption is stable equivalence rules. Main delivery risk is overbuilding the taxonomy. |

**Quality gate.** CampusFlow passes the 10-second test with “A lab move leaves cars at a full gate and a classroom still powered.” The one-diagram test is event → model → checks → independent approvals and readback. The memory cue is “Parking verified, room held.” For the demo test, show actual writes and one recheck only once they run. The easiest PoC rejection is an unimplemented demo. The strongest innovation rejection is “two rules behind a chatbot.” Use a changed wording and a different evidence request in a second test to answer it.

## Reusable review checklist

Run five perspectives before finalizing the deck.

| Perspective | Question that could cost a shortlist slot |
| --- | --- |
| Agentic AI expert | Which decision requires autonomy, and how does the system verify and adapt? |
| Technical architecture judge | What happens when a dependency, data source or agent action fails? |
| Campus stakeholder | Who owns the workflow and what privacy, approval and escalation requirements matter? |
| Innovation evaluator | What already addresses this, and which verified gap remains? |
| Skeptical feasibility judge | What can the team build overnight and prove live with available data and resources? |

Score the proposal with the official rubric. If unavailable, use the [internal weighted criteria](../strategy/PROBLEM_SELECTION.md) on a 100-point scale and label the result internal. Tie each score to evidence. Give the strongest rejection reason and list each major weakness, shortlist impact, concrete correction, urgency and owner. Recheck urgent fixes before export and send the hardest questions to [judge Q&A](../presentation/JUDGE_QA.md).
