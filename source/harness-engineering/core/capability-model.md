# Capability Model (Platform-Agnostic)

## Purpose

Define the minimum protocol for a `superpower` capability spec so it can be understood and executed without any host-specific runtime assumptions.

## Required Fields

### 1) Input Boundaries

- **Problem Scope**: what class of engineering problems this capability addresses.
- **Entry Conditions**: required preconditions before execution (context, artifacts, constraints).
- **Out-of-Scope**: explicit boundaries for requests that should not be handled by this capability.

### 2) Phase Model

- **Phases**: ordered execution phases (for Harness Engineering: Layer 0 to Layer 6).
- **Phase Goal**: the expected state change for each phase.
- **Phase Deliverables**: required artifacts to complete each phase.
- **Phase Transition Rule**: condition to move to the next phase.

### 3) Gate Criteria

- **Definition of Done (DoD)** per phase.
- **Blocking Signals**: conditions that must halt progression.
- **Escalation Rule**: when to switch role or seek user confirmation.

### 4) Evidence Contract

- **Required Execution Record**: minimum evidence that execution happened.
- **Traceability**: links between decisions, artifacts, and code changes.
- **Verification Signals**: checks/tests/inspections proving each gate passed.

### 5) Rollback Contract

- **Rollback Trigger**: signals that require re-entry to an earlier phase.
- **Rollback Target**: the specific phase to return to based on change type.
- **Consistency Rule**: documentation and implementation must converge after rollback.

### 6) Role Handoff Contract

- **Role Responsibilities**: planner/coder/debugger/reviewer accountability boundaries.
- **Handoff Payload**: minimum context package passed between roles.
- **Acceptance Rule**: receiving role must confirm inputs meet handoff criteria.

## Conformance Rules

- Core capability specs MUST NOT encode host paths, host command prefixes, or runtime-specific config locations.
- Host-specific invocation and permission mapping belong to `adapters/<host>/` only.
- A capability spec is conformant only if all required fields above are explicitly addressable.

## Mapping Note

This model defines the protocol. Concrete capability content for Harness Engineering is canonical within this bundle at:

- `../SPEC.md`
- `../PHASES.md`
- `../CHECKS.md`
