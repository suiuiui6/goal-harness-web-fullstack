# Capability Discovery

Discover dependencies only before the first governed mutation, verification,
closure, or an explicit host question. Do not repeat discovery at ordinary
checkpoints.

## Discovery order

1. Start with the host-configured or otherwise known dependency command. Do
   not scan arbitrary locations or install a replacement during discovery.
2. Run its `capabilities` subcommand without `--workspace` or goal state and
   parse the single-line JSON descriptor. For Guard, the descriptor identifies
   `goal-guard`, protocol major `1`, supported state schemas, commands, and
   enforcement modes.
3. Load Goal Protocol v2 from `protocol.json` and use
   `scripts/protocol.py`'s `capability_compatible()` check for the named
   dependency. Also confirm that the operation's required command, state
   schema, and enforcement mode appear in the descriptor.
   For an explicitly requested Web full-stack delivery runtime, call
   `delivery_feature_available()` as an additional check and require the
   `web-fullstack-delivery-v1` feature before `initialize-state` or any write.
   An existing legacy run without `delivery` uses the ordinary compatibility
   check and does not require this feature.
4. If the configured command is missing, does not recognize `capabilities`,
   or reports an incompatible descriptor, try the documented legacy Guard
   path once: `$env:USERPROFILE\plugins\goal-enforcement\scripts\goal_guard.py`.
   Apply the same JSON and compatibility checks to that result.
5. If no compatible dependency remains, emit the Goal Protocol v2 structured
   dependency blocker from `output-contract.md`. Use `DEPENDENCY_MISSING` when
   no candidate exists, `PROTOCOL_VERSION_MISMATCH` for a capability name or
   protocol-major mismatch, and `CAPABILITY_DISABLED` for malformed JSON or a
   required command, schema, or enforcement mode that is not advertised.
   Preserve the exact command result as evidence.

GSD is an optional Layer 6 adapter. Missing, invalid, disabled, or blocked GSD
falls back to the original `/goal` plus Harness Layer 6 path. Missing Harness
or Guard blocks only the operation that requires that capability; it does not
retroactively block intake, classification, or unrelated read-only work.

On Windows, report the available host mode as `audit-only-windows`. Audits are
required evidence, but hooks may be unavailable, so never claim that the host
mechanically blocked a mutation or completion.

## Successful Compatibility Reply

When the configured `capabilities` lookup succeeds, report the selected
dependency, the observed protocol-major compatibility result, state schema,
required command, enforcement mode, and whether the same operation continues.
The report must identify protocol major 1, schema 1, the required command,
and the selected dependency's compatibility result; it may describe the
protocol checker generically rather than requiring a fixed script name.
For a Web delivery request also report the observed
`web-fullstack-delivery-v1` feature check. Do not try the legacy candidate
after a successful compatible lookup and do not emit a blocker.

```text
Compatibility: The configured capabilities lookup selected goal-guard. The protocol compatibility check found major 1, state schema 1, required command write-state, and enforcement mode audit-only-windows; the requested delivery feature check is [present|absent].
Next action: [Continue the same operation|Block before initialization or write with CAPABILITY_DISABLED]. Do not try an unneeded legacy candidate after a successful lookup; when continuing, state that the same operation continues, the legacy candidate is not tried, and no blocker is emitted.

For a selected but feature-incomplete Guard, return `CAPABILITY_DISABLED` with
`Dependency: goal-guard`; do not initialize, write `delivery`, or silently
continue as legacy. Preserve the exact descriptor and command result.
```

## Incompatible Candidate Evidence

When all candidates are incompatible, give evidence for each candidate
separately. For each candidate, name its lookup source—the configured command
or documented legacy path—and its observed result, including the reported
protocol major. Do not collapse these into an unsupported summary.

Use this fixed blocker shape, replacing the bracketed major values with the
observed values:

```text
[决策] Dependency -> blocked
Code: PROTOCOL_VERSION_MISMATCH
Dependency: goal-guard
Evidence: The configured Guard `capabilities` command reported protocol major [configured major]; the documented legacy path `$env:USERPROFILE\plugins\goal-enforcement\scripts\goal_guard.py capabilities` reported protocol major [legacy major]; Goal Protocol v2 requires major 1.
Impact: No compatible Guard remains, so the governed mutation cannot proceed.
Next action: Select or restore a Guard implementing goal-guard protocol major 1; do not execute or authorize the mutation.
```
