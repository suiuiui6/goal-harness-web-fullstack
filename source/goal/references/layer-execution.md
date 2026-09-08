# Layer Execution

## Classification

Classification values and state phases must agree with the normative
`references/protocol.json` contract. This guide retains the meanings of Layers
0 through 6; it does not redefine protocol owners, transitions, or records.

| Situation | Mode | Start Layer |
|---|---|---:|
| New system, architecture rebuild, or core replacement | `bootstrap` | `0` |
| Data-flow or topology change in an existing system | `maintenance` | `2` |
| External framework or deployment shift | `maintenance` | `3` |
| New major feature flow across multiple layers | `maintenance` | `4` |
| Engineering-rule drift | `maintenance` | `5` |
| Local implementation bug under stable contracts | `maintenance` | `6` |

Bootstrap confirmation is required. For maintenance, explicit confirmation is preferred when the classification is surprising or the rollback target reopens earlier layers.

## Provisional classification evidence

When the mode or start layer is ambiguous, before formal confirmation perform a provisional classification evidence check that is minimal and read-only. Inspect only existing evidence needed to resolve the ambiguity. Do not load Harness execution runtime, do not mutate project or goal state, and do not treat the provisional result as a confirmed classification.

## Per-layer loop

1. STATE: read upstream artifacts and current evidence.
2. PLAN: define the next bounded action for this layer.
3. EXECUTE: do the work for this layer only.
4. GATE: record pass or rollback with concrete evidence.

## Gate record

```text
Layer [N]: [PASS/FAIL]
Evidence: [artifact, command, or inspection result]
Decision: [advance / rollback to Layer X]
If rollback: [invalid assumption + rationale]
```
