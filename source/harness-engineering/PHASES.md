# Harness Engineering Delivery Arc and Operational Phases

This file defines both the human-readable delivery arc and the strict operational choreography for `harness-engineering`.

The delivery arc explains why the method moves the way it does.
The operational phases define how execution, rollback, and closure happen.

## Part A: Delivery Arc

## Phase 1: Foundation and Capability Proof

Goal:

- make the workbench observable and prove what components can actually do

Canonical moves:

1. Establish the workbench baseline so the scope is observable, manageable, and reusable.
2. Define boundaries before making architecture claims.
3. Use source or API evidence as the final capability proof.

Primary mapping:

- precondition, Layer 0, Layer 1

## Phase 2: Engineering Loop

Goal:

- turn validated behavior into contracts, bridge stages, and blueprints

Canonical moves:

4. Solidify understanding into specs and contracts.
5. Close single-component MVP loops before bridge or system integration.
6. Let runtime facts override stale documents; write back or roll back immediately.

Primary mapping:

- Layer 1, Layer 2, Layer 3, Layer 4

## Phase 3: Productization

Goal:

- isolate environments, integrate by plan, and land the product safely

Canonical moves:

7. Isolate environments, dependencies, and secret handling.
8. Integrate by explicit contracts and planned stage order.
9. Land the product through API -> prototype -> frontend -> integrated release as applicable.

Primary mapping:

- Layer 5, Layer 6

## Part B: Operational Phases

## Phase 0: Intake and Entry Classification

Objective:

- classify incoming work as Bootstrap Mode or Maintenance Mode

Required input:

- user request
- current project or system state
- existing stability status

Procedure:

1. Determine whether the request is system-building or localized maintenance.
2. If ambiguous, default to maintenance unless evidence shows upstream or systemic impact.
3. Choose the minimal start layer using re-entry rules.
4. Record classification and start layer in work notes.

Output:

- `mode`: `bootstrap` or `maintenance`
- `start_layer`: one of `0..6`
- classification rationale

Gate:

- explicit mode and start layer must exist before entering layered work

Failure handling:

- if scope clarity is missing, pause and clarify before proceeding

## Phase 0.5: Workbench Baseline

Objective:

- confirm the affected scope is observable, bounded, replayable, and safe to execute

Procedure:

1. Confirm isolated runtime or bounded workspace for the affected scope.
2. Confirm evidence locations for specs, logs, tests, and review artifacts.
3. Confirm execution record destination.
4. Confirm secrets stay templated and ignored.
5. Confirm commands can be replayed by another operator.

Output:

- bounded execution surface
- evidence index for this scope

Gate:

- no numbered layer begins until the workbench baseline passes

Failure handling:

- repair the baseline before entering Layer 0 or any maintenance re-entry layer

## Phase 1: Layered Execution Core

Objective:

- execute required layers with gate discipline and artifact traceability

Rules:

- bootstrap: execute Layer 0 -> 6 in order
- maintenance: execute only from the chosen minimal start layer forward as needed
- never advance without current-layer pass evidence

Per-layer loop:

1. collect layer inputs
2. run layer actions
3. produce outputs or artifacts
4. evaluate pass criteria
5. record `pass` or `fail`, evidence pointers, and the decision to `advance` or `rollback`

Output:

- layer decision log for all touched layers
- artifact set for each touched layer

Gate:

- all touched layers must have explicit outcome, evidence pointer, and decision

Failure handling:

- on fail, enter rollback logic immediately

## Phase 2: Gate Evaluation and Minimal Rollback

Objective:

- resolve failures by repairing at the smallest layer scope that restores correctness

Procedure:

1. identify the first invalid assumption in the dependency chain
2. decide the rollback target layer with minimal scope
3. repair artifacts or implementation at the target layer
4. re-run gate checks from the target layer forward for the affected scope

Decision rules:

- do not reset to Layer 0 by default
- prefer in-layer repair if the assumption remains valid
- escalate rollback only when evidence invalidates an upstream assumption

Output:

- rollback decision record
- re-validation evidence for affected layers

Gate:

- a failed layer cannot be marked complete without re-validation evidence

Failure handling:

- if repeated failure persists, reclassify as broader scope and move the start layer upstream

## Phase 3: Blueprint and Governance Synchronization

Objective:

- keep specifications, architecture, engineering rules, and Product Contract synchronized with implementation intent

When required:

- always for bootstrap
- for maintenance whenever the change touches contracts, topology, architecture, governance, or release rules

Procedure:

1. update affected blueprint or governance docs in dependency order
2. re-check cross-document consistency
3. ensure project rules still enforce intended behavior
4. ensure runtime findings are written back to affected docs

Output:

- updated blueprint or governance docs
- consistency check result

Gate:

- no unresolved doc-to-doc or doc-to-contract mismatch remains

Failure handling:

- roll back to the earliest mismatched layer and reconcile

## Phase 4: Build, Verify, and Readiness Closure

Objective:

- produce runnable system state with test, review, and readiness evidence

Procedure:

1. implement according to approved blueprints and rules
2. validate endpoint integrations on real dependencies
3. close the runtime bug loop with root-cause evidence
4. close the static review loop with issue and fix evidence
5. execute the readiness checklist

Output:

- verified implementation
- test and review evidence
- readiness result

Gate:

- required tests and readiness checks are passing

Failure handling:

- route failure to the proper rollback target based on source

## Phase 5: Exit Bootstrap or Continue Maintenance

Objective:

- decide the operation state after completion of the current scope

Bootstrap exit checklist:

1. Layer 6 is complete.
2. Stability window is met.
3. Docs-implementation spot-check passes.
4. Onboarding path is reproducible.

If all pass:

- mark bootstrap completion in governance records
- switch default operation mode to maintenance

Maintenance continuation checklist:

1. affected layers are closed with evidence
2. no unresolved drift remains in touched scope
3. the re-entry trigger table remains accurate

Output:

- `scope_result`: `accepted`, `rework-required`, `blocked`, or `incomplete`
- `operation_state`: `bootstrap_exited`, `maintenance_continues`, or `in_progress`
- completion note with touched layers and evidence index

## Fast Mapping Table

| Change type | Default mode | Start layer |
|---|---|---|
| New or replaced core component | `bootstrap` | `0` |
| Data-flow or topology change | `maintenance` or `bootstrap` | `2` |
| External framework or deployment shift | `maintenance` or `bootstrap` | `3` |
| New major feature flow | `maintenance` or `bootstrap` | `4` |
| Engineering-rule drift | `maintenance` | `5` |
| Local implementation bug under stable contracts | `maintenance` | `6` |

## Required Execution Record

For each scoped execution, persist:

- mode classification
- start layer
- touched layers
- layer outcomes
- evidence pointers
- rollback decisions
- `scope_result`
- `operation_state`

Missing record means incomplete execution closure.
