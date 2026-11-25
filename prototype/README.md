# CampusFlow

The local MARTIAN 1.0 Checkpoint Beta interface for CampusFlow. One revised lab session creates two independently approved and verified actions at Gate A and classroom C-101.

## Run locally

From the MARTIAN workspace root:

```sh
python3 -m venv prototype/.venv
source prototype/.venv/bin/activate
python -m pip install -r prototype/requirements.txt
python -m uvicorn --app-dir prototype app:app --host 127.0.0.1 --port 8765
```

Open [CampusFlow on localhost](http://127.0.0.1:8765/). With the listed dependencies already installed, the Uvicorn command can run directly. The browser and application assets load locally. The default database is created in a temporary directory for the server process. To persist a demo between process restarts, set `CAMPUSFLOW_DB` to a writable file. **Reset demo** restores the fixture and clears the current run's sample audit.

Start a fresh server after changing FastAPI routes. If port 8765 is already occupied, use `--port 8766` and open [localhost:8766](http://127.0.0.1:8766/).

## Dashboards

| Route | Sections |
| --- | --- |
| `/` | Landing page with direct links to both dashboards |
| `/fleet` | Parking overview, Campus map, Gate ledger, Overflow approvals |
| `/resources` | Rooms & devices, Labs, Library seats, Sports equipment |

The fleet map shows the BMSITM Gate A approach, the main bike and car lots, and Bike Zone 2. The parking counters and actions use the smaller synthetic bay set in the incident. Both dashboards read the same incident and decision audit.

### Optional model intake

Set `GEMINI_API_KEY` and `CAMPUSFLOW_GEMINI_MODEL` in the server environment using a team-approved credential and a Gemini model that supports Interactions API function calling. For example, with the secret already supplied by your environment:

```sh
export CAMPUSFLOW_GEMINI_MODEL="<team-validated-model-id>"
python -m uvicorn --app-dir prototype app:app --host 127.0.0.1 --port 8765
```

Use **Run agent** after the note arrives. The server sends the fixed synthetic note and permits a single timetable lookup or clarification. A missing credential uses **Confirm timetable lookup**. A provider timeout or invalid reply prompts **Confirm synthetic schedule**. The local demo and application tests used structured intake. Live provider execution is unverified. [Gemini function calling](https://ai.google.dev/gemini-api/docs/function-calling)

## Present

1. Open **Vehicle Fleet Management**, trigger the schedule change and confirm the timetable lookup.
2. Approve overflow, confirm the regular car exit and open the resource view.
3. Inject the occupied reading and show the room safety hold.
4. Recheck sustained vacancy and approve standby with the fresh facilities proposal.
5. Open the decision audit. Reset before the next run.

[75-second script and fallback assets](../presentation/DEMO_STORYBOARD.md) · [Verification report](../evaluation/PROTOTYPE_VERIFICATION.md)

## Capabilities and scope

| Capability | State |
| --- | --- |
| Vehicle Fleet Management | Implemented parking overview, a campus parking map, gate ledger and overflow approvals. Class-based assignments, protected capacity, expiry, idempotent exits and transactional readback run on sample data. |
| College Resource Allocation | Implemented room/device, lab, library-seat and sports-equipment views. Room counts, lab states and library seating are fixtures. One sports kit supports mock checkout and return. |
| Agent coordination | Implemented evidence, planning, permissioned action, readback, explainability and room recovery. The optional model is limited to selecting an intake tool. |
| Approval and safety | Implemented independent proposal IDs and version checks. The presenter plays simulated staff roles in a single localhost workspace. Device writes are confined to SQLite. |
| Current limits | One schedule change and fixed synthetic inputs. Library capacity is a snapshot. Room control covers the one approval and readback sequence. Staff authentication, streaming occupancy, automatic power restoration and live campus integration are future work. |

## Verify

```sh
python -m pip install -r prototype/requirements-dev.txt
python -m unittest discover -s prototype -v
node --check prototype/static/app.js
```

## Tools and attribution

Original CampusFlow prototype implementation for this event, assisted by OpenAI Codex. The runtime uses Python and its SQLite module, FastAPI (MIT), Pydantic (MIT), and Uvicorn (BSD 3-Clause). HTTPX (BSD 3-Clause) is a development test dependency. The browser UI uses vanilla HTML, CSS and JavaScript, local system fonts, and the BMSITM crest from the team-supplied lockup. Optional model provider is Google's Gemini API. The presentation screenshots were captured in the Codex in-app browser and the diagram exports use Pillow (HPND). Record team members and their actual contributions in the event submission.

The team-supplied parking screenshot matches the base floorplan in the [existing parking simulation](../presentation/campusflow_parking_sim.html). The frontend uses a WebP export of that base map. Pillow was used to prepare the local image assets and CampusFlow mark. The [illustrative reading-room photograph](static/resource-library.webp) was created with built-in OpenAI ImageGen.

> Create a premium landscape editorial architectural photograph for a college resource dashboard. Interior of a contemporary university reading room in Bengaluru: long natural oak communal tables, aligned chairs, warm cream concrete columns, floor-to-ceiling windows with tasteful horizontal fins, soft sunlight and subtle long shadows, muted greenery outside. Sightline along the tables, centered visual focal point; leave a composition that also works in a center portrait crop. Pale oak, dusty warm ivory, olive hints, elegant believable materials, real architectural magazine photography, calm and uncluttered. Wide landscape canvas, full bleed, no people, typography, logos, watermark or interface.

[Architecture and final-round roadmap](../solution/PROTOTYPE_DESIGN.md) · [Diagrams](../solution/CAMPUSFLOW_DIAGRAMS.md)
