# Harness Engineering Core Flow

## Scope

Harness Engineering is a documentation-driven delivery method for project bootstrap and stabilization. Within this portable bundle, the canonical capability specification lives in the bundle root (`SPEC.md`, `PHASES.md`, and `CHECKS.md`), while `core/*` defines a strict Layer 0-6 sequence for build-up and maintenance-mode policy after go-live.

## Entry Classification

Classify the request before choosing a layer path.

- Bootstrap mode: new superpower construction, core component replacement, main architecture rebuild, or a net-new primary workflow.
- Maintenance mode: localized feature work, bug fixes, focused refactors, or partial superpower/spec updates on an already stable system.
- Default rule: if the system is already stable and the requested change does not invalidate core assumptions, stay in maintenance mode and re-enter only at the smallest necessary layer.

## Layer Sequence

1. Layer 0: Capability Boundary Mapping
2. Layer 1: Per-Component MVP Validation
3. Layer 2: Integration Topology + Bridge Pipeline
4. Layer 3: External Tooling Validation (optional) + Technical Architecture (required)
5. Layer 4: Product and System Blueprints
6. Layer 5: Project Engineering Rules
7. Layer 6: Frontend/Backend Construction, Integration, and Readiness

## Gate Rule

Only move to the next layer after current layer pass criteria are met.

- If pass criteria are not met: stop and repair in current layer.
- If downstream work reveals upstream assumption failure: rollback to the smallest affected upstream layer.

## Pass Criteria by Layer

### Layer 0 Pass

- Every candidate component has an explicit capability and non-capability statement.
- Evidence is based on source/API inspection, not assumptions.
- Boundary conclusions are persisted in project records.

### Layer 1 Pass

- Every selected component runs independently in an isolated environment.
- Minimal input-to-output path is validated by real execution.
- Component spec is generated from measured behavior.

### Layer 2 Pass

- Integration topology exists with clear dependency order.
- Every bridge stage has explicit input/output schema conversion rules.
- End-to-end bridge run is reproducible; stage-level debugging is possible.

### Layer 3 Pass

- If external framework/service is used: connectivity and compatibility validated.
- Technical architecture documents deployment topology and communication contracts.
- Architecture decisions include explicit rationale.

### Layer 4 Pass

- PRD, backend API spec, and frontend system spec are complete and mutually consistent.
- Document dependency order is respected: PRD -> Backend API -> Frontend system.
- Priorities and implementation route are explicit.

### Layer 5 Pass

- Project-wide engineering rules are established and discoverable.
- Environment isolation, secret handling, testing discipline, dependency lock, and security scanning are defined.
- Multi-agent collaboration roles and boundaries are defined.
- Product Contract is complete and linked in Layer 5 outputs: version declaration, boundary definition, change log, and acceptance criteria.
- If any Product Contract field is missing, Layer 5 is marked not passed and must be backfilled before moving to Layer 6.

### Layer 6 Pass

- Frontend and backend run independently and together.
- API integration tests pass against real dependencies.
- Debug and review loops are closed.
- Production-readiness checklist is fully passed.

## Rollback Rule

Use minimum rollback scope.

- Do not rebuild from Layer 0 unless root cause requires it.
- Rollback target is determined by the first invalid assumption in the dependency chain.
- After rollback changes, re-verify pass criteria for changed layers before moving forward.

## Exit to Maintenance Mode

Exit bootstrap mode only if all are true:

- Layer 6 deliverables complete
- system is stable for the agreed stability window
- random spot-check shows docs and implementation are consistent
- onboarding guidance can reproduce environment and core workflow

Record the bootstrap completion date in project governance docs.

## Maintenance Mode Rules

Keep:

- docs as source of truth
- incremental knowledge write-back
- environment isolation and locked dependencies
- security checks and secret hygiene
- role-based collaboration for feature/bug/review work

Drop:

- mandatory full 0->6 sequence for every small change
- full blueprint rollback for localized fixes unless systemic mismatch is found
- global document refresh when only local specs are affected

Apply:

- classify whether the change is bootstrap-scale or maintenance-scale before reopening layers
- for maintenance work, start from the smallest affected layer instead of Layer 0
- only escalate to an earlier layer when current evidence shows an upstream assumption is invalid

## Re-entry Triggers

- New/replaced core component -> re-enter at Layer 0
- Topology or data-flow change -> re-enter at Layer 2
- New external framework or deployment-architecture shift -> re-enter at Layer 3
- New major feature flow -> re-enter at Layer 4
- Engineering-discipline drift -> re-enter at Layer 5
- Large-scale refactor -> re-enter at Layer 4 then progress to Layer 6
