# Claude Code Assembly

This file explains how to package the shared `harness-engineering` bundle for Claude Code without changing the core method contract.

## 0. Install Shape

Recommended installed layout:

```text
<repo>/
├─ CLAUDE.md
├─ .claude/
│  ├─ skills/
│  │  └─ harness-engineering/
│  │     ├─ SKILL.md
│  │     ├─ SPEC.md
│  │     ├─ PHASES.md
│  │     ├─ CHECKS.md
│  │     ├─ core/
│  │     ├─ adapters/
│  │     └─ references/
└─ <component>/CLAUDE.md
```

Optional repo-owned role prompts or delegation assets can live under `.claude/agents/` when the repo wants reusable templates.

## 1. Repository Root Contract

Root `CLAUDE.md` should enforce:

- classify before coding
- smallest valid layer re-entry
- evidence before gate advance
- confirmation before irreversible or shared-state actions
- explicit `/harness-engineering` invocation when the user asks for the structured workflow

## 2. Component-Local Contract

Use component-level `CLAUDE.md` files for local runtime, contract, and acceptance details, not for independent method forks.

Component-level `CLAUDE.md` files may add local runtime, contract, and acceptance details, but repository or component `CLAUDE.md` files can impose higher-priority runtime instructions. Keep them aligned with the canonical bundle and do not assume Claude Code will automatically prefer the bundle if those instructions conflict with Harness Engineering layer, gate, rollback, or closure rules.

## 3. Skill Invocation Contract

`.claude/skills/harness-engineering/SKILL.md` should:

- point first to `references/runtime-stages.md`
- point to `references/delivery-arc.md` for phase-to-layer alignment
- point to `references/output-contract.md` for classification, gate, and closure wording
- point to `adapters/claude-code/host-map.md` for host execution behavior
- load only the canonical references needed for the current scope
- require mode plus start-layer judgment before implementation
- require closure with `scope_result` and `operation_state`

## 4. Agent Delegation Contract

Use `Agent` only when delegation preserves layer discipline instead of hiding it.

If the repo keeps planner/coder/reviewer/debugger prompts under `.claude/agents/`, treat them as optional templates rather than required host-native agents.

Recommended role split when delegation is justified:

- planner -> decomposition and upstream assumptions
- coder -> implementation
- reviewer -> risk scan and closure check
- debugger -> failure isolation

## 5. Validation Call

Validate the installation with one explicit `/harness-engineering` run that proves:

- mode classification is reported
- smallest valid start layer is reported
- touched layers are tracked
- pass evidence is cited
- final `scope_result` and `operation_state` are emitted
