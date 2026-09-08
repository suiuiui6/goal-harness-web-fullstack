# Goal Harness

[![CI](https://github.com/suiuiui6/goal-harness-web-fullstack/actions/workflows/ci.yml/badge.svg)](https://github.com/suiuiui6/goal-harness-web-fullstack/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Evidence-first delivery governance for AI coding agents.

> 中文：Goal Harness 为 AI 编码 Agent 提供证据优先的项目交付治理。它会区分
> 静态契约、真实事件回放与隔离全栈验证，拒绝把过期证据、Mock 或单纯退出码 0
> 当作真实交付成功。

Goal Harness helps an agent distinguish a real, revalidated delivery result
from a green-looking command. It combines Goal intake, Harness execution
references, and Guard-enforced state transitions for Web full-stack work.

## Why it exists

AI coding workflows often report success when evidence is stale, a mock replaced
the real API, or a dependency is incompatible. Goal Harness makes those cases
machine-checkable while preserving legacy runs and explicit scope decisions.

## Quick start

```powershell
git clone https://github.com/suiuiui6/goal-harness-web-fullstack.git
cd goal-harness-web-fullstack
python -m goal_harness --help
python -m goal_harness validate --root .
python -m goal_harness capability-check --root .
python -m goal_harness delivery-audit --root .
```

The CLI delegates to the existing validators and Guard; it does not create a
second rules engine. Windows enforcement is `audit-only-windows`: audits are
required evidence, but unavailable lifecycle hooks are never described as
mechanical blocking.

## Evidence levels

- `contract`: structure, ownership, links, and rule invariants.
- `event_replay`: observed read/tool/judgment events; synthetic records do not
  count as observed behavior.
- `fullstack_fixture`: isolated page/API/SQLite/auth behavior.

Missing observed input remains `not-run`. A passing process exit code alone does
not prove delivery correctness.

## Project map

| Path | Purpose |
| --- | --- |
| `source/goal` | project intake, protocol, capability routing |
| `source/harness-engineering` | execution loading, gates, rollback, closure |
| `source/goal-enforcement` | delivery contract, Guard, state transitions |
| `fixtures/web-notes` | local page/API/SQLite fixture |
| `goal_harness` | public CLI |

## Development

```powershell
python -B -m pytest --rootdir . -p no:cacheprovider tests -q
python -B -m pytest --rootdir . -p no:cacheprovider source/goal-enforcement/tests -q
python -B -m pytest --rootdir . -p no:cacheprovider source/goal/scripts -q
python -B -m pytest --rootdir . -p no:cacheprovider source/harness-engineering/scripts -q
```

See [CONTRIBUTING.md](CONTRIBUTING.md), [SECURITY.md](SECURITY.md), and
[CHANGELOG.md](CHANGELOG.md). This project is MIT licensed.

## Roadmap

- observed Agent+Skill trace collection with explicit consent
- richer release automation and published examples
- integrations for additional agent hosts without changing the core contract

## Limitations

This repository is a governance toolkit, not a hosted deployment platform. It
does not connect to production systems, install dependencies automatically, or
claim browser/agent behavior when those observations were not run.
