---
name: harness-engineering
description: Use when the user explicitly asks for `/harness-engineering` or when the work involves core component replacement, topology or architecture change, major feature-flow design, governance/reset work, or maintenance that must prove evidence, minimal rollback, and structured closure. Do not use it for casual explanation, isolated review, or one-off local tweaks unless the user explicitly asks for the workflow.
---

# Harness Engineering

The delivery scope is Web full-stack: frontend, backend, data, and deployment
surfaces evaluated together where applicability requires it. Reused surfaces
still require evidence, while `not_applicable` is an explicit scope decision.
Conditional loading is routed through `references/load-policy.json`, with
domain details in `references/domain-routing.md` and
`references/web-fullstack-delivery.md`.

This bundle is the copyable entry point for evidence-first engineering work. Keep the hot path short: classify, choose the smallest valid layer, load only the references needed now, and close with canonical fields.

## Five-Stage Runtime

`Trigger -> Load -> Inject -> Orchestrate -> Return`

- Read `references/runtime-stages.md` first.
- Read `references/delivery-arc.md` when aligning method phase to layers or checking Layer 5 constraints.
- Read `references/output-contract.md` before gate, readiness, or closure replies.
- In Codex, read `adapters/codex/host-map.md`.
- In Claude Code, read `adapters/claude-code/host-map.md`.
- When installing or synchronizing a host bundle, read `adapters/codex/assembly.md` or `adapters/claude-code/assembly.md` for that host.

## Hot-Path Rules

- Classify `bootstrap` or `maintenance`.
- Choose the smallest valid start layer from current evidence.
- Verify the workbench baseline before touching any layer.
- Do not cross a layer gate without pass evidence.
- If downstream evidence breaks an upstream assumption, roll back minimally.
- Every closure must emit `scope_result` and `operation_state`.
- Every active run also carries `goal_statement`, `execution_plan`, and `environment_facts`; closure adds a concise `retrospective` and an actionable `next_start_state` so the next run can resume from evidence rather than reconstructing context.

## Cold-Path Reads

- Read `SPEC.md` and `PHASES.md` only for contract wording, policy disputes, or delivery-arc alignment.
- Read `core/checklists.md` only for gate or readiness evaluation.
- Read `core/exit-and-reentry.md` only for rollback or maintenance re-entry decisions.
- Read `core/layer-details.md` only for per-layer anti-patterns, outputs, or detailed repair guidance.
- Read `core/capability-model.md` only when capability boundaries or component roles need clarification.
- Read `references/decision-quality.md` only when the risk check identifies a trigger or when evaluating a decision-quality gate; do not turn it into an always-on prompt ritual.
- Read `references/learn-harness-engineering-mapping.md` when comparing this bundle with the upstream course or deciding whether to import a harness pattern.

## Reusable Resources And Validation

- Copy `REQUIRED-EXECUTION-RECORD.template.md` when a touched layer needs an execution record; keep the template at the bundle root because it is a canonical operator-facing artifact rather than generated output.
- After changing bundle structure or routing, and before synchronizing an installed copy, run `python scripts/validate_harness_skill.py <bundle-root>` using `scripts/validate_harness_skill.py`.
- For bundle-quality work, use `evals/contract-invariants.json` through `scripts/contract_consistency.py`, validate recorded host outputs with `scripts/behavior_evals.py`, and generate review evidence with `scripts/render_skill_review.py`. Missing host output remains `not-run`; static checks never prove live behavior.
- Do not ship generated caches such as `__pycache__/` or `*.pyc` files.
