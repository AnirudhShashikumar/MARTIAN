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

## Deploy on Vercel

1. Import this Git repository into Vercel and set the **Root Directory** to the repository root. The configuration uses the FastAPI preset, Python 3.12, and `server.py`. Leave the build, install and output overrides at their defaults. [FastAPI on Vercel](https://vercel.com/docs/frameworks/backend/fastapi)
2. Connect a dedicated Supabase PostgreSQL database through Vercel Storage. CampusFlow accepts the integration’s `POSTGRES_URL` and gives an explicit `DATABASE_URL` precedence. For a manual connection, save the Supabase **transaction pooler** URI with TLS as a server-side `DATABASE_URL` secret. Use a separate preview database or branch. The database role must own CampusFlow’s session table so it can create the table, index and row-level security on first use. [Supabase Vercel integration](https://supabase.com/docs/guides/integrations/vercel-marketplace) · [Supabase connection strings](https://supabase.com/docs/guides/database/connecting-to-postgres)
3. Deploy a Preview and check `/api/health` for `{"status":"ok"}`. Open the landing page and complete the parking and room approval flow across both dashboards. Open a private browser window to confirm that it starts with a separate run. Promote the preview after the checks pass.

The hosted demo stores synthetic state and audit events in PostgreSQL. The browser keeps an HTTP-only HTTPS session cookie. Each session lasts 24 hours. Expired sessions are removed as new sessions start. The local Uvicorn demo uses its existing SQLite store.

After changing Vercel environment variables, redeploy the affected environment. The public health endpoint reports HTTP 503 until a deployment has a working connection. [Vercel environment variables](https://vercel.com/docs/environment-variables/managing-environment-variables)

The live AMB82 serial bridge, Android WebSocket panel, and classroom console run on the private local server. The hosted room URLs link visitors to the simulated facilities dashboard.

Structured intake is the hosted default. On a protected deployment with team-approved model access, set `CAMPUSFLOW_ENABLE_HOSTED_MODEL=1`, `GEMINI_API_KEY`, and `CAMPUSFLOW_GEMINI_MODEL` in Vercel. Use [the environment template](../.env.example) as a reference.

For local Vercel verification, export the URL for a disposable PostgreSQL database as `DATABASE_URL` and run from the repository root:

```sh
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
VERCEL_ENV=development npx vercel dev --local --listen 127.0.0.1:8888
```

Use a fresh browser session at [localhost:8888](http://127.0.0.1:8888/). Set `CAMPUSFLOW_TEST_DATABASE_URL` to a disposable PostgreSQL database URL before running the test suite to exercise durability, session isolation, concurrent approvals, and rollback.

## Dashboards

| Route | Sections |
| --- | --- |
| `/` | Landing page with direct links to both dashboards |
| `/fleet` | Parking overview, Campus map, Gate ledger, Overflow approvals |
| `/resources` | Rooms & devices, Labs, Library seats, Sports equipment |

The fleet map shows the BMSITM Gate A approach, the main bike and car lots, and Bike Zone 2. The parking counters and actions use the smaller synthetic bay set in the incident. Both dashboards read the same incident and decision audit.

### Gate A camera demo

Open **Vehicle Fleet → Parking overview** and select **Play footage**. The default 32.5-second reel combines three real clips. Reviewed YOLOX vehicle tracks identify the crossing evidence. Each crossing uses the video clock to trigger an animated car or motorcycle and a policy decision on the campus map. The example uses anonymous track IDs and a seeded parking ledger. The car lot starts full so the first arrival exercises the overflow reserve.

| Real reel time | Map action |
| --- | --- |
| `0:07.80` | A car crosses the driveway gate. The agent routes it to overflow bay `OC-01`. |
| `0:21.15` | A motorcycle enters the garage access aisle. The agent allocates `B-08`. |
| `0:27.00` | A car leaves the garage approach and releases `C-01`. |
| `0:31.35` | A motorcycle crosses the exit path and releases `B-01`. |

The video combines Taryn Elliott’s [car gate arrival](https://www.pexels.com/video/a-car-entering-the-gates-of-a-property-onward-to-its-driveway-3782429/), Michele Lazzari’s [motorcycle garage approach](https://www.pexels.com/video/motorcycle-rider-in-underground-parking-lot-31901416/), and Ivan Chumak’s [mixed garage exit](https://www.pexels.com/video/urban-parking-scene-with-cars-and-motorbike-37508953/) under the [Pexels license](https://www.pexels.com/license/). Faces and plate regions in the garage cuts are masked. The car approach uses an overhead angle. Crossing times were reviewed against the cut and the [OpenCV Zoo YOLOX model](https://github.com/opencv/opencv_zoo/tree/main/models/object_detection_yolox) detections. The real reel plays reviewed tracks, and the parking engine applies its policy as the video plays.

Select **Synthetic model test** in the camera feed picker and press **Play & analyze** for fresh inference. The 5:30 synthetic clip uses a fitted car/motorcycle classifier and a separate registration glyph recognizer on browser video pixels. Direction comes from crossing both sides of the calibrated gate line. The registration model requires repeated agreeing readings. Both feeds work offline with no API key and offer CSV export.

| Clip time | What to show |
| --- | --- |
| `0:06` and `0:14` | A car and a motorbike fill the last general bays for their respective classes. |
| `0:22` and `0:30` | Both vehicle classes reach capacity and use their designated overflow reserve. |
| `0:46` and `0:54` | A car waits when its overflow reserve is also full. After a confirmed departure, the agent assigns the freed bay to the waiting registration. |
| `1:10` through `1:26` | A duplicate entry, an unreadable plate, and an exit with no matching bay are held for staff review. |

Use **Jump to** to replay events from verified model observations. Use **Run models from start** to return to fresh browser inference. The camera exercise uses a separate synthetic ledger. **Shared incident** links to the incident involving parking and C-101. Automatic overflow uses marked reserve bays. Accessible and reserved bays are outside the automatic allocation pool.

The fixture tests matched all 32 crossings at both 8 and 5 samples per second, including 31 exact registrations and one unreadable plate. The classifier matched 120 held-out synthetic sprite variants. These measurements describe this calibrated clip and its synthetic assets. The models target the clip’s fixed lanes and test plate font.

OpenPK provides 5-minute parking scenes with plates intentionally unidentifiable. The 5:17 Wikimedia clip demonstrates camera zoom. The selected real reel prioritizes visible gate movements in both directions. The longer test sequence provides reproducible registrations and controlled overflow. [OpenPK parking dataset](https://github.com/ciprianiacobescu/OpenPK) · [Wikimedia camera demonstration](https://commons.wikimedia.org/wiki/File:BLK-HDPTZ12_Security_Camera_Parkng_Lot_Surveillance_Video.webm)

The clip contains adapted CC0 **Tiny Cars** sprites by RooMan93 and **Bikes** sprites by Mark Ainsworth (mainsworthy, ref. 210665). The camera scene and sample registrations were created for CampusFlow. Local build tools are Pillow, NumPy and FFmpeg through `imageio-ffmpeg`. [Tiny Cars](https://opengameart.org/content/tiny-cars-0) · [Bikes](https://opengameart.org/content/bikes)

To rebuild and verify the camera assets from the repository root with Node.js and those Python packages available:

```sh
python simulation/build_gate_clip.py
FFMPEG="$(python -c 'from imageio_ffmpeg import get_ffmpeg_exe; print(get_ffmpeg_exe())')" node simulation/verify_gate_clip.mjs --write
```

The real reel builder also uses OpenCV. Download the three credited originals to an external directory and name them `car-entry.mp4`, `bike-aisle.mp4`, and `mixed.mp4`. Pass that directory and the official YOLOX ONNX weights to `python simulation/build_real_gate_reel.py`. Only the privacy-edited output and anonymous evidence belong in the project.

### Local resource workflows

Open `/resources?section=labs`, `/resources?section=library`, or `/resources?section=equipment` on the local server. Each tab uses its own sample ledger and decision trace. **Reset demo** restores the resources fixture along with the current incident. Set `CAMPUSFLOW_DB` to a writable path to retain the run across restarts.

1. **Labs.** Use the prefilled 24-person Lab 2 request. The timetable shows why that slot is blocked. Approve the first alternative, then try rescheduling or canceling as the simulated lab coordinator.
2. **Library seats.** Hold Q10 as `DEMO-01`. Choose `DEMO-02`, enable the waitlist and submit for the same window. Release Q10 or advance the demo clock by ten minutes. The agent assigns the seat to `DEMO-02`, who can check in directly. To switch a general booking, request a protected seat as the same requester for the remaining window and approve it as library staff.
3. **Sports equipment.** Reserve two rackets and confirm pickup. Return one in good condition and report the other damaged. The item ledger shows the second racket under inspection until the sports desk clears it.

Every confirmed effect is rechecked against the latest ledger, written transactionally and verified by SQLite readback. The model, when configured locally, interprets synthetic notes through a read-only tool. You can exercise it from **Interpret a synthetic note** using **Use example**. The form provides the complete workflow offline. Staff roles and sample data simulate campus operations.

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
| College Resource Allocation | Implemented room/device views and local lab booking, library seats and sports equipment workflows. Synthetic requests support role-aware approval, concurrency checks, SQLite readback and a per-tab trace. |
| Agent coordination | Implemented evidence, planning, permissioned action, readback, explainability and room recovery. The optional model is limited to selecting an intake tool. |
| Approval and safety | Implemented independent proposal IDs and version checks. The presenter plays simulated staff roles. Simulated device writes go to SQLite locally and per-browser PostgreSQL state on Vercel. |
| Current limits | The shared incident uses one schedule change. Resource workflows use a synthetic catalog and demo clock. Room control covers the one approval and readback sequence. Staff authentication, automated power restoration and campus integration are future work. |

## Verify

```sh
python -m pip install -r prototype/requirements-dev.txt
python -m unittest discover -s prototype -v
node --check prototype/static/app.js
```

## Tools and attribution

Original CampusFlow prototype implementation for this event, assisted by OpenAI Codex. The runtime uses Python and its SQLite module, FastAPI (MIT), Pydantic (MIT), and Uvicorn (BSD 3-Clause). HTTPX (BSD 3-Clause) is a development test dependency. The browser UI uses vanilla HTML, CSS and JavaScript, local system fonts, and the BMSITM crest from the team-supplied lockup. Optional model provider is Google's Gemini API. The presentation screenshots were captured in the Codex in-app browser and the diagram exports use Pillow (HPND). Record team members and their actual contributions in the event submission.

The hosted simulation uses Vercel Functions and PostgreSQL through Psycopg (LGPL-3.0).

The team-supplied parking screenshot matches the base floorplan in the [existing parking simulation](../presentation/campusflow_parking_sim.html). The frontend uses a WebP export of that base map. Pillow was used to prepare the local image assets and CampusFlow mark. The [illustrative reading-room photograph](static/resource-library.webp) was created with built-in OpenAI ImageGen.

The landing page uses two illustrative photographs under the [Pexels License](https://www.pexels.com/license/). Both are served locally as responsive WebP variants.

- **Mobility** uses Joshua Santos’s parking aerial, published March 16, 2022. Its tree-lined parking aisles remain recognizable in a wide crop. [Drone Shot of a Parking Lot](https://www.pexels.com/photo/drone-shot-of-a-parking-lot-11502892/)
- **Facilities** uses Grisha Grishkoff’s reading hall, published June 8, 2020. The crop retains the communal desks and geometric ceiling. [Empty reading hall in library in daytime](https://www.pexels.com/photo/empty-reading-hall-in-library-in-daytime-4593942/)

> Create a premium landscape editorial architectural photograph for a college resource dashboard. Interior of a contemporary university reading room in Bengaluru: long natural oak communal tables, aligned chairs, warm cream concrete columns, floor-to-ceiling windows with tasteful horizontal fins, soft sunlight and subtle long shadows, muted greenery outside. Sightline along the tables, centered visual focal point; leave a composition that also works in a center portrait crop. Pale oak, dusty warm ivory, olive hints, elegant believable materials, real architectural magazine photography, calm and uncluttered. Wide landscape canvas, full bleed, no people, typography, logos, watermark or interface.

[Architecture and final-round roadmap](../solution/PROTOTYPE_DESIGN.md) · [Diagrams](../solution/CAMPUSFLOW_DIAGRAMS.md)
