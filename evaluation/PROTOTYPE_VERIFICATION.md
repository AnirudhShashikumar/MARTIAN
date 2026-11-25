# CampusFlow Checkpoint Alpha verification

Verified November 25, 2026 on the local presentation build. All operational inputs and outputs are synthetic.

## Results

| Check | Result |
| --- | --- |
| Automated API and policy suite | 12 passing tests. Includes the main journey, role rejection, approval concurrency, idempotent exits, window expiry, stale-room and override recovery, constrained model tool selection, failed-readback rollback and equipment checkout. |
| Local browser demonstration | Passed from baseline through updated timetable, bike allocation, overflow approval and readback, regular car exit, occupied-room block, fresh facilities approval, device readback, shared audit and reset. |
| Navigation | Visited both main tabs and all seven subtabs. The synthetic sports kit count changed 4 → 3 → 4 on checkout and return. |
| Browser and projection | No warnings or errors in the observed console. Final outcome fit 1600 × 900. Verified the responsive view at 390 px width without horizontal overflow. Exported seven 1920 × 1080 screenshots. |
| Runtime checks | Python sources compiled, JavaScript syntax passed and Uvicorn served the UI and local API. The static frontend has no production bundling step. |
| Optional model | Tool validation and coordinator fallback passed in tests. A configured Gemini API run remains unverified. The browser demo used structured intake. |

**Observed synthetic outcome.** One case produced two verified branches. A fresh occupied reading revoked one pending room proposal without a device write, and one confirmed regular exit released one bay. The later occupancy sequence led to mock lights and fans off and projector in standby. These figures count results in the fixture. The scenario clock and counts provide no estimate of campus-wide savings or frequency.

## Five-perspective judge review

| Perspective | Hard question | Evidence and remaining work |
| --- | --- | --- |
| Innovation | Why do these actions belong in one case? | TT-018 changes the arrival window and releases the old room. Both panels keep the case visible. Show the room hold beside the still-verified overflow. |
| Agentic AI | What did AI decide in this run? | Structured intake runs the verified workflow offline. The optional model selects a timetable or clarification tool. Demonstrate a live model choice and alternate note only after testing a configured provider. |
| Technical architecture | Can a stale or duplicate approval change state? | Concurrent approval, stale-room token, duplicate gate exit, and rollback checks passed. Same-transaction readback proves mock persistence. Future integrations need actual device acknowledgments. |
| Campus operations | Who retains authority, and what data are needed? | Parking and facilities review independent proposals. Protected bays remain available to eligible users. The room track uses count, confidence and timestamp only. Reviewer identity is simulated on localhost. |
| Feasibility | Can the team present it under a tight deadline? | The main flow runs on one laptop with offline dependencies already installed. Use the 75-second sequence and screenshots if runtime fails. Actual slot and cutoff were pending at verification. |

Use the [local launch commands](../prototype/README.md#run-locally) and [75-second storyboard](../presentation/DEMO_STORYBOARD.md). Reset at the beginning and present the synthetic impact figures only after the audit.
