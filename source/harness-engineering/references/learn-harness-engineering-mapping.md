# Learn Harness Engineering Mapping

This note records the bounded lessons imported from the public course repository
[`walkinglabs/learn-harness-engineering`](https://github.com/walkinglabs/learn-harness-engineering).
It is a design reference, not a runtime dependency.

## Observed principles

- A harness is the environment around the model: instructions, tools, environment,
  state, and feedback.
- A goal needs an executable definition of done; a feature/state ledger prevents
  scope drift and makes one work item resumable.
- Initialization is its own phase: establish the workbench before mutation.
- Long sessions need a durable handoff; the repository is the system of record,
  not chat history.
- Verification must be independent enough to catch premature victory claims,
  and a clean-state check is part of closure.
- Repeated execution benefits from a maker/checker split and explicit feedback;
  automation is a separate loop concern, not a reason to weaken gates.

## Mapping into this bundle

| Course principle | Harness contract | Boundary |
|---|---|---|
| Goal + definition of done | `goal_statement`, layer pass gate, acceptance rationale | Does not invent product requirements |
| Execution loop | `execution_plan`, bounded actions, stop/rollback conditions | Does not replace layer gates |
| Environment/workbench | `environment_facts`, baseline, host adapter | Windows remains `audit-only-windows` |
| State + handoff | execution record, `next_start_state`, next start layer | State is evidence-bearing, not proof of execution |
| Feedback/retrospective | `retrospective`, runtime facts, doc write-back | Never stores secrets or private chain-of-thought |
| Feature ledger / clean state | touched-layer records, closure evidence, readiness checks | Use project-local ledgers when the project needs per-feature tracking |

## Deliberate non-imports

- No external course scripts, autonomous loop, scheduler, or alternate state machine.
- No mandatory feature-list file for every project; require one when work contains
  multiple independently verifiable features or repeated sessions.
- No claim that a fingerprint proves command execution or prevents edit-and-restore.

The source was consulted on 2026-09-02. Re-check the upstream repository before
changing this mapping when its framework or terminology materially changes.
