# Output Contract

## First Reply Gate

The First Reply Gate applies only when the request already includes a concrete project objective. In that case, the first active `/goal` reply must use the Classification Reply exactly. Begin with `Goal:` and include all five fields before any optional explanation. Do not substitute an informal project outline for classification.

A bare `/goal` or `$goal` command without a concrete project objective is `goal-intake`. Ask only for the missing project objective. Do not emit the Classification Reply.

A project-scoped natural-language request uses the same contract when it already contains a concrete project objective, even when it does not literally contain `/goal`.

## Classification Reply

```markdown
Goal: [one-sentence summary]
Classification: [bootstrap/maintenance], starting from Layer [N]
Rationale: [why this start layer is correct]
Confirmation: [required/recorded/not-required and why]
Next action: [what happens before any mutation]
```

These five labels are a closed set and must appear exactly once in that order.
`Host mode` must not replace `Confirmation:` in this reply.
Host-mode discovery and reporting belong only to the later operation that needs
them.

## Classification Reference Boundary

A classification reply may use `layer-execution.md`, this output contract, and
the classification fields in `protocol.json`. Stop after the five-field reply
and the required confirmation boundary; capability and host discovery belong to
the later operation that needs them.

- Do not read `capability-discovery.md` during a classification-only turn.
- Do not read `host-modes.md` during a classification-only turn.
- Do not read `scripts/protocol.py` during a classification-only turn.

## Layer Gate Reply

After Harness is loaded, `/goal` should mirror the canonical Harness layer-gate contract rather than fork it.

```markdown
[Decision] Layer [N] -> [advance / rollback to Layer X / stay]
Inputs: [artifacts or facts used]
Actions: [what was done]
Outputs: [artifacts produced]
Evidence: [command result, file, log, or inspection]
Reason: [why the decision is correct]
```

## Gate / Checkpoint Discipline

After Harness is loaded, every in-progress return should still be a Layer Gate Reply or a structured progress checkpoint using the Harness gate and closure fields.

Do not replace a Layer Gate Reply or progress checkpoint with an offer for a Visual Companion, mockup, diagram, comparison, browser preview, or other optional sidecar. Offer those only when the user explicitly asks for them.

For the first governed Layer 0 mutation, include state initialization and audit in the checkpoint narrative when those steps were required to unlock the mutation. Do not turn that checkpoint into a missing-state, workspace-resolution, or schema-investigation detour.

## Verification Reply

```markdown
[决策] Verification -> [pass / fail]
Command: [exact command]
Evidence: [exact passing output or failing blocker]
Verified At: [timestamp]
Mutation Seq: [number]
Next action: [close / fix / re-verify]
```

### Verification freshness

After any stale-verification event, closure has one recovery prerequisite:
rerun the original exact verification command after the last edit and immediately before closure, replace the receipt, obtain a fresh `goal_guard.py audit --workspace`, and bind the current `Workspace Fingerprint`.
In `audit-only-windows`, report the advisory limitation: the audit remains
required evidence but does not mechanically block a mutation or closure.
The reply is incomplete unless it explicitly names `audit-only-windows` and
states that its audit is advisory evidence that does not mechanically block
mutation or closure.

Use this fixed reply shape after any stale-verification event:

```text
Prior receipt: stale (`STALE_VERIFICATION`); `Mutation Seq` alone does not prove current bytes.
Next action: Rerun the original exact verification command after the last edit and immediately before closure; replace the receipt; run a fresh `goal_guard.py audit --workspace`; bind the current `Workspace Fingerprint`.
Host enforcement: `audit-only-windows`; the audit is required advisory evidence and does not mechanically block mutation or closure.
```

`Mutation Seq` proves that the receipt is not older than the latest mutation
recorded by goal enforcement; it does not prove that the workspace bytes stayed
unchanged. The command and evidence fields must describe the exact verification
that was run, and the receipt must be replaced after any subsequent edit,
including an edit made by a subagent or the appearance of a new untracked source
file.

The guard implementation requires a workspace content fingerprint for
`verified` and `complete` states. Add:

```markdown
Workspace Fingerprint: [algorithm and value]
```

The guard recomputes the manifest during `goal_guard.py audit --workspace` and
rejects missing, malformed, stale, or mismatched values. The receipt binds the
current bytes and the exact command hash.
The receipt does not prove that an external command actually ran or detect an edit-and-restore during a long verification.
In `audit-only-windows`, rerun the exact verification immediately before
closure and report that advisory limitation rather than claiming mechanical
blocking.

## Dependency Blocker Reply

Use this when `harness-engineering`, a required Harness reference, or a required goal-enforcement guard is unavailable.

```markdown
[决策] Dependency -> blocked
Code: [DEPENDENCY_MISSING / PROTOCOL_VERSION_MISMATCH / CAPABILITY_DISABLED]
Dependency: [missing Skill, reference, or guard path]
Evidence: [exact lookup or command result]
Impact: [why planning, execution, audit, or closure cannot continue]
Next action: [install, restore, select a supported host, or obtain user direction]
```

This is a dependency blocker, not a layer pass and not evidence that Windows mechanically blocked an action.

`Evidence:` must name the lookup command or path and its observed result. A
paraphrase such as "unavailable", "cannot be found", or "reports major 2" is
not concrete lookup evidence. For a missing Harness dependency, cite the exact
Skill/reference path and the lookup result, for example `Get-Item <path>
returned PathNotFound`. For `PROTOCOL_VERSION_MISMATCH`, cite the configured and
legacy descriptor or capabilities sources and the observed protocol major from
each source.
The literal `<path>` placeholder is not concrete evidence; replace it with the
actual path that was checked before returning the blocker.

When two supplied lookups fail, copy both complete lookup-and-result clauses
into the single `Evidence:` field. Do not shorten a path with an ellipsis and
do not replace either clause with a summary such as "both checks failed".

```text
Evidence: `[exact lookup command 1]` returned `[exact result 1]`; `[exact lookup command 2]` returned `[exact result 2]`.
```

## Capability Compatibility Reply

When Guard discovery succeeds, report the compatibility decision explicitly:
`scripts/protocol.py` checked the selected `goal-guard` descriptor and reported
protocol compatibility: protocol major 1 compatible. Also report state schema 1, the required
`write-state` command, and `audit-only-windows`. Continue the same operation and
do not use the legacy candidate or emit a blocker.

## Closure Reply

After Harness is loaded, `/goal` should mirror the canonical Harness closure contract rather than fork it.

```markdown
Mode: [bootstrap/maintenance]
Start Layer: [N]
Touched Layers: [list]
Layer Outcomes: [pass/fail/not-run by layer]
Evidence Pointers: [paths, commands, or logs]
Rollback Decisions: [list or none]
scope_result: [accepted / rework-required / blocked / incomplete]
operation_state: [bootstrap_exited / maintenance_continues / in_progress]
```

## Host-mode wording

- If the host is `hard-hook`, say a hook blocked or rejected an action only when that actually happened.
- If the host is `audit-only-windows`, say the audit was required or the workflow should not proceed, but never claim the platform mechanically blocked the mutation or completion.
