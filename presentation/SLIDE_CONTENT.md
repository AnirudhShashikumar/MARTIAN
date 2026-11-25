# CampusFlow · Round 1 PPT information document

**Recommendation.** Present CampusFlow as the agent that coordinates what happens **after a late campus schedule change**. Show one shift in demand, an approved overflow parking assignment and a room-power decision that responds to new occupancy evidence. This is the proposed pitch and demonstration. Project approval and PoC status must be confirmed before presentation. [Decision package](../strategy/FINAL_RECOMMENDATION.md) · [Official template](../references/official/SUBMISSION%20TEMPLATEEE.pptx)

Use the seven template slides in order. The blocks labeled **Slide copy** are ready to paste. The notes are for the presenter. The proposed plan shares **180 seconds** between slides and the live walkthrough, with **180 seconds** reserved for Q&A. If a PoC cannot be built within the authorized window, present the planned scenario accurately as a storyboard and record the corresponding rubric risk. [Official rubric](../context/JUDGING_CRITERIA.md)

## 1. Team submission · 10 seconds

**Slide copy**

| Template field | Insert |
| --- | --- |
| Team Name | [Registered team name] |
| Team Leader | [Registered team leader] |
| Chosen Domain | Management · Track 4 · Open Innovation |
| Problem Statement | Coordinating Campus Parking and Shared Resources During Demand Changes |
| Product name, if room permits | **CampusFlow** |

**Visual.** Use the official cover and its existing branding. Add the product name unobtrusively where the reference permits.

**Speaker.** “A lab session moves and runs late. Visiting cars reach a full lot, while the classroom it left behind is still powered. CampusFlow helps staff resolve both from the same schedule change.”

**Why it earns attention.** The audience hears one event, two consequences and a narrow scope in ten seconds.

## 2. Problem Statement & Real-World Impact · 20 seconds

**Slide copy**

> **A room change creates work beyond the timetable.**
>
> - Parking staff reconcile arrivals, departures and temporary capacity.
> - Facilities staff determine whether the old classroom can go into standby.
> - Students and staff need current information before they act.
>
> **The gap:** The operator must connect the revised session, current availability and verified occupancy.

**Visual.** Put the updated session in the center. Show **Full car lot** to the left and **Old classroom still powered** to the right. Underneath, show short comparator labels: **T2 entry/exit · 25Live scheduling · Occupancy lighting controls**.

**Speaker.** “The gate determines space availability, the timetable determines where the session is now, and the room feed shows whether people are still there. Those are three kinds of evidence. Our proposed workflow gives the operator a reliable way to connect them for one change.”

**Evidence and caveat.** Penn State publishes real-time parking capacity. T2 documents gated entry/exit. Mississippi State describes centralized room scheduling. DOE documents occupancy-based lighting control. These establish the operating categories. Local incident frequency, costs and incumbent integration capability remain unverified. [Penn State](https://www.psu.edu/news/university-park/story/transportation-services-announces-real-time-parking-deck-capacity-website) · [T2](https://www.t2systems.com/parcs-parking-access/) · [Mississippi State](https://www.registrar.msstate.edu/faculty-staff/resources/25live-room-scheduling-software) · [U.S. DOE](https://betterbuildingssolutioncenter.energy.gov/resources/wireless-occupancy-sensors-lighting-controls)

**Why it earns marks.** Defines primary users, an operational gap and three named references for Market & Industry.

## 3. Proposed Solution & Innovation · 25 seconds

**Slide copy**

> **One schedule change. Two verified responses.**
>
> - **Sense** the change, gate events and room occupancy.
> - **Think** by resolving the revised session and choosing the checks it needs.
> - **Act** by staging parking and room actions for policy checks and approval.
> - **Explain** the evidence, signed-off actions and verified outcomes.
>
> **If conditions change, recheck before committing.**

**Visual.** Draw the four official stages horizontally. Under **Act**, branch into **Parking** and **Room state**. Show a small **state changed → recheck** arrow back to the check stage.

**Speaker.** “When a note says the lab is running 20 minutes late, the model checks the updated schedule before it decides how long overflow is needed. It checks the former room independently. If someone is still inside, it holds the power change while parking continues. The outputs are verified state changes and a reason for each decision.”

**Why it earns marks.** Defines the model’s decision, tool use and controlled autonomy. The two outcomes can diverge as fresh evidence arrives.

## 4. System Architecture & Technical Implementation · 30 seconds

**Slide copy**

> **The agent plans. The server validates and applies approved actions.**
>
> 1. Synthetic schedule note, gate events and synthetic occupancy replay
> 2. **One model chooses read tools and proposes actions**
> 3. **Capacity, booking and occupancy checks**
> 4. **Staff approval for overflow and room power**
> 5. **Mock parking and room state, audit and readback**
>
> - **Stack:** Browser UI · FastAPI/Pydantic · SQLite · one team-approved model API
> - **Failure path:** stale evidence or model timeout → hold and route to the operator

**Visual.** Use five numbered boxes, with the two sample state targets below the last box. Inputs enter at one side. Place a red arrow from **Checks** to **Hold / recheck**. See the [diagram and tools](../solution/AGENTIC_ARCHITECTURE.md).

**Speaker.** “The model can read the schedule, gate and room state and stage a proposal. It cannot directly write either ledger. The server validates each action and rechecks the exact evidence versions at approval. It uses a transaction to apply the change and audit entry, then reads the state back.”

**Why it earns marks.** Makes permissions, the data lifecycle and failure handling explicit for Technical Research. Stack and provider are proposed until confirmed and tested. [FastAPI](https://fastapi.tiangolo.com/tutorial/response-model/) · [SQLite](https://sqlite.org/lang_transaction.html)

## 5. Demo Plan & Future Roadmap · 75 seconds

**Slide copy**

> **Planned live scenario:** A lab move. A full car lot. A room that may still be occupied.
>
> 1. Confirm revised session → approve temporary overflow → verify bay assignment.
> 2. Detect an occupied frame at approval → block the room transition.
> 3. Confirm sustained vacancy and get fresh approval → verify mock room standby.
>
> - **Measure:** verified actions, unsafe actions blocked, time to resolution.
> - **Roadmap:** One working scenario → repeatable tests → lab, library and equipment handoffs.

**Visual.** Show a before/after timeline with two staff actions. Label demo inputs **Synthetic**. Display a **Parking verified** marker and a distinct **Room held** marker before **Room standby verified**.

| Demo seconds | What to show and say |
| --- | --- |
| 0–12 | Enter the sample note “Lab induction moved to Lab 2 and is running 20 minutes late. Guests are at Gate A.” Show the agent verifying the active booking and interpreting the revised end time. |
| 12–28 | Main car lot is full. A demo bike receives an eligible normal slot. The attendant approves one temporary car overflow bay through the revised window. Show slot ID and a timestamped park/exit path. |
| 28–48 | Scheduled room check and sustained synthetic vacancy allow a draft power action. A fresh frame shows someone returned. The room approval is stale and the system holds the power action. The checked parking assignment remains active. |
| 48–67 | A later synthetic replay with explicit simulated time and sustained fresh vacancy permits a new proposal. After the facilities role approves it, verify lights and fans off and projector in standby in the mock state. |
| 67–75 | Point to two verified outcomes and one blocked unsafe action in the audit view. State which run metrics were actually observed. |

**Roadmap to explain if asked.** Near term, finish the two state changes and failure handling. Mid term, add repeatable synthetic cases and one generic resource checkout. Longer term, assess real deployment with privacy and institution approval. Library-seat and sports-equipment availability can be shown as fixture catalog rows. An optional LED model represents device state.

**Why it earns marks.** Gives PoC an end-to-end state change and a recovery branch. A short storyboard is the presentation fallback if working code is unavailable.

## 6. 24-Hour Grand Finale Build Scope & Feasibility · 15 seconds

**Slide copy**

> - **Build first** · one event, one gate, one overflow zone, one classroom
> - **Then harden** · stale feeds, duplicate events, full lots, approvals and retries
> - **Freeze** · repeatable replay, live readback and a manual-entry fallback
> - **Hardware** · laptop only for MVP, optional standalone LEDs
>
> **Scale path** · keep explicit policies per zone and room, add resource adapters after validation.

**Visual.** Use four compact milestones: **Fixtures → Vertical slice → Safety tests → Freeze**. Put the timetable in notes: **4:00–5:30 PM** fixture/contracts, **5:30–8:30 PM** vertical slice, **8:30 PM–12:30 AM** integration and failure cases, **12:30–6:15 AM** testing and rehearsal, **6:15–8:30 AM** freeze and judging buffer. Planned around the published **16.5-hour elapsed finale window**, with breaks and cutoff confirmed on site. [Feasibility details](../solution/FEASIBILITY.md)

**Speaker.** “We can build the first workflow with a laptop and fixtures. We’ll test stale video and full lots, then freeze the local replay. Hardware comes after repeatable readback.”

**Why it earns marks.** Commits to build order, testing, a fallback and a bounded MVP.

## 7. Team Details · 5 seconds

**Slide copy**

| Template field | Insert |
| --- | --- |
| Team leader details | [Registered leader details required by organizer] |
| Team members | [Names exactly as registered] |
| Contribution areas | [Map actual members to agent/API, state and policy checks, demo/UI, testing and pitch. Combine roles as needed.] |
| Third-party/open-source tools used | [List actual tools, versions/models where known, and required attribution. Mark planned tools separately.] |

**Visual.** Keep one clean roster and a short tool line. Leave contact information out of extra copies unless required.

**Speaker.** “Shortlist us to prove that a last-minute schedule change can close as a verified campus operation.”

**Why it earns marks.** Ends on a specific proof the team can build and keeps ownership and disclosures clear.

## Speaker preparation and submission checks

- Confirm exact approved problem wording, team name, leader, member roster and required contact fields. The workspace has no verified roster.
- Confirm organizer permission for a Round 1 PoC and the actual cutoff. Label the walkthrough as **planned**, **working on synthetic fixtures**, or a **recorded fallback** as applicable.
- Attach short attribution on slides 2 and 4 or in notes. Keep synthetic metrics labeled as proposed until measured. Run the [pitch and fallback timing](PITCH_SCRIPT.md) and practice [judge defense](JUDGE_QA.md).
