# Host Modes

Dependency discovery and compatibility belong to `capability-discovery.md`.
This file only defines enforcement behavior after a compatible host/Guard has
been selected.

## State and Guard Enforcement

Prefer native Codex goal state when available.
Persist to `.codex/goal-state.json` only after the first Harness gate reply or before the first governed mutation.
Defer native Codex goal state checks until after the first Harness gate reply or before the first governed mutation.
If workspace-local state is required, keep it in the governed project workspace.
If `/goal` already resolved the governed project workspace for the active run, reuse that workspace for first-state initialization.
Do not re-ask for the workspace path merely because `.codex/goal-state.json` is absent.
Before the first governed mutation at any layer, run `goal_guard.py initialize-state` to atomically create the initial `classified` state. Then advance to an adjacent `planned` or `executing` state, perform the mutation, and audit before claiming a layer checkpoint or gate. The initialization requirement applies equally to bootstrap and maintenance goals and to every start layer (0 through 6).
When the first Layer 0 governed mutation is about to occur in a resolved project workspace, initialize workspace-local `.codex/goal-state.json` first. Operationally, write an initial `classified` state, then an adjacent `planned` or `executing` state, then perform the mutation, then audit before claiming the Layer 0 checkpoint or gate. Do not ask the user to restate the workspace path. Do not detour into state-schema or missing-state investigation.
Do not audit the drive root as a fallback for missing state.
Never create candidate state or lock files as a prerequisite for simply returning the first Layer 0 gate.
Never create `.codex/goal-state.lock` or `.codex/goal-state.candidate.json` as a prerequisite for simply returning the first Layer 0 gate.
Never place active state inside the installed `goal` Skill package.

Resolve the guard from `$env:USERPROFILE\plugins\goal-enforcement\scripts\goal_guard.py`. If the guard is required but unavailable, return a dependency blocker rather than pretending an audit ran.

## hard-hook

- `codex_hooks` is enabled.
- `hooks.json` lifecycle events are active.
- PreToolUse, PostToolUse, and Stop can mechanically reject invalid work.

## audit-only-windows

- Current Windows Codex CLI disables lifecycle hooks when `codex_hooks` is false.
- `goal_guard.py audit` is still required before mutation claims, layer advancement, verification, and completion.
- When practical, manually pair `pre-tool-use` and `post-tool-use` around each governed mutation, then audit before the next mutation.
- Never say the host blocked an action unless an active hook actually blocked it.

### Verification freshness and workspace content

For `verified` and `complete` states, the state carries a structured
`workspace_fingerprint` receipt using `sha256-manifest-v1`. In a Git workspace
the manifest covers tracked and non-ignored untracked files; in a non-Git
workspace it covers regular files while excluding `.codex` and `.git` metadata.
The receipt also includes `command_sha256`, the SHA-256 of the exact verification
command. `goal_guard.py audit --workspace <workspace>` recomputes the current
manifest under the goal-state lock and fails closed on a missing, malformed, or
mismatched receipt. Closure must carry the same fingerprint as verification.
The receipt and command hash are required even for direct guard API calls; a
verification or closure record without them is invalid. The guard also rejects
symlinked `.codex`/state/lock paths, directory symlinks, and special files in
the fingerprint scope. CLI guard commands without `--workspace` may use only
the nearest active governed ancestor; they never guess a drive root or an
unrelated current directory. `write-state` cannot disable a required plan,
forge bootstrap confirmation, or jump/rewind `current_layer`; use the
guard-owned `rollback-layer` command for rewinds.
The command hash and timestamp are self-consistency checks; they do not prove
that an external command really ran or that its evidence was honestly authored.

The fingerprint proves current-content equality at audit time. An edit-and-restore
during a long-running verification is not detectable. Use
an isolated snapshot/worktree for verification when concurrent writers are
possible. On Windows lifecycle hooks remain unavailable, so this is still
`audit-only-windows`: rerun the exact verification command after every file
change and immediately before closure, and never claim mechanical blocking.

## Guard Commands

```powershell
python $env:USERPROFILE\plugins\goal-enforcement\scripts\goal_guard.py write-state --workspace <workspace> --file <candidate.json>
python $env:USERPROFILE\plugins\goal-enforcement\scripts\goal_guard.py initialize-state --workspace <workspace> --goal "<goal>" --mode <bootstrap|maintenance> --start-layer <0-6> --rationale "<classification rationale>" [--confirmation-id <bootstrap confirmation>]
python $env:USERPROFILE\plugins\goal-enforcement\scripts\goal_guard.py rollback-layer --workspace <workspace> --to-layer <0-6> --reason "<rollback reason>" --evidence "<rollback evidence>"
python $env:USERPROFILE\plugins\goal-enforcement\scripts\goal_guard.py audit --workspace <workspace>
python $env:USERPROFILE\plugins\goal-enforcement\scripts\goal_guard.py resolve-failure --workspace <workspace> --failure-id <id> --evidence "<root cause and re-verification evidence>"
python $env:USERPROFILE\plugins\goal-enforcement\scripts\goal_guard.py recover-reservation --workspace <workspace> --reservation-id <id> --evidence "<crash/interruption investigation evidence>"
```

### Delivery state handoff

For a new delivery profile, callers read the exact raw bytes of
`.codex/goal-state.json`, compute SHA-256, and pass it to `write-state` as
`--expected-state-sha256 <digest>`. Guard compares that digest while holding
the state lock and rejects an absent, malformed, or stale digest. After a
rejection, re-read the raw state and digest, rebuild the candidate from that
current state, then retry through Guard. Legacy calls keep their existing
arguments and do not require CAS.
