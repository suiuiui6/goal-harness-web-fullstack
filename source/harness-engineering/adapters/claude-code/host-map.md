# Claude Code Host Map

## Claude Code Native Entry Surfaces

Claude Code can enter Harness Engineering from three places:

1. repository root `CLAUDE.md`
2. component-local `CLAUDE.md`
3. explicit skill call via `.claude/skills/harness-engineering/SKILL.md`

All three surfaces should route to the same method contract rather than fork it.

Component-local `CLAUDE.md` files may tighten local runtime or acceptance rules. Repository or component `CLAUDE.md` files can also impose higher-priority runtime instructions, so keep them aligned with the canonical bundle and do not assume Claude Code will automatically prefer the bundle if those instructions conflict with Harness Engineering layer, gate, rollback, or closure rules.

## Entry Judgment

Before execution:

1. classify `bootstrap` vs `maintenance`
2. choose the smallest valid start layer
3. confirm required inputs, constraints, and acceptance evidence
4. if any boundary is unclear, reopen Layer 0 rather than coding directly

## Claude Tool Mapping

- inspect and collect evidence: `Read`, `Grep`, `Glob`
- edit existing files: prefer `Edit`
- create new files only when needed: `Write`
- run checks, builds, and scripts: `Bash`
- track multi-step work: `TaskCreate/TaskUpdate`
- delegate broad or parallel work: `Agent`

## Gate And Closure Behavior

- every touched layer must be marked `pass`, `fail`, or `not-run`
- no evidence means no pass
- downstream failure rolls back only to the first invalid upstream assumption
- final closure must report touched layers, evidence pointers, rollback decisions, `scope_result`, and `operation_state`
- operation state must explicitly use `bootstrap_exited`, `maintenance_continues`, or `in_progress`

## Shared-State Safety

- ask before irreversible actions
- ask before push, release, permission, CI, or shared-environment changes
- do not bypass tests, review hooks, or repo safety constraints
