# CampusFlow · 75-second demonstration

Start on **Vehicle Fleet Management → Parking overview** at 16:9 with **Reset demo** available. Use the offline structured intake unless a team-configured Gemini model has been tested on the presenting laptop. Every arrival, occupant count and device action uses synthetic data.

| Time | Screen and action | Expected response | Say |
| --- | --- | --- | --- |
| 0–10s | Parking overview. Select **Trigger schedule change**. | The ambiguous note and two Gate A arrivals appear in one incident. | “Lab induction moved, the note says ‘20 minutes late,’ and two arrivals are at Gate A.” |
| 10–20s | Select **Confirm timetable lookup**. In a separately validated model run, select **Run agent**. | The authoritative record confirms Lab 2, 14:20–15:05. Both branch proposals appear. | Offline: “I’m selecting the authoritative lookup in structured intake. The record confirms a later start and frees C-101.” Model: “The agent chose the timetable lookup before proposing actions.” |
| 20–34s | Select **Approve overflow**, then **Confirm regular car exit**. | The regular bike has B-03, CAR-078 gets OV-01, and the confirmed exit opens C-01. | “The bike uses a regular bay. The first eligible waiting car gets approved overflow. Both protected car bays stay free.” |
| 34–49s | Select **Open resource view**, then **Inject occupied reading**. | The former room has one occupant, the proposal is revoked and all devices stay on. Parking retains its verified status. | “Someone returned to C-101 before approval. Facilities loses the stale proposal, while the parking decision remains verified.” |
| 49–65s | Select **Recheck sustained vacancy**, then **Approve standby**. | A new 20-second synthetic count sequence produces a new proposal. Readback shows lights and fans off and projector standby. | “A fresh vacancy window and a separate facilities approval are required. CampusFlow reads back each mock device state.” |
| 65–75s | Select **View decision audit**. | Two verified branches, one blocked room proposal and one released bay. | “One schedule change, two verified decisions. This run also blocked one proposed power change and released one bay on exit.” |

## Still-image fallback

If a model call fails, use **Confirm synthetic schedule** to continue locally. On a browser or local server failure, present the stills in sequence and say “These are captures of a local run on synthetic data.” Use the saved impact image to close. The scenario clock represents demo evidence time.

| Slide material | Asset |
| --- | --- |
| Operations overview | [Operations overview](assets/CampusFlow_Operations_Overview.jpg) |
| Fleet decision and human approval | [Overflow approval](assets/CampusFlow_Fleet_Approval.jpg) · [Verified fleet state](assets/CampusFlow_Fleet_Verified.jpg) |
| Room exception and recovery | [Safety hold](assets/CampusFlow_Room_Safety_Hold.jpg) · [Fresh facilities approval](assets/CampusFlow_Facilities_Approval.jpg) |
| Hero and audit | [Verified outcome](assets/CampusFlow_Verified_Outcome.jpg) · [Incident audit](assets/CampusFlow_Incident_Audit.jpg) |
| Architecture and workflow | [System architecture](assets/CampusFlow_System_Architecture.png) · [Agent workflow](assets/CampusFlow_Agent_Workflow.png) · [Data flow](assets/CampusFlow_Data_Flow.png) |
| Synthetic impact | [Before and after](assets/CampusFlow_Scenario_Impact.png) |

Keep the main demo on Parking overview and Rooms & devices. Gate ledger and Overflow approvals drill into fleet detail. Labs, Library seats and Sports equipment show the broader resource scope if judges ask. The sample equipment checkout and return are a separate sandbox action.
