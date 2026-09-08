---
name: goal-enforcement
description: "Use when operating, auditing, or troubleshooting the goal-enforcement guard for an active /goal workflow: state audits, mutation gating, stale verification, open failures, overrides, lifecycle hooks, or Windows audit-only behavior. Do not use it as a general project-planning skill; it is only for the enforcement layer."
---

# Goal Enforcement

This is the enforcement-layer companion to `/goal`, not a general project-planning skill.

Use the bundled `scripts/goal_guard.py` to validate `.codex/goal-state.json` and enforce project-goal transitions.

## Host mode

Run `codex features list` before claiming hard enforcement.

- On a host that supports `hooks.json` and has `codex_hooks` enabled, report `hard-hook`.
- Codex CLI 0.118.0 on Windows disables lifecycle hooks. Report `audit-only-windows`; violations are not mechanically blocked.

Never describe audit-only mode as hard enforcement.

## Resolve Workspace Before Audit

- Use an explicit workspace path from the user when one is provided.
- Otherwise, use the nearest current directory or ancestor that contains `.codex/goal-state.json`.
- Never audit a drive root such as `C:\` merely because a projectless task starts there.
- If no state file is found, do not run the guard against a guessed path; ask the user for the intended workspace path.
- Report a missing state only after the intended workspace has been resolved.
- Guard CLI commands without `--workspace` may resolve only the nearest ancestor
  containing an active state; otherwise they fail with a workspace-required
  error. Hooks reject malformed payloads, non-object tool inputs, and
  symlinked `.codex`, state, or lock paths rather than falling back to `cwd`.

## Audit

```bash
python3 ./scripts/goal_guard.py audit --workspace <workspace>
```

A passing audit verifies schema, classification, plan approval, layer evidence, open failures, verification freshness, command binding, workspace fingerprint, and closure state. The fingerprint covers tracked plus non-ignored untracked Git files (or regular non-governance files outside Git) and excludes `.codex` guard metadata. It proves current-content equality at audit time, not the absence of an edit-and-restore during a long verification; use an isolated snapshot when concurrent writers are possible. It does not prove that an audit-only model could not edit the state file.

`verified`/`complete` receipts always require a real single-use command hash and
workspace content fingerprint. `write-state` cannot turn off a required plan,
change bootstrap confirmation, or skip adjacent layer progression; rewind only
through `rollback-layer`. The guard rejects governance-path symlinks and
unsupported special files before hashing.

## Guarded lifecycle

The plugin registers PreToolUse, PostToolUse, SessionStart, UserPromptSubmit, and Stop hooks. PreToolUse blocks premature mutations and completion; PostToolUse invalidates stale verification and records failed mutations; Stop rejects early finalization.

## Failure and interruption recovery

`open_failures`, `in_flight_mutations`, and `last_mutation_seq` are guard-owned and serialized with a workspace lock. Resolve failures with `goal_guard.py resolve-failure --failure-id <id> --evidence "<root cause and re-verification>"`; do not clear them through `write-state`.

If PreToolUse reserved a mutation but PostToolUse never arrived because the process or hook lifecycle was interrupted, recover only that reservation with `goal_guard.py recover-reservation --reservation-id <id> --evidence "<crash/interruption investigation>"`. Recovery removes the named reservation and creates an open failure; resolve that failure separately after remediation and re-verification. Never silently delete an orphan reservation.

## Override

An override is valid only with a non-empty reason, `authorized_by: user`, a confirmation identifier, and a positive single-use counter. `write-state` cannot install or broaden it. Use the interactive `authorize-override` command from a human terminal; non-interactive agent execution is rejected. Consume the authorization before one mutation, completion, or Stop.
