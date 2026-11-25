# CampusFlow innovation

**One late session change creates a single auditable case with two independently verified actions: overflow parking and room standby.**

The AI model interprets an ambiguous staff note, chooses which source to consult and can select a clarification when evidence conflicts. In the demo, “running 20 minutes late” can refer to start or end. The tool lookup checks the canonical schedule instead of guessing. The model can then select the relevant arrival window, parking lookup and former-room lookup. Typed rules enforce capacity, eligibility, freshness, reservations, roles and safe device controls.

| Alternative | What it can do | CampusFlow difference to demonstrate |
| --- | --- | --- |
| Manual coordination | A coordinator can check schedules, gates and room status and contact both staff roles. | Compare time to verified action and missed checks with the same inputs. |
| Dedicated parking, scheduling and occupancy tools | T2 handles parking access and entry/exit, 25Live centralizes room schedules, and conventional controls can use occupancy. | Verify how the same late change affects two operational decisions and show evidence, approval and readback for each. Existing custom integrations have not been exhaustively assessed. |
| Chatbot or dashboard | Summarizes the note or displays availability. | Commit an approved mock parking action, hold stale room power and verify resulting state. |
| Strong rules and optimization system | Can coordinate both streams when event identity, window and room are already typed. | Test the additional help with ambiguous notes, conflicting reports and which clarification is needed. If results are equivalent, narrow the AI claim to intake and exception handling. |

**Competitor hypotheses.** An average team may show a dashboard or smart-lights demo. A strong team could add first-fit parking and vacancy detection. An exceptional team might show integrated booking and capacity optimization. Our best response is an ambiguous real-world-style trigger, one invalidated room action, independent verification of the parking outcome, and a fair benchmark against a structured rules baseline. [T2](https://www.t2systems.com/parcs-parking-access/) · [Mississippi State on 25Live](https://www.registrar.msstate.edu/faculty-staff/resources/25live-room-scheduling-software) · [DOE](https://betterbuildingssolutioncenter.energy.gov/resources/wireless-occupancy-sensors-lighting-controls)

The transfer from earlier research is evidence selection (RiskWise), explicit policy checks (VendorGuard) and a verifiable operational artifact (Province). The campus schedule-to-action mechanism is the team's proposed original implementation. [Verified winners](../references/research/HACKATHON_WINNERS.md) · [Winning patterns](../strategy/WINNING_PATTERNS.md)
