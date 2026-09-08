# Codex Assembly

This file explains how to package the shared `harness-engineering` bundle for Codex without rewriting the method.

## 0. Install Shape

Recommended installed layout:

```text
<repo>/
├─ AGENTS.md
├─ .codex/
│  ├─ skills/
│  │  └─ harness-engineering/
│  │     ├─ SKILL.md
│  │     ├─ SPEC.md
│  │     ├─ PHASES.md
│  │     ├─ CHECKS.md
│  │     ├─ core/
│  │     ├─ adapters/
│  │     └─ references/
└─ <component>/AGENTS.md
```

Optional repo-owned role prompts or delegation assets can live under `.codex/agents/` when the repo wants reusable templates.

## 1. Repository Root Contract

Root `AGENTS.md` should enforce:

- classify before coding
- smallest valid layer re-entry
- evidence before gate advance
- confirmation before irreversible or shared-state actions
- explicit `/harness-engineering` invocation when the user asks for the structured workflow

## 2. Component-Local Contract

Use component-level `AGENTS.md` files for local runtime, contract, and acceptance details, not for independent method forks.

Component-level `AGENTS.md` files may add local runtime, contract, and acceptance details, but repository or component `AGENTS.md` files can impose higher-priority runtime instructions. Keep them aligned with the canonical bundle and do not assume Codex will automatically prefer the bundle if those instructions conflict with Harness Engineering layer, gate, rollback, or closure rules.

## 3. Execution Contract

`.codex/skills/harness-engineering/SKILL.md` should:

- point first to `references/runtime-stages.md`
- point to `references/delivery-arc.md` for phase-to-layer alignment
- point to `references/output-contract.md` for classification, gate, and closure wording
- point to `adapters/codex/host-map.md` for host execution behavior
- load only the canonical references needed for the current scope
- require mode plus start-layer judgment before implementation
- require closure with `scope_result` and `operation_state`

## 4. Delegation Contract

When the work is sequential, keep it inline and use `update_plan`.
When the work is independent and read-heavy, use `multi_tool_use.parallel` when the current Codex host exposes it; otherwise batch focused read-only commands.
Use repo-owned planner/coder/reviewer/debugger prompts only when they clarify delegation and preserve layer discipline. If the repo keeps them under `.codex/agents/`, treat them as optional templates rather than required host-native agents.

## 5. Validation Call

Validate the installation with one explicit `/harness-engineering` run that proves:

- mode classification is reported
- smallest valid start layer is reported
- touched layers are tracked
- pass evidence is cited
- final `scope_result` and `operation_state` are emitted

