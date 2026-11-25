# CampusFlow three minute judge presentation

**MARTIAN 1.0 · Checkpoint Alpha · Management Track 4 · Open Innovation**

**Rehearsal target** Finish the spoken close at **2:57**. Keep the browser demo on the one lab move. The moment to emphasize is **parking verified, room held**.

## Set up before the timer starts

1. Open the [seven-slide deck](CampusFlow_Round_1_Two_Tab_Draft.pptx) at slide 1 and [CampusFlow](http://127.0.0.1:8765/) in a separate window. Rehearse switching from slide 5 to the browser and back. If the server is down, use the [local launch command](../prototype/README.md#run-locally) or the stills below.
2. In CampusFlow, click **Reset demo**. Confirm you see **Campus operations**, **Vehicle Fleet Management → Parking overview**, **0 / 3** general car bays free and **1 / 3** bike bays free. The demo panel should say **Trigger schedule change**.
3. Open the four fallback images in order. Keep notifications off and the browser at its tested zoom. Start the timer with the opening line.

## 0:00 to 1:20 · Slides 1 through 4

| Time | Show and point | Say this aloud |
| --- | --- | --- |
| **0:00–0:10** | **1 · Cover.** Say the team name once. | “We’re [team name]. A lab session moves, visitors reach a full car lot, and the classroom it left behind is still powered. This is CampusFlow.” |
| **0:10–0:29** | **2 · Problem.** Point from parking to the classroom. | “Parking and classroom scheduling already have dedicated tools. The coordination gap starts when one timetable revision changes who is arriving and which room is free. Parking staff need a valid overflow decision, while facilities needs evidence that the room is empty.” |
| **0:29–0:50** | **3 · Solution.** Point to the shared incident, then the two branches. | “CampusFlow links both decisions to one incident. It checks the timetable to resolve an ambiguous note, proposes eligible overflow and a room action, and sends each to the staff role responsible. Each team gets a verified result and the evidence behind it.” |
| **0:50–1:20** | **4 · Technical implementation.** Trace evidence → policy → approval → readback. | “The browser runs against FastAPI and SQLite. The server checks capacity, protected bays, bookings and vacancy. An approval is tied to that branch’s evidence version. The server rechecks it and reads back the mock state before committing the change and its audit. We tested stale approvals, simultaneous approvals and rollback. The demo uses synthetic data and offline timetable confirmation.” |

## 1:20 to 2:40 · Slide 5 and the live clicks

Advance to **slide 5**, then switch to CampusFlow. The times are cues for when to click. Use the words in the last column while pointing at the visible result.

| Time | Click exactly | Point at this result | Say this aloud |
| --- | --- | --- | --- |
| **1:22** | **Trigger schedule change** | Staff note and two Gate A arrivals. | “The note says the lab moved and is twenty minutes late.” |
| **1:30** | **Confirm timetable lookup** | **Lab 2 · 14:20–15:05** and both proposals. The bike appears in **B-03**. | “The timetable confirms a later start, moves the session to Lab 2, and frees C-101. The bike gets a regular bay.” |
| **1:41** | **Approve overflow** | **CAR-078 · OV-01** and **Verified** in the fleet summary. | “The car lot is full. Parking approves temporary overflow, and the bay and gate records agree.” |
| **1:51** | **Confirm regular car exit** | **C-01** reopens. General car capacity changes to **1 / 3 free**. | “A confirmed exit releases a regular bay.” |
| **1:57** | **Open resource view** | C-101, **Approval needed**, lights, fans and projector **On**. | “Facilities has a pending standby proposal. Watch what happens when someone returns.” |
| **2:05** | **Inject occupied reading** | **1 person detected**, **Safety hold**, all devices **On**. Point back to fleet **Verified** and pause. | “CampusFlow revokes the room proposal. The devices stay on, and the verified parking assignment stays in place.” |
| **2:16** | **Recheck sustained vacancy** | New synthetic vacancy readings and a fresh proposal. | “A new twenty-second synthetic vacancy window makes the room eligible again.” |
| **2:24** | **Approve standby** | Lights **Off**, fans **Off**, projector **Standby**. | “Facilities approves again. CampusFlow reads back all three mock device states.” |
| **2:31** | **View decision audit** | **2 / 2** verified branches, **1** blocked proposal, **1** bay released. | “The audit records two verified decisions, one blocked power action, and one bay released.” |

## 2:40 to 3:00 · Feasibility and close

| Time | Show | Say this aloud |
| --- | --- | --- |
| **2:40–2:53** | Return to the deck and advance to **6 · Feasibility**. | “This runs locally on one laptop and passed twelve automated tests. For the finale, we’ll compare it with manual coordination using the same scenarios, then test more exceptions.” |
| **2:53–2:57** | **7 · Team and tools.** Face the judges. | “One campus change. Two decisions staff can verify.” |

At **2:57**, stop and take the first question. If time slips, keep the occupied-room hold, the standby readback and the closing line. Give the exit and audit results in one sentence.

## If the browser stalls

Switch to the saved screens on the first failed step. Say “These captures are from our verified local run on synthetic data.” Continue at the point you reached.

1. [Verified overflow and regular bay release](assets/CampusFlow_Fleet_Verified.jpg)
2. [C-101 safety hold with parking still verified](assets/CampusFlow_Room_Safety_Hold.jpg)
3. [Two verified outcomes and device readback](assets/CampusFlow_Verified_Outcome.jpg)
4. [Impact counts](assets/CampusFlow_Scenario_Impact.png)

If **Run agent** appears unexpectedly, use the verified offline configuration for the pitch. If a model call has already stalled and the coordinator prompt appears, click **Confirm synthetic schedule** and resume.

## Answers to keep ready

- **Where is the AI?** The verified run uses operator-confirmed timetable lookup. The optional Gemini path selects a read tool or requests clarification. The server stages proposals and enforces approvals. Live provider execution remains unverified.
- **What if two people approve at once?** The server serializes the SQLite writes and checks the active proposal token. The concurrency test produced one verified assignment. The second approval was rejected.
- **How do you know the room action succeeded?** The fixture guard checks freshness, booking, vacancy and manual hold. After approval, the server reads back the mock device state in the same transaction. The failed-readback test confirmed rollback.
- **What impact did you measure?** Two verified branches, one blocked standby proposal and one released bay in the synthetic run. The proposed finale comparison measures time to verified resolution and missed checks with identical inputs.

[Technical data flow](assets/CampusFlow_Data_Flow.png) · [Verification report](../evaluation/PROTOTYPE_VERIFICATION.md) · [Full judge Q&A](JUDGE_QA.md)
