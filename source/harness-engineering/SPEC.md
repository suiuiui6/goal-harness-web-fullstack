---
name: harness-engineering
type: superpower-spec
status: canonical
canonical: true
version: 1.2.0
---

# Harness Engineering Capability Specification

## 1. Scope

Harness Engineering is a document-driven, gate-controlled delivery method for:

- bootstrap of a new project or net-new primary workflow
- controlled maintenance changes on an already stable system
- minimal-scope rollback and deterministic re-entry when assumptions fail

This superpower governs decision flow, artifact discipline, and the route from capability proof to productized delivery. Runtime or host differences are delegated to `adapters/*`.

## 2. Method Anchors

Harness Engineering always carries these anchors:

- layered decomposition
- evidence before advancement
- specification solidification from measured behavior
- single-component MVP proof before bridge work
- environment isolation
- progressive integration toward release

Priority rule:

- source or API inspection is the final authority for capability claims
- runtime facts outrank stale documentation or informal promises

## 3. Delivery Arc

The method is easiest to understand as a three-phase arc that maps onto the canonical seven layers.

| Method phase | Goal | Canonical moves | Primary layers |
|---|---|---|---|
| Phase 1: Foundation and capability proof | Make work observable and prove real capability boundaries | workbench baseline, boundary mapping, source or API verification | precondition, Layer 0-1 |
| Phase 2: Engineering loop | Turn proof into contracts, bridges, and system blueprints | spec consolidation, single-component MVP closure, runtime-driven correction | Layer 1-4 |
| Phase 3: Productization | Isolate environments, integrate by plan, and land the product | environment isolation, planned integration, API -> prototype -> frontend -> integrated release | Layer 5-6 |

The phase model explains intent. The layer model remains the execution contract.

## 4. Canonical References

Normative references that must stay aligned inside this bundle:

- `core/flow.md`
- `core/layer-details.md`
- `core/checklists.md`
- `core/exit-and-reentry.md`

Host-specific references:

- `adapters/codex/host-map.md`
- `adapters/claude-code/host-map.md`

Conflict rule:

- if adapter behavior conflicts with core engineering constraints, core constraints win

## 5. Operating Modes

### 5.1 Bootstrap Mode

Use when the request implies one of:

- new superpower construction
- core component replacement
- main architecture rebuild
- net-new primary workflow

Execution path:

- run Layer 0 -> 6 in strict order
- do not cross a gate without pass evidence

### 5.2 Maintenance Mode

Use when the request is localized:

- feature increment
- bug fix
- focused refactor
- local spec or contract correction

Execution path:

- start from the smallest impacted layer
- reopen upstream only when evidence shows a broken assumption

## 6. Global Contract

Every touched layer must define and produce:

- inputs: concrete artifacts or runtime facts required to start
- actions: bounded, executable work
- outputs: persisted artifacts
- pass gate: objective criteria to advance
- fail signal: what invalidates the current layer
- rollback target rule: the smallest upstream layer that must be revisited

Advance rule:

- `PASS` is required to move forward

Failure rule:

- `FAIL` stops forward progress
- repair inside the current layer first
- if root cause is upstream assumption failure, roll back minimally

## 7. Execution Precondition: Workbench Baseline

Before any layer starts, establish a workbench baseline for the affected scope.

Inputs:

- workspace or runtime boundary for the task
- expected evidence locations
- secret template and ignore policy
- execution record destination

Actions:

- confirm the affected scope can be observed, replayed, and audited
- confirm commands can be rerun by another operator
- confirm secrets remain templated and excluded from repo or logs

Outputs:

- bounded execution surface
- evidence index for this scope

Pass Gate:

- work is observable, manageable, and reusable for the affected scope

Fail Signal:

- shared or drifting runtime with no traceable evidence path
- commands cannot be replayed

Rollback Target Rule:

- repair the baseline before entering any numbered layer

## 6.1. Five-Part Execution Loop

Every execution record must make the engineering loop explicit:

1. **Goal** — state the observable outcome, scope boundary, and acceptance criteria.
2. **Execution** — list bounded actions, dependencies, sequencing, and stop/rollback conditions.
3. **Environment** — record host mode, workspace/isolation boundary, runtime/dependency versions, permissions, and external constraints.
4. **Retrospective** — at closure, compare result with the goal, record deviations, root causes, lessons, and what the evidence cannot prove.
5. **State handoff** — record the next start layer, preserved artifacts/evidence, open risks, and the first restart action.

The first three fields are required before governed mutation. The last two are required for `accepted`, `rework-required`, `blocked`, and `incomplete` closure records. A closure without a state handoff is incomplete because it cannot safely seed the next plan.

## 8. Layer-by-Layer Contract

## 8.1 Layer 0: Capability Boundary Mapping

Inputs:

- candidate component list
- source or API entry points
- dependency declarations and provider or factory contracts

Actions:

- verify explicit capabilities by code or API evidence
- verify explicit non-capabilities and unsupported paths
- persist boundary records with evidence pointers

Outputs:

- capability boundary record per component

Pass Gate:

- capability and non-capability statements are explicit for all candidates
- evidence is inspection-based, not assumption-based

Fail Signal:

- any "probably supported" claim without proof
- missing non-capability list

Rollback Target Rule:

- not applicable because this is the first numbered layer

## 8.2 Layer 1: Per-Component MVP Validation

Inputs:

- Layer 0 boundary records
- selected component set

Actions:

- create isolated runtime for each component
- install minimal dependencies
- create secret template and ignore real secret files
- build a minimal runnable script with representative sample input
- execute and preserve runtime evidence
- derive measured component I/O contract from output

Outputs:

- runnable MVP assets per component
- component spec v1 derived from measured contracts

Pass Gate:

- every selected component runs independently
- the minimal required path is validated with real execution
- artifacts are preserved and traceable

Fail Signal:

- integration attempted before isolated pass
- shared runtime causes non-deterministic behavior
- spec written without measured output

Rollback Target Rule:

- if failure is a boundary misunderstanding, roll back to Layer 0
- otherwise repair in Layer 1

## 8.3 Layer 2: Integration Topology and Bridge Pipeline

Inputs:

- Layer 1 component specs
- dependency and data-flow requirements

Actions:

- define component dependency graph and stage order
- define schema conversion on every edge
- implement bridge pipeline stage by stage
- validate each stage before moving forward
- add cache or replay mode for downstream debugging

Outputs:

- integration topology specification
- bridge implementation with stage-level traceability

Pass Gate:

- all bridge stages have explicit input or output schema
- topology references all upstream component specs
- end-to-end bridge run is reproducible

Fail Signal:

- end-only testing without stage validation
- implicit schema assumptions

Rollback Target Rule:

- if it is a single-stage mapping bug, repair in Layer 2
- if the component contract from Layer 1 is invalid, roll back to Layer 1

## 8.4 Layer 3: External Tooling Validation and Technical Architecture

Inputs:

- Layer 2 topology and bridge evidence
- optional external framework or service requirements

Actions:

- validate connectivity and compatibility of optional external tooling
- define technical components and deployment units
- define inter-unit communication contracts
- record architecture decisions with rationale

Outputs:

- technical architecture document
- optional external-tool connectivity records

Pass Gate:

- no unvalidated component enters architecture
- architecture and communication contracts are explicit
- decision rationale exists

Fail Signal:

- architecture claim without validated component or tooling
- missing rationale for critical decisions

Rollback Target Rule:

- if the architecture issue is a topology mismatch, roll back to Layer 2
- if root cause is a wrong capability assumption, roll back to Layer 0 or 1

## 8.5 Layer 4: Product and System Blueprints

Inputs:

- Layer 3 architecture baseline
- product requirements and constraints

Actions in fixed order:

- write the PRD first
- write the backend API specification second
- write the frontend system specification third
- make the implementation route explicit from API to prototype to frontend and integrated flow
- cross-check dependency and contract consistency across all three documents

Outputs:

- PRD
- backend API specification
- frontend system specification

Pass Gate:

- all three documents are complete and mutually consistent
- priority and implementation route are explicit
- document dependency order is respected

Fail Signal:

- implementation starts before blueprint convergence
- frontend spec precedes clear backend contracts

Rollback Target Rule:

- if there is a contract mismatch from architecture assumptions, roll back to Layer 3
- if product scope invalidates architecture, roll back to Layer 3 or Layer 2 if data flow changed

## 8.6 Layer 5: Project Engineering Rules

Inputs:

- Layer 4 approved blueprints
- team and process constraints

Actions:

- define repository boundaries and ownership
- define runtime isolation and dependency lock policy
- define secret handling and log hygiene policy
- define integration-test discipline on real dependencies
- define collaboration roles and review or debug loops
- define security scan baseline and readiness gates
- complete the Product Contract with version declaration, boundary definition, change log, and acceptance criteria

Outputs:

- engineering rules or governance document
- Product Contract linked from Layer 5 outputs

Pass Gate:

- mandatory policies exist and are explicit
- rules are enforceable and discoverable by executors
- Product Contract is complete and linked

Fail Signal:

- integration contracts are validated only with mocks
- missing dependency lock or vulnerability-scan baseline
- any Product Contract field is missing

Rollback Target Rule:

- if rules conflict with blueprint assumptions, roll back to Layer 4
- otherwise repair in Layer 5

## 8.7 Layer 6: Construction, Integration, and Readiness

Inputs:

- Layer 4 blueprints
- Layer 5 engineering rules

Actions:

- implement frontend from approved frontend spec
- implement backend from approved backend API spec
- add integration tests for backend endpoints
- execute integration and optional end-to-end checks
- drive the delivery path from API to prototype to frontend to integrated release as applicable
- close the runtime bug loop with root-cause and fix evidence
- close the static review loop with issue and fix evidence
- execute the production-readiness checklist

Outputs:

- running system with independent and integrated surfaces
- integration test evidence
- review and bug-fix evidence
- readiness checklist result

Pass Gate:

- the integration workflow runs end to end
- required tests pass on real dependencies
- runtime and static issues are closed
- production-readiness checklist passes

Fail Signal:

- "runs once" is treated as completion
- readiness is bypassed
- runtime facts contradict docs and no write-back or rollback occurs

Rollback Target Rule:

- if it is an implementation bug under stable contracts, stay in Layer 6
- if it is a contract mismatch, roll back to Layer 4 or 5 depending on source
- if architecture or topology is invalid, roll back to Layer 3 or 2

## 9. Exit and Re-entry Contract

Bootstrap exit is allowed only when all are true:

- Layer 6 deliverables are complete
- stability window is met
- spot-check confirms docs and implementation consistency
- onboarding path reproduces environment and core flow

Then:

- record bootstrap completion date in governance docs
- switch default operation to Maintenance Mode

Re-entry triggers and minimal start layer:

- new or replaced core component -> Layer 0
- data-flow or topology change -> Layer 2
- external framework or deployment shift -> Layer 3
- new major feature flow -> Layer 4
- engineering-discipline drift -> Layer 5
- large-scale refactor -> Layer 4 then progress to 6

## 10. Required Artifact Matrix

Each execution cycle must leave traceable artifacts:

- layer gate status per touched layer
- evidence pointers per gate
- rollback decisions with minimal-scope rationale
- updated affected spec or governance documents
- closure record with `scope_result` and `operation_state`

No hidden completion rule:

- work is incomplete if artifacts are missing, even when code appears to run

## 11. Security and Quality Baseline

Mandatory baseline across all modes:

- secret hygiene with no secrets in repo or logs
- dependency and vulnerability hygiene
- timeout and failure semantics for external calls
- documentation remains source of truth after runtime write-back
- runtime isolation controls remain explicit

## 12. Non-goals

This superpower does not prescribe:

- a specific tech stack
- a fixed UI style or deployment vendor
- adapter-specific command syntax

Those concerns belong to adapters and project rules.
