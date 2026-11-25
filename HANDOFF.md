# CampusFlow Checkpoint Beta handoff

Updated November 25, 2026 at 7:58 PM IST. Git base `a0362dc`. The dashboard work is in the working tree. Check current status and rerun verification before integrating it.

## Current goal

Present one synthetic schedule change with two approved and verified outcomes. The Beta priority is to demonstrate timetable evidence selection on variable note wording. [Execution plan](strategy/ROUND_2_EXECUTION_PLAN.md)

## Verified state

- The local landing page opens Vehicle Fleet Management and College Resource Allocation. The two dashboards contain eight sections and share the incident and audit. [Run guide](prototype/README.md)
- The Fleet dashboard includes the BMSITM Gate A layout, car lot, bike lot and right-perimeter Bike Zone 2. Counters reflect the synthetic incident fixture.
- Browser verification covered all eight sections, the parking assignment and exit, the room safety hold and recovery, equipment checkout and return, the final audit and demo reset. The audit showed two verified branches and one blocked standby proposal.
- Layout checks covered 390 px, 930 px and 1440 px. Keyboard activation kept focus on the selected Campus map tab.

### Test output

```text
Ran 13 tests in 0.101s

OK
```

JavaScript syntax and `git diff --check` passed.

## Decisions and rationale

- Keep the shared FastAPI and SQLite workflow behind the redesigned UI. It already enforces independent approval and verification for each branch.
- Use the existing team floorplan as the fleet map. Use generated illustrative imagery for the resource dashboard. [Asset attribution](prototype/README.md#tools-and-attribution)

## Failed approaches

- Port 8765 was already occupied by an older CampusFlow process that still served the previous root route. A fresh process at 8766 served the new routes and supported the browser run.

## Known constraints

- The verified demo uses structured intake and one fixed timetable fixture. Live Gemini execution and the variable-note comparison still need verification.
- Alpha is recoverable from Git base `a0362dc`. The archive and copies of the worktree UI before this redesign are in `/private/tmp/campusflow-pre-redesign/` on this machine.

## Next steps

1. Record the organizer's Beta cutoff, team slot and required deliverables.
2. Add the second synthetic timetable fixture and variable-note intake, with an explicit clarification path. Run the paired evaluation before making model-performance claims.
3. Rehearse from a fresh local server and refresh the verified fallback captures. [Clock and work budget](tracking/STATUS.md)

## Open questions

Who owns each Beta workstream, and what submission deadline, format and demo duration did the organizers confirm?
