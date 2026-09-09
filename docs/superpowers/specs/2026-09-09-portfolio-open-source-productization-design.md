# Portfolio Open-Source Productization Design

## Objective

Raise the public presentation quality of every repository owned by `suiuiui6`
without overstating product maturity or changing core architecture. The initial
portfolio contains five public repositories:

- `goal-harness-web-fullstack`
- `goal-skill`
- `harness-engineering-skill`
- `knowledge-manager`
- `graghRAG-agent`

The primary README language is English, with a concise Chinese summary where it
helps Chinese-speaking users. Success means a new visitor can identify the
project, intended audience, working entry point, evidence level, and contribution
path within roughly 30 seconds.

## Productization Strategy

Use a shared information architecture with project-specific content. Do not copy
one generic README across the portfolio and do not add decorative badges that do
not correspond to a real workflow, package, release, or license.

Each repository should expose, when applicable:

1. product name and one-sentence value proposition;
2. verified CI and license badges;
3. a short Chinese summary;
4. audience, use cases, and explicit non-goals;
5. a minimal, reproducible quick start;
6. architecture or repository map only when it reduces onboarding cost;
7. validation commands and honest evidence boundaries;
8. roadmap or project status;
9. contribution, security, and license links.

## Portfolio Boundaries

The Goal family has a deliberate three-repository ownership model:

- `goal-skill` owns intake, classification, confirmation, and handoff.
- `harness-engineering-skill` owns layered execution, gates, rollback, and closure.
- `goal-harness-web-fullstack` owns version-pinned integration and full-stack
  verification evidence.

`knowledge-manager` and `graghRAG-agent` remain standalone products. They may link
to Harness as development provenance, but must not imply that Harness is required
for end users to run the software.

## Repository-Specific Direction

### Goal Harness

Keep the evidence-first positioning. Improve the first screen with a compact
workflow explanation, verified commands, project-family navigation, current
status, and links to evidence. Preserve the distinctions between contract checks,
event replay, and isolated full-stack fixtures.

### Goal Skill

Lead with the user problem: project-level coding requests lack a reliable intake
and confirmation boundary. Show a concise Goal-to-Harness flow, installation and
validation commands, compatibility ownership, and limitations. Do not describe
Windows audit evidence as mechanical enforcement.

### Harness Engineering

Lead with the seven-layer evidence loop rather than internal terminology. Provide
separate Codex and Claude Code installation paths only where verified by repository
content. Present evaluation numbers as bounded samples, never universal performance
claims. Link to Goal and the Fullstack integration repository.

### Knowledge Manager

Position it as a Git-native MCP knowledge layer. Repair the quick start so it
includes installation before use, replace embedded-looking key examples with
environment-variable guidance, and reconcile version/test claims with executable
project evidence. Add missing community and CI surfaces before presenting them as
available.

### GraphRAG Agent

Use the correctly spelled product title while retaining the existing repository
URL. Lead with a truthful project-status label and architecture summary. Replace
placeholder or platform-specific commands with tested Windows and POSIX variants.
Separate application onboarding from the Harness development-method section. Add
community, security, and CI surfaces only after their commands are validated.

## GitHub Metadata

Every repository receives a concise description and focused topics. Homepages
should point to a real documentation or README anchor, not an unavailable deployed
site. Issues stay enabled. Discussions are enabled only for the reusable Goal and
Harness developer-tool repositories, where usage questions and design discussion
are likely to outgrow issue tracking.

Recommended topic vocabulary is intentionally small and repository-specific,
drawn from: `ai-agents`, `coding-agents`, `developer-tools`, `governance`,
`mcp`, `knowledge-management`, `rag`, `graphrag`, `fastapi`, `react`, and `testing`.

## Community and Quality Signals

Repositories missing public collaboration files receive:

- `CONTRIBUTING.md` with verified setup and test commands;
- `SECURITY.md` with private vulnerability-reporting guidance;
- `CODE_OF_CONDUCT.md` using the Contributor Covenant;
- `.github/ISSUE_TEMPLATE/bug_report.yml` and `feature_request.yml`;
- `.github/pull_request_template.md`;
- a minimal GitHub Actions workflow that runs an existing, reproducible validation
  command without secrets or paid external services.

Existing files are preserved and aligned rather than replaced wholesale.

## Evidence and Safety

- README claims must be traceable to repository files or fresh command output.
- Existing failing tests are reported; they are not hidden by weaker assertions.
- Live API tests remain opt-in and require environment variables.
- Secret scans cover the current tree before every push.
- Generated logs, local state, caches, credentials, and private paths are excluded.
- GitHub metadata changes occur after local documentation and workflow validation.
- No releases, package publication, hosted deployment, or paid external calls are
  introduced by this productization pass.

## Execution and Rollback

Work repository by repository. For each repository: establish the baseline, add a
documentation contract check, observe its initial failure, implement the smallest
documentation/community changes, validate links and workflows, run relevant tests,
commit, push, and verify GitHub metadata. A failure stays local to that repository;
it does not block safe improvements to independent repositories.

Rollback is one normal revert per repository. Metadata rollback restores the
captured description, topics, homepage, and Discussions state. No history rewrite
or force push is part of this work.

## Acceptance Criteria

- All five README files use English as the primary language and contain an accurate
  concise Chinese summary.
- Every first screen states value, audience, status or evidence, and a next action.
- Quick-start commands are syntactically valid and match current repository layout.
- Goal, Harness, and Fullstack ownership links are reciprocal and consistent.
- Every repository has MIT licensing, contribution guidance, a security policy,
  issue templates, a pull-request template, and a real CI signal where feasible.
- GitHub descriptions and topics are populated and verified through the GitHub API.
- Current-tree secret scans return no identified credentials.
- Any unrun live behavior is explicitly reported as `not-run`.
