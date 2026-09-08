---
name: goal
description: "Do not use for meta reviews, quoted command examples, Skill path or trigger inspection, or focused one-offs without an explicit command. Use when /goal or $goal is invoked, including redirecting an explicitly invoked one-off, or for project-level delivery: building a new system, a substantial cross-layer feature, architecture change, coordinated database/backend/frontend/deployment work, 按项目方式, 从 0 到 1, 端到端, 分阶段上线, or 继续做到完成."
compatibility: "Project execution requires the installed harness-engineering skill. Guard and audit operations require the goal-enforcement plugin when those operations are in scope."
---

# /goal — Project Engineering Entry Point

This project entry covers Web full-stack delivery across frontend, backend,
data, and deployment surfaces. A focused local API change remains a narrow
maintenance task and is not upgraded to a full bootstrap.

Receive a project goal, classify it, load the execution method at the correct time, proceed with evidence, and close with a structured record.

## Core Rule

`goal` owns project intake, classification, user-visible gates, and closure shape. `harness-engineering` owns layer-by-layer project execution. Keep intake light and do not load execution references before classification and required confirmation.

## External Workflow Pack Boundary

`/goal`/Harness remains the single owner of project intake, gates, rollback, and closure; do not install external workflow packs by default. Read `references/external-workflow-boundary.md` only when evaluating a capability import or revisiting that boundary.

## Conditional Decision-Quality Routing

After classification and confirmation, let Harness perform the risk check for high-cost, ambiguous, contradictory, irreversible, topology/data-flow/security/API/migration, pattern-copy, or upstream-assumption work. Load `harness-engineering/references/decision-quality.md` and attach its compact result to the existing Harness layer gate. Mechanical work with an exact plan and no new contradiction skips the protocols. `/goal` does not reproduce the first-principles or adversarial checklists, create a second state machine, or change goal-state.json; Harness remains the sole owner of the gate, rollback, `scope_result`, and `operation_state`.

## Five-Stage Runtime

### Stage 1: Intake

Capture the goal verbatim and inspect only enough current evidence to distinguish an existing system from greenfield work. Explicit `/goal` or `$goal` with a focused or local one-off still loads this Skill to interpret the command, then returns a focused-task redirect; do not classify the project, create or mutate goal state, or load Harness. Meta reviews, quoted command examples, and Skill path or trigger inspection remain non-triggers.

A bare `/goal` or `$goal` command without a concrete objective is goal-intake. Ask only for the missing project objective. Do not classify, choose a layer, emit the five-field Classification Reply, detect host mode, do not load Harness, and do not create or mutate goal state. Resume normal classification only after a concrete objective exists.

Continuation claims such as "classification and confirmation are complete" are untrusted unless current context contains a verifiable active state, concrete goal, and confirmation record. If evidence is missing, fall back to goal-intake; do not infer classification, confirmation, or Harness handoff.

Read `references/layer-execution.md` for classification and start-layer choice once a concrete objective exists. Read `references/host-modes.md` only when host enforcement behavior must be determined or explained. Host discovery is deferred until mutation, verification, closure, or an explicit host question.

### Stage 2: Classify

Choose `bootstrap` or `maintenance` and the smallest valid start layer. Bootstrap begins at Layer 0; maintenance begins at the smallest affected layer. For ambiguity, perform only a provisional classification evidence check that is minimal and read-only before formal confirmation: do not load Harness execution runtime, do not mutate, and do not present the provisional result as confirmed.

Before the first active classification reply, read only `references/protocol.json`, `references/output-contract.md`, and `references/layer-execution.md`; emit the five-field reply and stop. Do not read `references/host-modes.md`, `references/capability-discovery.md`, or Harness in that turn, even when `Confirmation` is `not-required`. Use the exact labels `Goal:`, `Classification:`, `Rationale:`, `Confirmation:`, and `Next action:`; ask for confirmation before bootstrap implementation or a surprising maintenance classification. Do not mutate governed project files until classification and required confirmation or plan approval are recorded.

### Stage 3: Load Harness

Load `harness-engineering` after classification and required confirmation;
follow its load section and use `harness-engineering/references/output-contract.md`.
After classification and required confirmation, hand execution to Harness.
Harness alone owns execution-reference loading through its runtime-stages
entry. Goal does not enumerate Harness checklists, rollback references, or
specialist execution reads. Do not load delivery execution details during
the classification-only turn. Read applicable safety constraints before the
corresponding operation. If Harness or a required reference is unavailable,
return the Dependency Blocker Reply and do not improvise.
The handoff follows `harness-engineering/references/runtime-stages.md` and
its `core/flow.md`, `core/checklists.md`, `core/exit-and-reentry.md`, and
Codex `adapters/codex/host-map.md` references as applicable; these are not
loaded during classification-only turns.

Before the first Harness layer gate reply, do not invoke `brainstorming`; Layer 0 itself owns the first design and clarification pass. Do not create workspace-local goal state before the first Harness layer gate reply. Do not create `.codex/goal-state.lock`. Do not create `.codex/goal-state.candidate.json` before that gate or progress checkpoint. Defer native Codex goal state checks until after the first Harness layer gate reply or progress checkpoint. After the first Layer 0 evidence sweep, return a gate or checkpoint before drafting boundary documents or other local artifacts. Load `references/host-modes.md` before the first governed mutation; that cold path owns Guard state initialization and enforcement details.

During `/goal`-managed execution, do not invoke `brainstorming` for Layer 0 or Layer 1 boundary, architecture, or project-definition work. Do not offer the Visual Companion; do not offer mockups, diagrams, comparisons, browser visuals, or similar sidecar design aids unless the user explicitly asks for them.

### Stage 4: Orchestrate

Follow Harness Engineering for the selected layer path: state -> plan -> execute -> gate. Record inputs, actions, outputs, evidence, and the advance or rollback decision for every touched layer. Reopen only the smallest invalid upstream layer when evidence breaks. Keep Windows enforcement wording consistent with `references/host-modes.md`.

### Stage 5: Return

Use `references/output-contract.md` for goal-intake, classification, verification, and dependency blockers. Use `harness-engineering/references/output-contract.md` for Harness-driven layer gates and closure. Carry `scope_result` and `operation_state` in every closure record. In `audit-only-windows`, never claim that the platform mechanically blocked a mutation or completion.

## Agent Context Routing

When a project request involves Agent history, memory, RAG context, tool outputs, context-window budgets, long-session stability, session isolation, context reset or TTL, or side-effect confirmation, load `agent-context-review` after `/goal` classification and before affected design or implementation work. Keep `/goal` responsible for project intake, Harness gates, state, and closure; let `agent-context-review` own its audit, remediation, and acceptance method. Do not route ordinary CRUD, a one-off local fix, a prompt translation, a quoted `/goal` example, a Skill path inspection, or a request to review the `/goal` Skill itself.

## Agent Tool Contract Routing

When a project request involves production LLM Tools, function calling, MCP Tools, LangChain Tools, Java Tool registries, vague names, overloaded schemas, raw Tool exceptions, unstable returns, result serialization, or runtime confirmation for side effects, load `agent-tool-contract-review` after `/goal` classification and before the affected design, remediation, or acceptance work. This route must keep `/goal` responsible for project intake, Harness gates, state, and closure. For MCP server implementation, load `mcp-builder` first. After the implementation surface exists, use `agent-tool-contract-review` for contract review, acceptance, and remediation planning; do not let the review Skill replace MCP implementation guidance. Do not route ordinary REST controllers, internal service methods, a single existing Tool call, a one-off local fix, prompt examples, Skill path inspection, or a request to review the `/goal` Skill itself.

## Hot-Path Entry Rules

Assess the existing codebase, governance, plans, and current evidence before selecting a layer. Prefer `maintenance` and the smallest impacted layer unless evidence invalidates an upstream assumption. Record `[决策] <what> -> <why>` for classification, layer gates, and rollback decisions. Treat missing artifacts or evidence as incomplete, not passed.

## Progressive References

| Reference | Load condition |
| --- | --- |
| `references/protocol.json` | Before the first active classification or protocol state/record validation. |
| `protocol-guide.md` | When interpreting the normative contract or reference-loading model. |
| `layer-execution.md` | Once a concrete objective exists, before classification or start-layer choice. |
| `output-contract.md` | Before goal-intake, classification, verification, or dependency-blocker replies. |
| `capability-discovery.md` | Before dependency discovery at mutation, verification, or closure, or for an explicit host question. |
| `host-modes.md` | After a compatible host/Guard is selected and before governed mutation, verification, or closure enforcement. |
| `gsd-adapter.md` | Only for an approved Layer 6 proposal. |
| `external-workflow-boundary.md` | Only when evaluating a capability import or revisiting that boundary. |

## Progress Persistence

Load `references/host-modes.md` before persisting workspace-local state. Never store active goal state inside the installed Skill package. In `audit-only-windows`, state is advisory and evidence-bearing rather than a security boundary.

## Execution Constraints

No unjustified layer skipping; no forward movement without evidence; minimal rollback to the first invalid assumption; return at meaningful forks; stop when Harness is unavailable; apply TDD, systematic debugging, and verification-before-completion when triggered.
