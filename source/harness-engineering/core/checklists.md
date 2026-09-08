# Checklists

## Bootstrap Checklist (Layer 0-6)

### Layer 0

- [ ] Capability statements are explicit and evidence-based.
- [ ] Non-capability list is explicit.
- [ ] Boundary records are persisted.

### Layer 1

- [ ] Each component uses isolated runtime.
- [ ] Secret files are ignored; secret template exists.
- [ ] Minimal MVP script runs end-to-end per component.
- [ ] Execution artifacts are preserved.
- [ ] Component spec is derived from measured output.

### Layer 2

- [ ] Integration topology spec references all upstream component specs.
- [ ] Every stage has explicit input/output schema.
- [ ] Stage-by-stage verification has been performed.
- [ ] Cache/replay mode exists for downstream debugging.

### Layer 3

- [ ] Optional external tooling (if used) passes connectivity checks.
- [ ] Technical architecture document exists with ADR rationale.
- [ ] No unvalidated component enters architecture.

### Layer 4

- [ ] PRD completed first.
- [ ] Backend API spec completed second.
- [ ] Frontend system spec completed third.
- [ ] Cross-document consistency has been checked.
- [ ] Feature priorities and implementation route are explicit.

### Layer 5

- [ ] Engineering rules document is complete and discoverable.
- [ ] Runtime isolation and dependency lock rules are explicit.
- [ ] Secret handling and logging safety rules are explicit.
- [ ] Integration tests are required on real dependencies.
- [ ] Collaboration roles and review/debug loops are explicit.
- [ ] Product Contract includes version declaration.
- [ ] Product Contract includes boundary definition.
- [ ] Product Contract includes change log.
- [ ] Product Contract includes acceptance criteria.
- [ ] Layer 5 is not marked passed if any Product Contract field is missing.

### Layer 6

- [ ] Frontend and backend run independently.
- [ ] Backend endpoint integration tests pass.
- [ ] Integration workflow works end-to-end.
- [ ] Runtime bug root-cause/fix loop is closed.
- [ ] Static review issue list is closed.
- [ ] Production-readiness checklist passes.

## Production-Readiness Checklist

- [ ] Dependency vulnerability scan has no blocking severity.
- [ ] Logs contain no secrets.
- [ ] External calls define timeout and failure behavior.
- [ ] Required environment keys are listed in secret template.
- [ ] Documentation matches current behavior.
- [ ] Runtime isolation controls are defined (permissions/hooks/sandbox model).

## Maintenance Iteration Checklist

- [ ] Goal statement and bounded execution plan are recorded.
- [ ] Execution environment facts and isolation boundary are recorded.
- [ ] Change impact layer is identified.
- [ ] Rollback scope is minimal and explicit.
- [ ] Affected specs are updated.
- [ ] Tests for affected contracts are executed.
- [ ] New findings are written back to relevant docs.
- [ ] Retrospective records result, deviations, lessons, and evidence limits.
- [ ] Next-state handoff records the next start layer, preserved evidence, and open risks.
- [ ] A per-feature/work-item ledger is used when the scope has multiple independently verifiable items or spans sessions.

## Anti-Pattern Spot Check

- [ ] No capability assumptions without evidence.
- [ ] No integration before per-component MVP pass.
- [ ] No blueprint skip before implementation.
- [ ] No docs-code drift left unresolved.
- [ ] No review or readiness bypass before release.

## Conditional Decision-Quality Checklist

- [ ] Trigger is recorded, or the exact mechanical/exact-plan skip reason is recorded.
- [ ] When first-principles is active, concise **Constraints**, **Assumptions**, **Falsifier**, and **Decision** fields are present.
- [ ] The fixed evidence block begins with `Decision quality:`, includes the canonical `Decision` field, and serializes the first-principles `Falsifier` condition in `Falsifiers / probes` with executable probe results and gaps.
- [ ] When adversarial review is active, at least three threats have executable probes, results, identified gaps, and residual risk; cover partially covered requirements, misleading tests, and untested error/concurrency/rollback paths as applicable.
- [ ] Missing high-severity probes or unresolved high-severity threats do not yield pass; choose `stay`, minimal upstream `rollback`, or `blocked`.
- [ ] Accepted medium- or low-risk items are recorded with rationale, owner, and follow-up evidence.
- [ ] Outcome is one of `pass | stay | rollback | blocked`, with the minimal affected layer and rollback rationale when relevant.
- [ ] A complete approved GSD receipt is consumed once without duplicate review; incomplete, missing, disabled, invalid, version-mismatched, or blocked GSD follows Harness fallback. Only `plan-phase`, `execute-phase`, and `verify-work` are allowlisted; no `gsd-review` or autonomous operation.
