# Layer Details

## Layer 0: Capability Boundary Mapping

### Objective

Make explicit what each candidate component can and cannot do.

### Actions

1. Inspect source/API entry points, schemas, dependency declarations, and provider/factory patterns.
2. Search for expected and excluded capability keywords.
3. Write boundary conclusions with evidence links.

### Outputs

- Capability boundary record per candidate component.

### Anti-patterns

- "Probably supported" statements without evidence.
- Skipping explicit non-capability list.

## Layer 1: Per-Component MVP Validation

### Objective

Prove each selected component works in isolation on the minimal required path.

### Actions

1. Create a dedicated isolated runtime per component.
2. Install minimum dependencies.
3. Create secret template and ignore secret files.
4. Build a minimal runnable MVP script.
5. Execute with representative sample input.
6. Preserve execution output as evidence.
7. Produce component spec from observed behavior.

### Outputs

- Runnable MVP assets per component.
- Component specification v1 with measured I/O contracts.

### Anti-patterns

- Shared runtime across unrelated components.
- Attempting component-to-component integration in Layer 1.

## Layer 2: Integration Topology + Bridge Pipeline

### Objective

Define and implement the data-flow bridge between independently validated components.

### Actions

1. List components and their spec references.
2. Create dependency graph and stage order.
3. Define schema conversion rules for each edge.
4. Implement bridge stage-by-stage in order.
5. Verify each stage before moving to next.
6. Provide cache/replay mode for faster downstream iteration.

### Outputs

- Integration topology specification.
- Bridge pipeline implementation with stage-level traceability.

### Anti-patterns

- Building all stages first and testing only at the end.
- Skipping schema definitions and relying on implicit formats.

## Layer 3: External Tooling + Technical Architecture

### Objective

Validate optional external tooling and define required system architecture.

### Actions

1. If applicable, validate external service/framework connectivity.
2. Enumerate all technical components and deployment units.
3. Define communication contracts across units.
4. Record architecture decisions with rationale.

### Outputs

- Architecture document with topology and ADR-style decisions.
- Optional external-tool connectivity records.

### Anti-patterns

- Introducing unvalidated components.
- Architecture decisions without rationale.

## Layer 4: Product and System Blueprints

### Objective

Create coherent implementation blueprints before construction.

### Actions

1. Write PRD first (user flow, module list, priority, core interactions).
2. Write backend API architecture/spec second.
3. Write frontend system design/spec third.
4. Validate cross-document consistency and dependency references.

### Outputs

- PRD
- Backend API spec
- Frontend system spec

### Anti-patterns

- Starting construction before blueprints converge.
- Writing frontend spec before backend API contracts are clear.

## Layer 5: Project Engineering Rules

### Objective

Establish mandatory engineering constraints for sustainable implementation.

### Actions

1. Define repository structure and ownership boundaries.
2. Define environment isolation and dependency-lock rules.
3. Define secret management and log hygiene rules.
4. Define test discipline (real dependencies for integration tests).
5. Define role-based collaboration flow and review/debug loops.
6. Define security scan baseline and readiness gates.

### Outputs

- Project governance and engineering-rules document.
- Product Contract for this skill/superpower with four required fields:
  - Version declaration (semantic version and compatibility statement)
  - Boundary definition (in-scope, out-of-scope, and done definition)
  - Change log (what changed, why, impact, migration/evidence links)
  - Acceptance criteria (must-pass checks, failure signals, rollback conditions)

### Anti-patterns

- Test suites relying only on mocks for integration contracts.
- Missing lockfile or vulnerability scanning rules.

## Layer 6: Construction, Integration, and Readiness

### Objective

Implement frontend/backend, close debug-review loops, and prove production readiness.

### Actions

1. Implement frontend from approved frontend spec.
2. Implement backend from approved backend API spec.
3. Add integration tests for every backend endpoint.
4. Run integration and optional E2E checks.
5. Resolve runtime bugs via root-cause workflow.
6. Resolve static/code-quality issues via review workflow.
7. Run production-readiness checklist.

### Outputs

- Running system
- Test evidence
- Review and bugfix evidence
- Readiness checklist result

### Anti-patterns

- Treating "it runs once" as complete.
- Shipping without readiness checks.
