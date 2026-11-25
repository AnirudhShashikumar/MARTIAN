# CampusFlow · Round 1 PPT information document

**Pitch:** One campus schedule change, two operating tabs, two verified decisions. **College Resource Allocation** handles rooms, labs, library seats, shared sports equipment and classroom devices. **Vehicle Fleet Management** handles car and bike parking, gate timestamps and temporary overflow. One agent reads the schedule change and coordinates both tabs. Parking and facilities staff retain separate approval authority. [Decision package](../strategy/FINAL_RECOMMENDATION.md) · [Official template](../references/official/SUBMISSION%20TEMPLATEEE.pptx)

Use the seven template slides in order. The blocks labeled **Slide copy** are ready to paste. The notes are for the presenter. The proposed plan shares **180 seconds** between slides and the live walkthrough, with **180 seconds** reserved for Q&A. If a PoC cannot be built within the authorized window, present the planned scenario accurately as a storyboard and record the corresponding rubric risk. [Official rubric](../context/JUDGING_CRITERIA.md)

The [editable PowerPoint draft](CampusFlow_Round_1_Two_Tab_Draft.pptx) fills the seven official slides and includes speaker notes. Replace the bracketed registration and tool fields before submission.

## 1. Team submission · 10 seconds

**Slide copy**

| Template field | Insert |
| --- | --- |
| Team Name | [Registered team name] |
| Team Leader | [Registered team leader] |
| Chosen Domain | Management · Track 4 · Open Innovation |
| Problem Statement | Coordinating Campus Parking and Shared Resources During Demand Changes |
| Product name, if room permits | **CampusFlow** |

**Subtitle, if room permits:** *One campus change. Two verified decisions.*

**Visual.** Keep the official cover and its existing branding. If there is room beneath the product name, add the two labels **College Resource Allocation** and **Vehicle Fleet Management** on one line.

**Speaker.** “A lab session moves and runs late. Visiting cars reach a full lot, while the classroom it left behind is still powered. CampusFlow helps staff resolve both from the same schedule change.”

**Why it earns attention.** The audience hears one event, two consequences and a narrow scope in ten seconds.

## 2. Problem Statement & Real-World Impact · 20 seconds

**Slide copy**

> **A late schedule change affects both campus resources and parking.**
>
> | College Resource Allocation | Vehicle Fleet Management |
> | --- | --- |
> | Staff need current availability for classrooms, labs, library seats and sports equipment. | Parking staff need current car and bike slots, entry and exit times, and overflow capacity. |
> | A released booking can leave a classroom powered or still occupied. | A delayed session can change when eligible overflow spaces are needed. |
>
> **The gap:** Staff must reconcile the revised schedule, capacity and occupancy before they act.

**Visual.** Put the updated session in the center. Show **Full car lot** to the left and **Old classroom still powered** to the right. Underneath, show short comparator labels: **T2 entry/exit · 25Live scheduling · Occupancy lighting controls**.

**Speaker.** “On the resource side, staff check the room, equipment and whether the old classroom is still occupied. At the gate, staff check parking by vehicle type and decide when overflow is needed. The revised session gives both teams the context for their decision.”

**Evidence and caveat.** Penn State publishes real-time parking capacity. T2 documents gated entry/exit. Mississippi State describes centralized room scheduling. DOE documents occupancy-based lighting control. These establish the operating categories. Local incident frequency, costs and incumbent integration capability remain unverified. [Penn State](https://www.psu.edu/news/university-park/story/transportation-services-announces-real-time-parking-deck-capacity-website) · [T2](https://www.t2systems.com/parcs-parking-access/) · [Mississippi State](https://www.registrar.msstate.edu/faculty-staff/resources/25live-room-scheduling-software) · [U.S. DOE](https://betterbuildingssolutioncenter.energy.gov/resources/wireless-occupancy-sensors-lighting-controls)

**Why it earns marks.** Defines primary users, an operational gap and three named references for Market & Industry.

## 3. Proposed Solution & Innovation · 25 seconds

**Slide copy**

> **Two operating tabs. One agent coordinates the response.**
>
> | College Resource Allocation | Vehicle Fleet Management |
> | --- | --- |
> | **Spaces:** Classroom and lab availability, library seat capacity. | **Spaces:** Live car and bike slot availability by vehicle type. |
> | **Equipment:** Sports-kit availability and checkout. | **Movement:** Timestamp entry and exit. Assign an eligible space and release it on exit. |
> | **Room devices:** Verify sustained vacancy, then apply staff-approved simulated lights and fans off and projector standby. | **Overflow:** Propose designated extra spaces for the revised session window. Apply after parking staff approval. |
>
> **Sense → Think → Act → Explain** · Verify the result and replan when evidence changes.

**Visual.** Show a two-tab product mockup. Put shared incident context just below the tab bar. Mark one **View proposal** action in each tab and place the agent loop in a narrow strip underneath.

**Speaker.** “College Resource Allocation shows spaces, equipment and room power. Vehicle Fleet Management shows car and bike spaces, gate events and overflow. When a note says the lab is running twenty minutes late, the coordinator checks the revised session window and former room, then creates a separate proposal for each staff role.”

**Why it earns marks.** Defines the model’s decision, tool use and controlled autonomy. The two outcomes can diverge as fresh evidence arrives.

## 4. System Architecture & Technical Implementation · 30 seconds

**Slide copy**

> **One incident record. Separate decisions and permissions.**
>
> 1. Synthetic schedule note, gate events and synthetic occupancy replay
> 2. **One model chooses read tools and proposes actions**
> 3. **Resource branch:** Check booking, fresh vacancy and override → facilities approval → verify mock device state
> 4. **Fleet branch:** Check vehicle class, capacity and window → parking approval → verify mock bay assignment
> 5. **Shared audit:** Evidence, decision, approval, outcome
>
> - **Stack:** Browser UI · FastAPI/Pydantic · SQLite · one team-approved model API
> - **Failure path:** stale evidence or model timeout → hold and route to the operator

**Visual.** Draw one input and model block, then split it into two parallel lanes with matching tab labels. Show role-specific approval in each lane. Rejoin at **Audit and verification**. Route uncertain evidence to **Hold / recheck**. See the [diagram and tools](../solution/AGENTIC_ARCHITECTURE.md).

**Fleet detail image.** The [Vehicle Fleet Management keynote flowchart](assets/Vehicle_Fleet_Management_Keynote_Flowchart.png) shows the proposed RTSP camera interface, OpenCV line crossing, FastAPI/SQLite event ledger and dashboard. The demo uses a synthetic feed. The amber branch shows operator approval and verified overflow writeback.

**Resource detail image.** The [earlier resource keynote flowchart](assets/College_Resource_Management_Keynote_Flowchart.png) shows synthetic occupancy detection and separate timetable and inventory inputs. The amber branch shows agent review, facilities approval, simulated device actions and dashboard readback.

**Speaker.** “One model interprets the schedule and chooses the next lookup. The server checks booking, occupancy and overrides for the resource tab. It checks type, capacity and time for the fleet tab. Each authorized staff role approves its own proposal. The server rechecks the evidence version, writes the action and audit entry together, then reads back the result.”

**Why it earns marks.** Makes permissions, the data lifecycle and failure handling explicit for Technical Research. The local FastAPI and SQLite flow is verified. Gemini intake remains optional and is pending a live provider test. [FastAPI](https://fastapi.tiangolo.com/tutorial/response-model/) · [SQLite](https://sqlite.org/lang_transaction.html)

## 5. Demo Plan & Future Roadmap · 75 seconds

**Slide copy**

> **Live synthetic scenario:** A lab move. A full car lot. A room that may still be occupied.
>
> 1. **Vehicle Fleet Management:** Assign a bike spot, approve temporary car overflow and verify the bay.
> 2. **College Resource Allocation:** An occupied frame invalidates the room-power proposal.
> 3. **College Resource Allocation:** Confirm sustained vacancy, get fresh approval and verify the simulated device states.
>
> - **Measure:** verified actions, unsafe actions blocked, time to resolution.
> - **Roadmap:** One working scenario → repeatable tests → lab, library and equipment handoffs.

**Visual.** Put the two-tab bar above a before/after timeline. Label inputs **Synthetic**. In Vehicle Fleet Management, highlight **Bay verified**. In College Resource Allocation, show **Room held** followed by **Device state verified**. Each tab keeps the same incident ID visible.

| Demo seconds | What to show and say |
| --- | --- |
| 0–12 | **Vehicle Fleet Management.** Trigger the synthetic staff note and confirm the timetable lookup. Show the revised Lab 2 booking window. |
| 12–29 | **Vehicle Fleet Management.** Normal car parking is full and a bike spot is free. Assign the bike, approve one temporary car overflow bay, then show its bay ID and entry timestamp. Use a synthetic exit to show how an occupied spot becomes available. |
| 29–49 | **College Resource Allocation.** Check the former classroom’s schedule and synthetic vacancy. A fresh occupancy count shows someone returned before approval. Hold the room action and display the reason. The parking branch keeps its verified outcome. |
| 49–67 | **College Resource Allocation.** Advance the labeled simulation to sustained vacancy, get fresh facilities approval and verify lights and fans off and projector in standby. |
| 67–75 | Show both outcomes and the blocked room action in the incident audit. State only the effects and timings actually observed in this run. |

**Roadmap to explain if asked.** Near term, finish the two state changes and failure handling. Mid term, add repeatable synthetic cases and one generic resource checkout. Longer term, assess real deployment with privacy and institution approval. Library-seat and sports-equipment availability can be shown as fixture catalog rows. An optional LED model represents device state.

**Why it earns marks.** Gives PoC an end-to-end state change and a recovery branch. Use the [verified storyboard and presentation captures](DEMO_STORYBOARD.md) as the fallback.

## 6. 24-Hour Grand Finale Build Scope & Feasibility · 15 seconds

**Slide copy**

> | College Resource Allocation MVP | Vehicle Fleet Management MVP |
> | --- | --- |
> | One source classroom, one destination lab, occupancy replay and mock device control. Sample library and sports catalog. | One gate, eligible car and bike slots, entry and exit ledger, and one approved overflow zone. |
>
> - **Build order** · fixtures → working changes in both tabs → approval tests → replay and freeze
> - **Hardware** · laptop for the MVP, optional standalone LEDs
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

### Tab contents for mockups and Q&A

| Tab | Show inside the tab |
| --- | --- |
| **College Resource Allocation** | **Spaces:** classroom and lab availability, library seat availability. **Equipment:** sports-kit stock and sample checkout. **Classroom devices:** room booking, occupancy status and freshness, manual override, approval state, and simulated light, fan and projector status. |
| **Vehicle Fleet Management** | **Availability:** car and bike capacity by vehicle class. **Gate log:** synthetic ID, assigned slot, entry time, exit time and current state. **Overflow:** designated area, available spaces, proposed time window, approval and expiry. Occupied bays release on confirmed exit. |

Use the same incident detail drawer from either tab. The drawer carries the revised session, decision reasons, approval, verification and unresolved actions.

- Confirm exact approved problem wording, team name, leader, member roster and required contact fields. The workspace has no verified roster.
- Confirm the actual cutoff. Label the walkthrough **working on synthetic fixtures** with structured intake, or identify the captures as a **fallback**.
- Attach short attribution on slides 2 and 4 or in notes. Keep synthetic metrics labeled as proposed until measured. Run the [pitch and fallback timing](PITCH_SCRIPT.md) and practice [judge defense](JUDGE_QA.md).
