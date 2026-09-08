# Open-Source Productization Design

## Objective

Turn the repository from an internal delivery workspace into an approachable,
installable, and verifiable open-source project without weakening Goal,
Harness, or Guard governance.

## Product Surface

- A bilingual README explains the problem, value, architecture, five-minute
  quick start, commands, evidence levels, limitations, and roadmap.
- `python -m goal_harness` provides `validate`, `capability-check`, and
  `delivery-audit` commands by delegating to existing validators and Guard.
- MIT licensing, contribution guidance, security policy, issue templates,
  changelog, CI, and release notes establish an ordinary open-source workflow.
- GitHub metadata uses a concise product description and relevant topics; the
  repository becomes public only after secret scanning and tests pass.

## Safety and Evidence

The CLI does not implement a second rules engine. Synthetic results remain
distinct from observed behavior, Windows remains `audit-only-windows`, and
publishing does not imply installation into local Codex runtime directories.

## Acceptance

- A new visitor can understand and run validation in five minutes.
- CLI help and all three commands have automated tests.
- CI runs the candidate suites from a clean checkout.
- No `.codex` state, generated release bundle, credentials, or caches are
  committed.
- Repository visibility and release publication happen only after local
  verification.
