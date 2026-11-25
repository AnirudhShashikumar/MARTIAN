# CampusFlow technical diagrams

The prototype diagrams describe the local implementation. The final-product diagram describes proposed components. The browser captures and slide-ready exports are indexed in the [demonstration storyboard](../presentation/DEMO_STORYBOARD.md).

## 1. High-level system architecture

**Local presentation prototype**

```mermaid
flowchart LR
    F["Synthetic inputs<br/>Staff note · gate events · room counts"] --> A["FastAPI<br/>One incident coordinator"]
    U["Local browser<br/>Fleet and resource views"] <-->|"Same-origin commands & state"| A
    A -. "Optional read-tool selection<br/>Fixed sample note" .-> M["Gemini API"]
    M -. "Validated tool name & session ID" .-> A
    A --> P["Typed policy<br/>Eligibility · capacity · freshness · versions"]
    P --> H["Simulated role approval<br/>Parking or facilities"]
    H --> D["SQLite<br/>Mock state + audit"]
    D --> V["Transaction readback<br/>Bay or device state"]
    V --> U
```

**Proposed final product**

```mermaid
flowchart LR
    A["Approved timetable and gate adapters"] --> I["Normalized event ingestion"]
    E["Edge occupancy aggregates"] --> I
    I --> C["Incident coordinator<br/>Typed tools and model interpretation"]
    R["Campus identity & scoped staff roles"] --> P["Policy, approval and revision checks"]
    C --> P
    P --> D["Operations store<br/>Incident versions, audit and outbox"]
    D --> L["Approved adapter dispatch"]
    L --> V["Device or allocation acknowledgment<br/>Reconcile or escalate"]
    V --> D
    D --> U["Operator workspace"]
```

## 2. Agentic workflow

```mermaid
flowchart LR
    S["Sense<br/>Note, arrivals and room counts"] --> T["Think<br/>Resolve revised timetable"]
    T --> P["Plan<br/>Calculate two policy-valid proposals"]
    P --> A["Act<br/>Route to each staff role"]
    A --> V["Verify<br/>Recheck evidence and read back state"]
    V --> E["Explain<br/>Evidence, actor, result and next owner"]
    V -->|"Room evidence changed"| R["Adapt<br/>Invalidate room token and hold"]
    R -->|"Fresh sustained vacancy"| P
    R -->|"Uncertain conditions"| H["Facilities review"]
```

## 3. Data flow

```mermaid
flowchart LR
    N["Staff note and simulated clock"] --> S["Timetable record TT-018"]
    G["Gate event ID, time, vehicle class"] --> F["Eligible bays and arrival order"]
    O["Room count, confidence and capture time"] --> R["Vacancy, booking and override guard"]
    S --> F
    S --> R
    F --> P["Parking proposal + evidence revision"]
    R --> C["Room proposal + evidence revision"]
    P --> T["Approval transaction<br/>Role + token + fresh guards"]
    C --> T
    T --> D["SQLite state write + verification + audit"]
    D --> U["Two operational views and incident summary"]
```

## 4. Agent tools and authority

```mermaid
flowchart TD
    I["Ambiguous synthetic note"] --> M{"Intake mode"}
    M -->|"Configured"| G["Gemini returns one tool selection"]
    M -->|"Offline"| H["Operator confirms sample session"]
    G --> A{"Validate tool and arguments"}
    A -->|"lookup_session + LAB-IND-04"| T["Read canonical timetable"]
    A -->|"Clarification, timeout or invalid"| H
    H --> T
    T --> B["Server reads bay, gate and occupancy state"]
    B --> P["Policy stages pending decisions"]
    P --> W["Role-authorized write and readback"]
```

## 5. Human decision flow

```mermaid
flowchart TD
    P["Proposal with evidence revision"] --> U{"Simulated designated role replies"}
    U -->|"Decline"| E["Staff review recorded"]
    U -->|"Approve"| V{"Matching role and token?<br/>Current evidence valid?"}
    V -->|"Invalid or changed"| H["Hold the affected branch<br/>Require fresh proposal"]
    V -->|"Valid"| A["Apply mock state update"]
    A --> R{"Readback confirms?"}
    R -->|"Yes"| D["Commit action and audit together"]
    R -->|"No"| X["Rollback and signal staff review"]
```

## 6. End-to-end scenario sequence

```mermaid
sequenceDiagram
    participant O as Demo operator
    participant C as CampusFlow
    participant T as Timetable
    participant P as Parking attendant
    participant F as Facilities supervisor
    participant D as SQLite mock state
    O->>C: Inject late move, two arrivals
    C->>T: Read canonical revised session
    T-->>C: TT-018 · Lab 2 · 14:20–15:05
    C->>D: Assign regular bike and stage both proposals
    C->>P: Request temporary OV-01 approval
    P->>C: Approve current parking proposal
    C->>D: Assign CAR-078 and read back bay + gate
    O->>C: Confirm regular car exit
    C->>D: Release C-01
    C->>F: Request C-101 standby approval
    O->>C: Inject fresh count of one
    C->>D: Revoke room proposal · parking stays verified
    O->>C: Supply new continuous vacancy sequence
    C->>F: Request fresh approval
    F->>C: Approve current room proposal
    C->>D: Apply and read back mock device state
    C-->>O: Both outcomes and blocked proposal in audit
```
