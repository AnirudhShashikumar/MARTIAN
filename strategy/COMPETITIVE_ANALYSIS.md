# Competitive analysis

Once a statement is selected, identify the campus stakeholder, the current workflow, its bottleneck and its root cause. Check organizer materials, product documentation and relevant research for capabilities that overlap with the proposed workflow.

For each source, record the title, URL, publication or update date if available, and the specific finding. Compare the manual process, conventional software, basic AI assistance and the proposed agent on the same capabilities. Label anticipated competitor approaches as hypotheses and mark unresolved evidence gaps.

End with one concrete gap, why it matters to the campus, and a scenario that can test the proposed advantage against the strongest practical baseline.

## AccessRelay competitive case

**Primary operator:** registrar or timetable coordinator at a multi-building institution. Facilities confirms an outage. Accessibility staff define or verify route constraints. The instructor acknowledges the new room and communicates the change. Students benefit without entering personal or accommodation data. Columbia documents an explicit handoff after unavoidable relocations and protects the reason for an accommodation. Gonzaga describes missed access when elevators fail. These are examples from other institutions. [Columbia Registrar](https://registrar.columbia.edu/content/protocol-classroom-relocations) · [Gonzaga](https://www.gonzaga.edu/academics/academic-resources/center-for-student-academic-success/disability-access/faculty/elevator-outage-procedure)

| Existing approach | Verified relevant capability | AccessRelay testable wedge |
| --- | --- | --- |
| Facilities request portal, represented by CMU’s service process | Intake and routing for service requests, with a separate urgent contact path. | Resolve the derived class access incident through booking and instructor acknowledgment. [Carnegie Mellon](https://www.cmu.edu/fms/services/service-requests.html) |
| CollegeNET 25Live | Central room scheduling, inventory and operational visibility. | Feed the optimizer a verified incident footprint, include current route status in validity, then track commitment and acknowledgment. [CollegeNET](https://collegenet.com/hubfs/Fliers/25Live%20Flyer%202025.pdf) · [Mississippi State](https://www.registrar.msstate.edu/faculty-staff/resources/25live-room-scheduling-software) |
| Accruent EMS Academic Planning | Academic space and course scheduling workflow. | Validate the revised booking after state changes and keep the access incident open until acknowledgment. [Accruent](https://help.accruent.com/ems/Content/EMSDesktopClient_AcademicPlanning/UserGuide_EMSDesktopClientAcademicPlanning/Introduction.htm) |
| Human coordinator with a scheduling tool | Can interpret ambiguity, check availability and route, obtain signoff and contact instructors. This is the strongest practical baseline. | Measure time, verified coverage and required coordinator steps on the same synthetic cases. |

The public materials reviewed do not establish whether individual deployments already automate some or all of this workflow. Make the narrow claim that AccessRelay demonstrates outage interpretation, route-aware replanning and acknowledgment together. Feasibility of a campus integration is future work.

### Competitor hypotheses and white space

| Landscape hypothesis | Example | Implication |
| --- | --- | --- |
| High competition, low differentiation | FAQ chat, timetable generation, complaint portal or event calendar | Common-shaped outputs give the panel little reason to remember a team. |
| High competition, high differentiation | Timetable optimizer with state-aware recovery, automated service desk | Match the optimizer for deterministic checks and show the full exception workflow. |
| Low competition, low impact | Isolated policy owner lookup or narrow feature suggestions | An unobvious topic still needs a consequential outcome. |
| Low competition, high impact | Accessible class recovery, teaching lab recovery, exam continuity | Each has a named owner and verifiable outcome. AccessRelay is the clearest to explain and the smallest to build. The actual field is unknown. |

| Candidate | Average team hypothesis | Strong team hypothesis | Defensible advantage and memory cue |
| --- | --- | --- | --- |
| AccessRelay | Flags an outage or suggests an empty classroom. | Runs a conflict-aware room optimizer and sends a notice. | Consequence propagates from lift to route to class. A stale plan cannot commit. The case closes only on verified booking and acknowledgment. |
| BenchShift | Gives a calendar of free instruments. | Optimizes allocation across rooms and instruments. | Match trained operators, instrument capabilities and deadline evidence. Show a superficially equivalent instrument being excluded. |
| ExamRelay | Assigns rooms and proctors. | Optimizes capacity, accommodations and staffing. | Audit reconstructed constraints from a late notice and preserve approved conditions through a shift. Strength is high, privacy and schedule risk are high. |
| DormPivot | Sends an outage notice. | Routes residents to alternate services. | Treat alternate capacity and unit acknowledgment as explicit checks. |
| ReUse Dispatch | Lists surplus assets. | Matches assets by detailed compatibility filters. | Preserve condition evidence, approvals and actual receipt through a failed first handoff. |

**Quantification plan.** Model 12 synthetic incidents across clean, ambiguous, stale and unresolvable cases. Compare a fully informed human using a room schedule and a structured-input rules baseline against the agent-assisted workflow. Report valid plans, blocked invalid writes, accepted handoffs, time to approval and steps requiring a coordinator. These are proposed measures. Two published case workflows substantiate recurrence across institutions, with no estimate of frequency, demand or cost at BMSITM. If staff can confirm the workflow in a short non-sensitive interview, record the role and observed handoff steps, with permission and without using personal or case data.
