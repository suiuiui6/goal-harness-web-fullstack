# Portfolio Open-Source Productization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the five public `suiuiui6` repositories consistent, discoverable, and honest at the README, community, CI, and GitHub metadata surfaces.

**Architecture:** Keep each repository independent while applying one shared public-surface contract. Goal, Harness, and Fullstack retain their three-repository ownership boundary; Knowledge Manager and GraphRAG remain standalone products. Documentation checks are local and dependency-light; existing code CI is preserved, and repositories with known code-test gaps receive a clearly named public-surface workflow rather than a misleading full-test badge.

**Tech Stack:** Markdown, GitHub issue forms, GitHub Actions, Python standard library, existing pytest/Node commands, GitHub CLI.

---

## File map

| Repository | Primary files | Responsibility |
|---|---|---|
| `goal-harness-web-fullstack` | `README.md`, `CODE_OF_CONDUCT.md`, `.github/ISSUE_TEMPLATE/*`, `.github/workflows/ci.yml` | Integration/product evidence entry point |
| `goal-skill` | `README.md`, `CODE_OF_CONDUCT.md`, `.github/ISSUE_TEMPLATE/*`, `.github/workflows/ci.yml` | Goal intake and handoff entry point |
| `harness-engineering-skill` | `README.md`, `CODE_OF_CONDUCT.md`, `.github/ISSUE_TEMPLATE/*`, `.github/workflows/integration.yml` | Layered execution methodology entry point |
| `knowledge-manager` | `README.md`, `CONTRIBUTING.md`, `SECURITY.md`, `CODE_OF_CONDUCT.md`, `.github/workflows/public-surface.yml`, `tools/check_public_surface.py` | Standalone MCP knowledge product |
| `graghRAG-agent` | `README.md`, `CONTRIBUTING.md`, `SECURITY.md`, `CODE_OF_CONDUCT.md`, `.github/workflows/public-surface.yml`, `tools/check_public_surface.py` | Standalone GraphRAG application |
| Integration record | `docs/superpowers/specs/2026-09-09-portfolio-open-source-productization-design.md` | Cross-repository source of truth |

## Task 1: Capture clean baselines

- [ ] Run `git status --short --branch` in all five repositories and record any pre-existing changes. Do not modify untracked `artifacts/` in the Fullstack repository.
- [ ] Run the current-tree secret scan in each repository:

```powershell
$pattern = 'sk-[A-Za-z0-9]{20,}|ghp_[A-Za-z0-9]{20,}|AKIA[0-9A-Z]{16}|-----BEGIN (RSA|OPENSSH|EC|PRIVATE) KEY-----'
rg -n -i $pattern . --glob '!*.pyc' --glob '!node_modules/**' --glob '!.git/**'
```

- [ ] Record existing validation commands without changing their assertions:
  - Fullstack: `python -B -m pytest --rootdir . -p no:cacheprovider tests -q` plus its existing CI suites.
  - Goal: `python -B -m pytest --rootdir . -p no:cacheprovider goal/scripts -q` and `python -B goal/scripts/validate_goal_skill.py goal`.
  - Harness: `python -B tools/check_integrations.py`.
  - Knowledge Manager: `python -B -m pytest -q`; record existing failures as pre-existing if unchanged.
  - GraphRAG: `git diff --check` plus the frontend build only if its dependencies are already installed; otherwise mark `not-run`.

## Task 2: Add the shared community surface

- [ ] Add the Contributor Covenant 2.1 `CODE_OF_CONDUCT.md` to all five repositories with the repository's issue URL and a private reporting path through the repository owner profile.
- [ ] Add `.github/ISSUE_TEMPLATE/bug_report.yml` and `feature_request.yml` to repositories missing them. Forms must ask for reproducible steps, expected/actual behavior, environment, and evidence level; feature forms must ask for problem, proposed outcome, and alternatives.
- [ ] Add or align `.github/pull_request_template.md` with checkboxes for tests, docs, security/secret scan, and evidence boundaries. Preserve existing templates where present and only add missing checks.
- [ ] Add `CONTRIBUTING.md` and `SECURITY.md` to Knowledge Manager and GraphRAG. Include exact local commands, live-provider opt-in rules, and “do not paste credentials into issues” guidance.
- [ ] Run `git diff --check` in each repository.

## Task 3: Add dependency-light public-surface checks

- [ ] Create `tools/check_public_surface.py` in Knowledge Manager and GraphRAG. The script must:
  - require `README.md`, `LICENSE`, `CONTRIBUTING.md`, `SECURITY.md`, and `CODE_OF_CONDUCT.md`;
  - require the README to contain `Quick Start`, `Contributing`, `Security`, and `License` headings/links;
  - reject tracked files matching `.env`, `.env.*`, `*.pem`, `*.key`, or generated `*.log` paths;
  - reject current-tree token patterns `sk-<20+ alphanumerics>`, `ghp_<20+ alphanumerics>`, `AKIA<16 uppercase digits>`, and private-key headers;
  - exit non-zero with the file and rule that failed.
- [ ] Add `.github/workflows/public-surface.yml` to both repositories. It runs on pushes to the default branch and pull requests, checks out the repository, installs no third-party packages, and runs `python -B tools/check_public_surface.py`.
- [ ] Run each script first to confirm RED on the missing-file/README contract, then add the files and rerun to confirm GREEN.

## Task 4: Rewrite the five README entry points

- [ ] Keep English as the primary language and add a concise Chinese summary immediately below the opening value proposition.
- [ ] Add, in this order: product promise, verified badges, audience/use cases, non-goals or limitations, Quick Start, validation/evidence, project map, contribution/security/license links.
- [ ] Fullstack: preserve `contract`, `event_replay`, and `fullstack_fixture` evidence distinctions, `audit-only-windows`, and Goal/Harness ownership links.
- [ ] Goal: explain intake/classification/confirmation/handoff, point to Harness for execution, and show the installable `goal/` package path.
- [ ] Harness: explain the seven-layer loop, distinguish `superpower`, `skill`, and `adapter`, bound evaluation claims to recorded samples, and link Goal/Fullstack.
- [ ] Knowledge Manager: lead with Git-native MCP knowledge modules, correct the version/test-count wording to match executable evidence, and use environment variables rather than key-shaped examples.
- [ ] GraphRAG: use “GraphRAG Agent” as the display name, state current project status, separate application setup from Harness provenance, and provide tested Windows/POSIX command variants only where available.
- [ ] Add a “Status and evidence” line to every README. If a live provider, browser, or production deployment was not run, say `not-run`.
- [ ] Run the repository-specific public-surface checks and a Markdown link/path scan after each README edit.

## Task 5: Align GitHub metadata

- [ ] Use `gh repo edit` to set descriptions, homepage README anchors, and focused topics:
  - Fullstack: “Evidence-first delivery governance and isolated full-stack verification for AI coding agents”; topics `ai-agents,coding-agents,developer-tools,governance,testing`.
  - Goal: “Goal intake, classification, confirmation, and handoff for AI coding agents”; topics `ai-agents,coding-agents,developer-tools,governance`.
  - Harness: “Seven-layer evidence-first engineering framework for AI-assisted development”; topics `ai-agents,coding-agents,developer-tools,governance,testing`.
  - Knowledge Manager: “Git-native structured knowledge modules and MCP retrieval for agentic workflows”; topics `mcp,knowledge-management,ai-agents,developer-tools`.
  - GraphRAG: “Multimodal GraphRAG application for document extraction, knowledge graphs, and grounded Q&A”; topics `graphrag,rag,knowledge-graph,fastapi,react`.
- [ ] Enable Discussions for Goal, Harness, and Fullstack only; keep Issues enabled for all five. Do not enable Discussions for the application repositories until their community guidance is complete.
- [ ] Verify metadata with:

```powershell
gh repo list suiuiui6 --limit 100 --json name,description,homepageUrl,repositoryTopics,defaultBranchRef,licenseInfo,hasIssuesEnabled,hasDiscussionsEnabled
```

## Task 6: Repository validation and delivery

- [ ] Run all public-surface scripts and `git diff --check`.
- [ ] Run the existing Fullstack, Goal, and Harness validation commands to guard against documentation/link regressions.
- [ ] Run Knowledge Manager tests and preserve the exact pre-existing failure count if failures are unrelated to this pass; do not add a green code-test badge where the suite is red.
- [ ] Run GraphRAG checks available without installing new dependencies; mark unavailable live/build checks `not-run` in the execution record.
- [ ] Re-run the current-tree secret scan in all five repositories.
- [ ] Commit and push each repository independently with messages scoped to public surface changes.
- [ ] Verify each remote branch and GitHub metadata after push. Do not create a release, deploy services, or install skills.
- [ ] Append a concise execution record to the Fullstack repository documenting per-repository RED/GREEN, tests, metadata, and any remaining risks.

## Rollback

- Revert only the affected repository commit if a README or workflow check introduces a regression.
- Restore captured GitHub metadata values with `gh repo edit` if a description, topic, homepage, or Discussions setting is incorrect.
- Do not use force push, history rewriting, or broad file deletion in this productization pass.
