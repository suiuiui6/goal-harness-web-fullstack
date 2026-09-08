# Codex Host Map

## Codex Native Entry Surfaces

Codex can enter Harness Engineering from three places:

1. repository root `AGENTS.md`
2. component-local `AGENTS.md`
3. explicit skill call via `.codex/skills/harness-engineering/SKILL.md`

All three surfaces should route to the same method contract rather than fork it.

Component-local `AGENTS.md` files may tighten local runtime or acceptance rules. Repository or component `AGENTS.md` files can also impose higher-priority runtime instructions, so keep them aligned with the canonical bundle and do not assume the host will automatically prefer the bundle if those instructions conflict with Harness Engineering layer, gate, rollback, or closure rules.

## Entry Judgment

Before execution:

1. classify `bootstrap` vs `maintenance`
2. choose the smallest valid start layer
3. confirm required inputs, constraints, and acceptance evidence
4. if any boundary is unclear, reopen Layer 0 instead of coding directly

## Codex Tool Mapping

- inspect and collect evidence: `shell_command` with focused reads and repository search
- parallel read-only context gathering: use `multi_tool_use.parallel` when the current Codex host exposes it; otherwise batch focused read-only commands
- edit existing files and create small changes: `apply_patch`
- run checks, builds, and scripts: `shell_command`
- keep the user informed: `commentary`
- track multi-step execution when needed: `update_plan`

## Gate And Closure Behavior

- every touched layer must be marked `pass`, `fail`, or `not-run`
- no evidence means no pass
- downstream failure rolls back only to the first invalid upstream assumption
- final closure must report touched layers, evidence pointers, rollback decisions, `scope_result`, and `operation_state`

## Shared-State Safety

- ask before irreversible actions
- ask before push, release, permission, CI, or shared-environment changes
- do not bypass tests, reviews, or repo safety rules
