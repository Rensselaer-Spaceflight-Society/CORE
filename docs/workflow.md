# Team workflow

![Team workflow](visuals/team-workflow.svg)

**One issue → one owner → a reviewable result → a second-person review.**

```mermaid
flowchart LR
    A[Pick a task] --> B[Confirm inputs and owner]
    B --> C[Calculate or design]
    C --> D[Test and explain the result]
    D --> E[Open a pull request]
    E --> F{Second review complete?}
    F -->|Changes needed| C
    F -->|Yes| G[Merge reviewed change]
    G --> H[Update dependent components]
```

At the weekly meeting, each component owner gives three facts: what changed, what evidence supports it, and what input or decision is needed next. When an upstream number changes, downstream owners repeat the affected checks.

## A software merge is not a part release

```mermaid
flowchart LR
    A[Merged model and CAD] --> B[Check limits and evidence]
    B --> C{Part-specific review complete?}
    C -->|No| D[Resolve open engineering tasks]
    D --> B
    C -->|Yes| E[Approve revision and drawings]
    E --> F[Shop confirms process and inspection]
    F --> G[Manufacture that approved part]
```

The engine-level release check is blocked. A non-running fixture or coupon can have a narrower review package; that does not release a rotor, hot section or complete engine.

## Meeting agenda · 30 minutes

| Minutes | Topic | Leave with |
|---|---|---|
| 0–5 | Mission and December outcome | Definition of first manufactured parts |
| 5–10 | Engine path and design order | Agreed interfaces |
| 10–20 | Combustion, rotating assembly, controls/test readiness | Top blockers and evidence needed |
| 20–27 | Assign this week's tasks | Owner, reviewer and acceptance criterion |
| 27–30 | Confirm next review | Date and required deliverables |
