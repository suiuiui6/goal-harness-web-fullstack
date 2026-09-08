# Conditional Decision Quality

This reference defines Harness's conditional first-principles and adversarial-review protocol. It is a cold-path control: load it when a risk check identifies a trigger or when a decision-quality gate is being evaluated. It is evidence for a decision, not an always-on prompt ritual.

## Ownership and skip rule

Harness owns the risk check, evidence requirements, layer gates, rollback decision, `scope_result`, and `operation_state`. This is the mechanical/exact-plan skip rule: a change may skip this protocol only when the risk check records both that it is mechanical (formatting, generated output, or an equivalent no-behavior edit) or an exact-plan execution with no unresolved choice, and the exact skip reason. A mechanical/exact-plan skip does not bypass ordinary layer gates, validation, or closure fields.

## First-principles trigger

Activate first-principles analysis when any of these conditions is present:

- classification or start layer is ambiguous (ambiguous classification/start layer);
- documentation, code, and runtime evidence contradict one another (contradictory docs/code/runtime);
- the change affects topology, data, security, a public API, or a migration;
- a choice is costly or irreversible (costly or irreversible choices);
- a proposed implementation copies a pattern whose constraints are unknown (copying patterns with unknown constraints);
- downstream failure could invalidate an upstream assumption (downstream failure possibly invalidating upstream assumption).

When active, write the following exact compact labels (one concise line or table row per label):

- **Constraints** — non-negotiable contracts, limits, dependencies, and scope;
- **Assumptions** — facts believed true and the evidence supporting each;
- **Falsifier** — an observable condition that would disprove an assumption or decision;
- **Decision** — the selected option, its rationale, and the smallest affected layer.

Do not invent a trigger to create ceremony. If no trigger exists, record `Protocol: skipped` and the precise mechanical/exact-plan reason.

## Adversarial trigger and minimum review

Adversarial review is mandatory before a key Layer 0, Layer 3, Layer 4, or Layer 6 gate (Layers 0/3/4/6); before migrations or security, privacy, permission, financial, or public-contract changes; before accepting a happy-path/static/self-authored pass claim; when deciding whether an unexpected failure is local or requires upstream rollback; and before final closure when a high-risk assumption or unverified path remains. It may be combined with first-principles work (`Protocol: both`).

The reviewer must try to falsify the result by documenting at least three ways it may still be wrong. In the evidence record, explicitly list three ways the result may still be wrong. For each threat, name an executable probe (a test, replay, query, check, or bounded experiment), its result, and any gap. Include these threat classes where applicable:

1. a partially covered requirement or an edge case outside the demonstrated path;
2. a misleading, vacuous, or self-authored test that can pass without proving behavior;
3. an untested error, concurrency, rollback, or recovery path.

Record residual risk even when every probe passes. An unresolved or unrun **high-severity** threat forces `stay`, `rollback`, or `blocked`; it can never produce `pass`. Accepted medium- or low-risk threats must be recorded with owner, rationale, and follow-up evidence or expiry.

## Fixed evidence block

Every active review, and every explicit skip, emits this fixed block. Keep labels and result vocabulary unchanged so gates and downstream tooling can consume it. The first-principles `Falsifier` is the compact condition that could disprove the decision; serialize that condition first in `Falsifiers / probes`, followed by each executable probe, result, and gap.

```text
Decision quality:
  Trigger: [first-principles, adversarial, both, or none plus concrete trigger/skip reason]
  Protocol: first_principles|adversarial|both|skipped
  Constraints: [compact list]
  Assumptions: [compact list with evidence pointers]
  Falsifier: [compact condition that would disprove the decision]
  Falsifiers / probes: [falsifier -> executable probe -> result; include gaps]
  Decision: [selected option, rationale, and minimal affected layer]
  Result: pass|stay|rollback|blocked
  Residual risk: [accepted medium/low risk, unresolved high risk, or none]
```

Embed the `Decision quality:` wrapper and block directly in the gate or closure evidence; when the surrounding record is long, its summary must point to this block and the evidence locations. The accepted result vocabulary is exactly `pass | stay | rollback | blocked`.

## Outcomes and rollback

- `pass` means required probes ran, no high-severity threat is unresolved or unrun, and the relevant gate may advance.
- `stay` means evidence is incomplete or a threat needs repair in the current layer; do not advance.
- `rollback` means a falsified upstream assumption requires returning to the smallest affected layer. Preserve the evidence and re-verify forward only for the affected scope.
- `blocked` means the required probe or authority is unavailable, or a high-severity threat cannot be resolved safely; state the dependency and next evidence needed.

When rollback is required, choose the minimal upstream rollback: the first invalid assumption and its owning layer, not a broad reset. Harness remains authoritative for this choice and for `scope_result` and `operation_state`.

## GSD receipt relationship

An approved, complete GSD receipt may be treated as equivalent evidence for the same decision-quality checks once: this is receipt equivalence/no duplicate review. A receipt is complete only when it covers the approved operation and includes the required constraints, assumptions, probes, result, residual risk, and evidence pointers. An incomplete receipt uses the Harness protocol here.

The GSD operation allowlist is exactly: `plan-phase`, `execute-phase`, `verify-work`. There is no `gsd-review` operation and no autonomous/GSD-autonomous execution surface; no `gsd-review`/autonomous operation is allowed. Missing, disabled, invalid, version-mismatched, or blocked GSD follows and must continue the original non-GSD path; do not silently downgrade a gate or invent a substitute operation.

## Recording and host wording

Persist conclusions/checks/results/pointers only. Never persist private chain-of-thought, credentials, secrets, or unbounded raw output; summarize bounded observations and retain a secure pointer when raw material must be inspected. On Windows, describe enforcement as `audit-only-windows`: report the audit result and required follow-up, and never claim mechanical blocking when hooks are unavailable.
