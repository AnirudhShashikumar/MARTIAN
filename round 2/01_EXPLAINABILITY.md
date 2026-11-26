# Criterion 1: Explainability (25 / 25 Marks)

> **Exemplary Rubric Bar (20–25 Marks):** *Transparent agent reasoning; provides human-interpretable logs, feature attribution, or confidence scores; zero black-box obscurity.*

---

## 1. Core Design Philosophy: Zero Black-Box Autonomy

Most AI prototypes fail operational trust because a neural network silently emits a binary command (`TURN OFF`, `OPEN GATE`) with no explanation of *why*, *how confident it was*, or *what alternatives were ruled out*.

CampusFlow enforces a **Glass-Box Agentic Architecture** across both pillars (`/fleet` and `/resources`):

1. **Every perception event exposes visual + numeric evidence** (bounding boxes, detection confidence, OCR confidence, person count, frame timestamp, hold timer countdown).
2. **Every policy decision is deterministic, auditable, and states what was ruled out** (e.g., *"Bike Lot ruled out — wrong vehicle class"*, *"Accessible ♿ bays preserved"*, *"Duplicate scan blocked — already in live DB"*).
3. **High-consequence actions require explicit Human-in-the-Loop (HITL) sign-off** (Attendant Overflow Approval on `/fleet`; manual Override Switch and role-checked facility reviews on `/resources`).
4. **Every state mutation closes with readback verification** — the agent never assumes an action succeeded until it confirms the updated ledger state.

---

## 2. How Explainability Is Implemented in Code

### A. Vehicle Fleet Management (`/fleet` — `prototype/static/fleet.html` & `prototype/fleet_vision.py`)

| Explainability Layer | Exact Implementation | What Operators & Judges See |
| :--- | :--- | :--- |
| **4-Step Live AI Decision Trace** | `#paneLoop` (`1 · Sense` → `2 · Think` → `3 · Act` → `4 · Explain & Verify`) | Plain-English causal chain updated on every single arrival, exit, overflow, redirect, and blocked duplicate. |
| **Feature Attribution & Scoring** | `fleet_vision.py` foreground scorer: `rel_area * conf * cy_bias * cx_bias` + `score_plate_candidate()` | Locks onto the primary foreground vehicle instead of distant background traffic; outputs `confidence`, `ocr_confidence`, `detected_at_sec`, and `plate_recognized`. |
| **Counterfactual Audit Log** | `#paneAudit` (`Time`, `Event`, `Why / Ruled Out`, `Result`) | Explicitly records **why** an option was chosen and **which alternatives were ruled out** (e.g., `Car lot 30/30 full; Bike ruled out` → `Awaiting Approval`). |
| **Live Physical Feedback** | `SIGN_JUNCTION` dynamic signboard + animated SVG route overlays + `#storyPill` | Real-time status banner showing exact transitions (`Scanning clip…` → `Detected Car (K8701KN) at 1.3s — spawning in 1.7s…` → `routed right to Car bay C-B07`). |
| **Guardrail Attribution** | `demo3DuplicateScan` / duplicate check in `addCar()` & `addBike()` | Turns the Act card red (`s-guard`), flashes `CAM-1`, blocks double allocation, and explains: *"Capacity count protected against scanner bounce or duplicate read."* |
| **Persistent State Inspection** | `#paneDb` (`Parked (DB)`) backed by `campusflow_parking_db_v3` | Every vehicle plate, bay ID, zone, and entry timestamp is inspectable and individually releasable with one click. |

### B. Classroom Resource Management (`/resources` — `prototype/cctv_stream.py` & `prototype/static/app.js`)

| Explainability Layer | Exact Implementation | What Operators & Judges See |
| :--- | :--- | :--- |
| **Live Visual Attribution** | `results[0].plot()` in `_infer_loop()` streamed over `/api/cctv/stream` | Live YOLOv8n **person bounding boxes + per-box confidence scores** overlaid directly on the video feed inside the web app, alongside a live status badge (`OCCUPIED (1) ON`, `AUTO-OFF 2.4s`, `CLASS EMPTY`). |
| **Live Telemetry Metrics** | `GET /api/cctv/status` → `#cctv-meta` | Displays exact `person_count`, `confidence`, `infer_ms`, `fps`, `hold_remaining`, and `lights_on` in real time (polled every `500ms`). |
| **Debounced State Transparency** | `DebouncedOccupancy` (`hold_seconds = 3.0`) | When a student leaves the frame while lights are ON, the UI explicitly shows the live countdown: *"Person left frame — turning lights off in 2.4s…"* instead of abruptly cutting power. |
| **Human-Centric Rule Clarity** | No Auto-ON / Auto-OFF policy | If a student sits in a dark room (`count > 0`, `lights_on = False`), the banner clearly explains: *"Person detected — Lights Off (no auto turn-on; use Override to turn ON)"*. |
| **Chronological Incident Log** | `self._events` (RAM-only ring buffer) rendered in `#activity` with **Clear** control | Logs every state change with timestamp, stage badge (`CCTV`, `Occupied`, `Override`, `Auto-Off`, `Empty`), title, and causal detail (e.g., *"Student left for 3.0s; sent /disabletorch to Sanjana & Ani"*). |

### C. LLM Tool-Use & Policy Explainability (`prototype/agent.py`, `prototype/scenario.py`, `prototype/resources.py`)
- **Allowlisted Tool Schema (`agent.py`):** When Gemini is enabled via the Interactions API, the model is strictly restricted to **read-only** tool selection (`lookup_session` or `request_clarification`) with `store: False`. `validate_selection()` rejects any unknown tool or hallucinated argument and safely degrades to structured human confirmation (`clarification(...)`).
- **Explainable Refusals in Shared Resources (`resources.py`):** Lab bookings show *why* a room is blocked (existing timetable conflict), Library seats explain FIFO waitlist promotions and protected-seat rules, and Sports equipment explicitly separates damaged items under inspection from available stock.
- **Transactional Audit Trail (`Store.apply` & `PostgresStore`):** Every command writes an immutable audit entry recording `stage`, `time`, `title`, and `detail`, and rolls back if readback verification fails.

---

## 3. What to Remember & Tell the Judges

### 30-Second Verbal Pitch for Explainability
> *"CampusFlow has zero black-box actions. Every vision decision shows the exact YOLO bounding boxes, confidence score, and hold countdown live in the browser; every parking decision exposes a 4-step Sense-Think-Act-Verify card and a 'Why / Ruled Out' audit log; and whenever a decision crosses a safety boundary — like opening external car overflow or turning off a classroom — our agent either asks a human attendant for sign-off or shows a transparent 3-second countdown before acting."*

### 3 Live Demo Proof Points (Show These on Screen!)
1. **On `/fleet`:** Click **Load Clip** → point to the `#storyPill` live countdown, then point to the **AI Decision** 4-step cards and click the **Audit** tab to show the `Why / Ruled Out` column.
2. **On `/fleet`:** Click **Demo 3 (Test Duplicate Scan Guard)** → show the red guardrail card blocking a double entry with an explicit reason instead of corrupting the bay count.
3. **On `/resources`:** Show the **live YOLOv8 bounding boxes**, toggle the **Override switch**, step out of frame to show the **3.0s Auto-OFF countdown**, and point to the right-side **Incident Log** recording every exact transition.

### Likely Judge Questions & Winning Answers
- **Q: "What if your YOLO model misclassifies a shadow or loses a student for 1 second?"**  
  **A:** Two layers protect users: (1) our `DebouncedOccupancy` requires `3.0s` of continuous zero-person readings before Auto-OFF triggers, and visibly displays the countdown; (2) we never auto-turn lights ON, and any person can override power immediately via the single **Override switch**, which logs the event transparently.
- **Q: "Can an LLM hallucinate a command and turn off an occupied classroom or open overflow without approval?"**  
  **A:** **Impossible by construction.** In `prototype/agent.py`, the LLM only has read-only tools (`lookup_session` / `request_clarification`). Deterministic Python policy code enforces all state transitions, role checks, and readback verification.
- **Q: "Why didn't you save CCTV footage for your audit trail?"**  
  **A:** **Privacy-by-design.** We keep full explainability through structured telemetry (timestamps, counts, confidence scores, policy reasons) while keeping all video frames strictly in RAM (`del frame, results, annotated`) so zero student faces or license-plate recordings are ever written to disk.
