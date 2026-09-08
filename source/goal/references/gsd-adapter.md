# GSD Layer 6 Adapter

Use this adapter only for a GSD proposal at Layer 6 after Goal classification and Harness approval. Do not infer GSD activation from a mention.

## Ownership and Activation

- Goal owns GSD activation and routing.
- `/goal` remains the unique project entry.
- Harness owns Layer 6 approval, gates, rollback, closure, and receipt approval.
- `gsd-plan-phase`, `gsd-execute-phase`, and `gsd-verify-work` are subordinate Layer 6 tools only.

## Execution Boundary

- Required operation order is `plan-phase -> execute-phase -> verify-work`.
- Receipt checks are mandatory before advancing to the next GSD operation.
- GSD must not change goal state, start_layer, or Harness pass/fail decisions.
- Layer 4 planning remains forbidden for GSD in this integration.
- `gsd-autonomous` and any autonomous execution surface remain forbidden unless the user separately approves them.
- Project-scoped GSD pilot activation additionally requires `<project>\.codex\gsd-layer6-pilot.local.json` and explicit Harness Layer 6 approval.
- If the previous pilot cleanup was blocked or drift was preserved, do not reactivate GSD until cleanup evidence is repaired and re-verified.
- If GSD is missing, disabled, invalid, or blocked, fall back to the original non-GSD `/goal` + Harness Layer 6 path.
- On Windows, describe host behavior as `audit-only-windows`; do not claim mechanical blocking when hooks are unavailable.
