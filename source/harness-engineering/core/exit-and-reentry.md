# Exit and Re-entry Policy

## Exit Bootstrap Mode

Bootstrap mode ends only when all conditions are true:

1. Layer 6 deliverables are complete.
2. System stability meets agreed observation window.
3. Spot-check confirms docs and implementation consistency.
4. Onboarding instructions reproduce environment and core flow.

When satisfied, record bootstrap completion date in project governance docs.

## Maintenance Operating Model

## Entry Classification Before Re-entry

Classify the request before deciding whether to reopen the full method.

- Bootstrap-scale change: new project setup, core component replacement, architecture rebuild, or a net-new primary flow.
- Maintenance-scale change: localized feature work, defect repair, partial refactor, or local spec correction on a stable system.
- Default: choose maintenance mode unless current evidence shows the change breaks an upstream assumption or widens into a system-level redesign.

### Keep

- documentation as source of truth
- iterative knowledge capture
- isolated runtime and dependency lock discipline
- security and secret-hygiene checks
- role-based workflow for feature, bug, and review tasks

### Stop

- mandatory full Layer 0-6 sequence for every small change
- full blueprint rollback for isolated fixes unless systemic mismatch is found
- global document updates when change is local

### Optional

- periodic drift audits between docs and implementation

## Re-entry Decision Table

| Trigger | Re-entry Layer | Scope |
|---|---|---|
| New/replaced core component | Layer 0 | Boundary mapping + MVP for affected components |
| Data-flow/topology change | Layer 2 | Topology spec + affected bridge stages |
| External framework/deployment shift | Layer 3 | Architecture and connectivity updates |
| New major feature flow | Layer 4 | PRD/API/frontend blueprint updates |
| Engineering-discipline regression | Layer 5 | Rules realignment and enforcement |
| Large refactor | Layer 4 | Full 4->6 progression for impacted scope |

## Minimal Rollback Policy

- Roll back to the smallest layer whose assumptions failed.
- Repair and re-verify that layer's pass criteria.
- Continue forward only after verification evidence is available.
- For maintenance work, do not reopen Layer 0-6 end-to-end unless the classification changes from local change to system redesign.
