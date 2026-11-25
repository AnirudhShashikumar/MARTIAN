# CampusFlow judge defense

Assign the roles below to registered team members. Use only measured results during Q&A.

| # | Likely hard question | Defensible short answer | Lead |
| --- | --- | --- | --- |
| 1 | Where is AI essential? | “The model resolves what ‘running 20 minutes late’ refers to and chooses whether to read the revised booking or ask for clarification. Fixed rules make the protected writes. We’ll compare with a structured-input rules baseline and report when the AI adds value.” | Agent |
| 2 | What actually ties parking to room occupancy? | “Both derive from the same confirmed session change. Its revised window sets the overflow proposal, and its old room determines where to check vacancy. We verify each branch independently, because occupancy can change without invalidating parking.” | Product |
| 3 | How is this different from T2, 25Live and occupancy controls? | “They document strong capabilities in their own operational areas. We propose testing how much staff effort a single case saves when it interprets a change, checks both sources and verifies both outcomes. Custom integrations may already do parts of this.” | Product |
| 4 | What if the camera misses someone or becomes stale? | “Any occupied, low-confidence, stale or interrupted sequence blocks the simulated power action. We require a sustained fresh vacancy window, a schedule and override check, and a fresh authorized approval. A new frame invalidates a pending proposal.” | Policy |
| 5 | Can the model open overflow or turn off a room? | “The model stages proposals. Role-checked staff approve the current version. Server rules recheck constraints and commit the mock state and audit entry together.” | API |
| 6 | What happens when overflow expires and a car is still there? | “Its bay still counts as occupied until a verified exit. Expiry closes new allocations and releases unused holds. Gate events are idempotent, so duplicate exits do not create extra capacity.” | Policy |
| 7 | What keeps the allocation fair? | “Vehicle class, policy eligibility and reserved spaces are hard constraints. We use first valid arrival among equally eligible requests. Staff can review exceptions and the log records the rule used.” | Policy |
| 8 | Which part will actually be ready by the final? | “One gate, one temporary bay, one classroom and one schedule change. First we prove the model lookup, approved action and readback. We harden the occupancy race and duplicate events before adding a catalog or LEDs.” | Demo |
| 9 | How will you prove impact without real campus data? | “First we replay the same synthetic incidents with manual, structured-rules and agent-assisted workflows. We report resolution time, verified actions and invalid actions blocked, with sample size. That tests the mechanism. It does not measure adoption or real savings.” | Evaluation |
| 10 | Is the demo live and how does it handle model failure? | “We’ll identify exactly which parts are live and which inputs are synthetic. A model timeout falls back to staff-entered structured facts using the same validation and approval. We’ll disclose the fallback and the actual PoC status.” | Demo |

### Five reserve questions

| Question | Short answer |
| --- | --- |
| Is any personal data retained? | Only synthetic IDs, counts, confidence, timestamps and evidence references. The prototype discards frames and uses no plates, faces or campus records. |
| What if the parking approval succeeds but the room approval fails? | The parking write is independently verified. The room remains held or pending, so the incident shows both outcomes without falsely closing. |
| What is the latency budget? | Bound model calls and retries, use indexed local reads and measure event-to-proposal and approval-to-verification on the tested configuration. Report actual observed timings. |
| Can this scale? | Preserve one incident identifier and branch records, define policies per zone and room, and add adapters after validating privacy and authority. The prototype uses one local worker and SQLite. |
| Why include sports equipment and library resources? | They demonstrate the same availability interface with sample records. The core demo focuses on the two outcomes affected by one late session change. |
