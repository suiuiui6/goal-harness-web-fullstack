# Harness Engineering Checks

This file defines mandatory checks for gate decisions, rollback discipline, and completion closure.

## 0. Workbench Baseline

Before touching a numbered layer, verify:

- isolated runtime or bounded workspace exists for the affected scope
- evidence locations for specs, logs, tests, and reviews are known
- execution record destination is prepared
- secret template exists and real secret files are excluded
- commands are replayable by another operator

Any missing item means the baseline is not passed.

## 1. Per-Layer Evidence Contract

For every touched layer, record all fields:

- Layer ID (`0..6`)
- inputs used
- actions performed
- outputs produced
- status (`pass` or `fail`)
- evidence pointer or pointers
- decision (`advance` or `rollback`)
- if rollback: target layer and rationale

Any missing field means the check fails.

## 2. Layer Gate Checklist

## Layer 0 Gate

- capability statements are explicit and evidence-backed
- non-capability list is explicit
- boundary conclusions are persisted

## Layer 1 Gate

- each component runs in isolated runtime
- secret template exists and secret files are ignored
- minimal MVP path executes successfully per component
- execution artifacts are preserved
- component spec is derived from measured output

## Layer 2 Gate

- integration topology references all upstream specs
- every stage has explicit input or output schema
- stage-by-stage verification is complete
- cache or replay mode exists for downstream debugging

## Layer 3 Gate

- optional external tooling connectivity checks pass if used
- technical architecture doc exists with rationale
- no unvalidated component is included

## Layer 4 Gate

- PRD is complete first
- backend API spec is complete second
- frontend system spec is complete third
- cross-document consistency is verified
- priorities and implementation route are explicit

## Layer 5 Gate

- engineering rules are complete and discoverable
- runtime isolation and dependency lock rules are explicit
- secret handling and logging hygiene rules are explicit
- integration tests on real dependencies are required
- collaboration roles and review or debug loops are explicit
- Product Contract includes version declaration
- Product Contract includes boundary definition
- Product Contract includes change log
- Product Contract includes acceptance criteria

## Layer 6 Gate

- frontend and backend run independently and integrated
- backend endpoint integration tests pass
- end-to-end integration workflow is functional
- runtime bug root-cause or fix loop is closed
- static review issue list is closed
- production-readiness checklist passes
- runtime facts that diverge from docs trigger write-back or rollback

## 3. Bootstrap-Mode Guards

Mandatory in bootstrap mode:

- no layer skipping
- no forward movement before gate pass
- no architecture or blueprint work using unvalidated upstream assumptions
- new findings are written back to affected specs before closure

Guard violations force rollback to the first invalid layer.

## 4. Maintenance-Mode Guards

Mandatory in maintenance mode:

- entry classification is explicit
- minimal start layer is selected and justified
- rollback uses the smallest necessary scope
- only impacted layers are reopened
- touched scope ends with code-spec consistency

If change expands scope and breaks upstream assumptions, reclassify and reopen earlier layers.

## 5. Rollback Decision Check

On any `fail`, verify:

- first invalid assumption is identified
- rollback target is the minimal valid layer
- repair evidence exists at the rollback target
- forward re-verification is completed for affected downstream layers

If any item is missing, rollback handling is incomplete.

## 6. Production-Readiness Baseline

Required before completion of delivery scope:

- dependency vulnerability scan has no blocking severity
- logs contain no secrets
- external calls define timeout and failure behavior
- required environment keys are listed in the secret template
- documentation matches current behavior
- runtime isolation controls are defined

Any blocking failure here prevents completion.

## 7. Drift and Consistency Check

At scope closure, verify:

- no unresolved doc-to-code drift remains in touched scope
- no unresolved doc-to-doc drift remains in touched scope
- `scope_result` is explicit
- `operation_state` is explicit

If drift remains, the scope stays open.

## 8. Completion Conditions

A scope is complete only when all are true:

- every touched layer has a complete evidence record
- all required gates for touched layers are `pass`
- all rollback loops are closed with re-validation evidence
- readiness baseline passes for delivery scopes
- final closure declares both `scope_result` and `operation_state`

Otherwise status is `incomplete`.

## 9. Spot Anti-Pattern Checks

Quick fail-fast checks:

- capability assumptions without evidence
- integration attempted before per-component MVP pass
- runtime facts contradict docs and nothing is updated
- shared environment contamination is ignored
- blueprint stage is skipped before implementation
- unresolved docs-code drift remains at closure
- readiness or review is bypassed before release

Any hit requires immediate correction before completion.

## 10. Conditional Decision-Quality Gate

The risk check determines whether a first-principles or adversarial trigger is active. When inactive, the evidence record must emit `Protocol: skipped` and the exact mechanical/exact-plan reason. When active, the fixed decision-quality evidence block is mandatory, including the `Decision quality:` wrapper, Trigger, Protocol, Constraints, Assumptions, Falsifier, Falsifiers / probes, Decision, Result, and Residual risk. The first-principles `Falsifier` condition is serialized first in `Falsifiers / probes`, followed by executable probes, results, and gaps.

An unresolved or unrun high-severity threat forces `stay`, a minimal upstream `rollback`, or `blocked`; it cannot be silently passed. Accepted medium- or low-risk items must be recorded. A complete approved GSD receipt may satisfy the same review once without duplication; incomplete, missing, disabled, invalid, version-mismatched, or blocked GSD falls back to the original Harness path. The only GSD operations allowed are `plan-phase`, `execute-phase`, and `verify-work`; `gsd-review` and autonomous execution are not allowed.

Harness remains authoritative for this gate, risk evidence, rollback, `scope_result`, and `operation_state`. This gate does not change goal-enforcement ownership or imply mechanical blocking on Windows; host wording remains `audit-only-windows` when hooks are unavailable.
