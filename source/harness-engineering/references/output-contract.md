# Output Contract

## Classification Reply

```markdown
Goal: [one-sentence summary]
Classification: [bootstrap/maintenance], starting from Layer [N]
Rationale: [why this start layer is correct]
Required reads: [files to load next]
Next action: [what happens before any mutation]
```

## Layer Gate Reply

```markdown
[Decision] Layer [N] -> [advance / rollback to Layer X / stay]
Inputs: [artifacts or facts used]
Actions: [what was done]
Outputs: [artifacts produced]
Evidence: [command result, file, log, or inspection]
Reason: [why the decision is correct]
```

## Closure Reply

Use this template for final closure, or for an explicit status checkpoint when work is still underway. If `operation_state` is `in_progress`, the reply is a progress checkpoint and must not claim completion.

```markdown
Mode: [bootstrap/maintenance]
Start Layer: [N]
Touched Layers: [list]
Layer Outcomes: [pass/fail/not-run by layer]
Evidence Pointers: [paths, commands, or logs]
Rollback Decisions: [list or none]
Retrospective: [what happened, what differed from plan, and what was learned]
Next start state: [next start layer, preserved artifacts/evidence, and unresolved risks]
scope_result: [accepted / rework-required / blocked / incomplete]
operation_state: [bootstrap_exited / maintenance_continues / in_progress]
```

## Decision-Quality Evidence

When a risk trigger is active, include this fixed block in the gate or closure evidence. For an inactive mechanical/exact-plan change, retain the same block with `Protocol: skipped` and the exact skip reason. Harness owns the interpretation, outcome, minimal rollback, `scope_result`, and `operation_state`. The first-principles `Falsifier` is the compact condition that could disprove the decision; serialize that condition first in `Falsifiers / probes`, followed by each executable probe, result, and gap.

```text
Decision quality:
  Trigger: [first-principles, adversarial, both, or none plus concrete trigger/skip reason]
  Protocol: first_principles|adversarial|both|skipped
  Constraints: [compact list]
  Assumptions: [compact list with evidence pointers]
  Falsifier: [compact condition that would disprove the decision]
  Falsifiers / probes: [falsifier -> executable probe -> result; include gaps]
  Decision: [selected option, rationale, and minimal affected layer]
  Result: pass|stay|rollback|blocked
  Residual risk: [accepted medium/low risk, unresolved high risk, or none]
```

Embed the `Decision quality:` wrapper and block directly in each gate or closure evidence record; when the surrounding record is long, point to this block and its evidence locations from the summary. Missing active evidence is not a pass. An unresolved or unrun high-severity threat requires `stay`, a minimal upstream rollback to the first invalid assumption, or `blocked`. Re-verify forward only for the affected scope. A complete approved GSD receipt is equivalent once and must not trigger duplicate review; an incomplete, missing, disabled, invalid, version-mismatched, or blocked receipt follows the original non-GSD Harness path. The only allowlisted GSD operations are `plan-phase`, `execute-phase`, and `verify-work`; `gsd-review` and autonomous execution are forbidden. Persist conclusions, checks, results, and pointers only—never private chain-of-thought, credentials, or unbounded raw output. Windows results remain audit-only evidence (`audit-only-windows`); do not claim mechanical blocking when hooks are unavailable.
