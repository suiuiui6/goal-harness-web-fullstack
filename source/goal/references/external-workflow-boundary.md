# External Workflow Boundary

This reference records the decision for evaluating external workflow packs
against `/goal` and Harness. It is intentionally off the hot path: load it only
when an external pack is proposed or a capability gap is being reconsidered.

## Controller boundary answer

The user-facing boundary answer must carry all three facts together:

`/goal` owns intake, classification, confirmation, and handoff; Harness owns planning, layer execution, gates, rollback, and closure. They remain the sole workflow owners.
Together, the `/goal`–Harness pair is the single workflow owner; no external
pack becomes a second owner.
Do not install or depend on an external workflow pack by default.
Re-evaluate only for a concrete capability-gap proposal; until that proposal supplies measured cost, compatibility, security, rollback, and acceptance evidence, keep the current boundary unchanged.
The answer is incomplete unless it explicitly states the default decision: do not install or depend on an external workflow pack by default.

## Current decision

Do not install or adapt the full gstack pack into this machine's Codex runtime.
Do not make it a second `/goal` entry point, a parallel layer state machine, or
an implicit release/autonomous surface. The current `/goal` + Harness split
already owns intake, layer selection, evidence gates, rollback, and closure.

The inspected gstack snapshot was commit
`0d1bd5616c0ef096bb7ccee336f63c60ee408618` (`1.79.0.0`). It contains 56 skill
templates, of which the Codex host exposes 55 after suppressing its `codex`
wrapper. The projected Codex frontmatter is about 29 KB (roughly 7.3 K tokens
using a byte/4 estimate) before host wrappers. That is a material always-on
catalog increase on top of the existing local skill catalog. Codex generation
keeps the full description shape; the Claude-only catalog trim must not be
assumed to reduce Codex cost.

The host and supply-chain costs are also material: Windows requires Git Bash or
MSYS plus Bun and Node, Playwright uses a Node fallback, file-copy installs need
re-running after updates, and the installer has a destructive refresh path for
an existing Codex runtime directory. None of these costs is justified by a
current `/goal` capability gap. On Windows the enforcement mode is
`audit-only-windows`: hooks provide audit evidence, but the platform must not be
described as mechanically blocking a mutation or completion.

## Capability triage

| Capability | Decision | Boundary reason |
|---|---|---|
| `gstack-wtree` + evidence freshness | Borrow the invariant only | Binds verification to tested content and catches mid-run edits; implement natively if approved, without a gstack dependency. |
| `gstack-context-bill` | Do not integrate | Useful for a one-time cost audit; progressive reference loading already keeps the current `/goal` hot path bounded. |
| `gstack-issue-guard` | Defer | `/goal` and Harness currently have no tracker-body ingestion path. Revisit only when Issue/PR text enters model context. |
| `office-hours`, `autoplan`, `plan-*` | Do not import | Overlaps intake, Layer 0/1 design, and Harness planning. |
| `review`, `qa`, `ship`, `land-and-deploy` | Do not import | Overlaps review/readiness/release gates and risks a second closure contract or side-effect path. |
| browser, Cookie, ngrok, pair-agent, gbrain | Do not import | Not required by `/goal`; expands local, credential, network, and remote-agent boundaries. |

## The one justified follow-up

The goal-enforcement path now carries a deterministic
`sha256-manifest-v1` workspace fingerprint and exact command hash alongside
the existing `Mutation Seq`. Git manifests include tracked and non-ignored
untracked files; non-Git manifests include regular files while excluding
`.codex` and `.git` metadata. The guard recomputes the manifest under the
workspace state lock and fails closed on missing, malformed, or mismatched
verification/closure receipts. It hashes content directly and never writes
untracked contents into a repository object store.

This is the workspace content fingerprint used by the native guard; it binds
verification and closure to the bytes observed at audit time without importing
gstack or creating a second workflow owner.

This proves current-content equality at audit time, not command execution
authenticity or the absence of an edit-and-restore during a long verification;
use an isolated snapshot/worktree when concurrent writers are possible.
Required regression cases remain: edit during a long test, edit after a passing
test, new untracked source, ignored-file change, identical content committed
after testing, missing fingerprint, and fingerprint calculation failure.

## Re-evaluation gate

Reopen this decision only when a concrete request demonstrates one of these
changes:

- a reproducible verification-staleness incident;
- tracker or external document text is about to enter model context;
- a measured context-budget regression in the current `/goal` hot path; or
- a required capability cannot be supplied by the existing Codex skills and
  Harness without adding a second owner.

Any proposal must include measured cost, host compatibility, security boundary,
rollback path, and an acceptance test. If those facts are absent, keep the
current system unchanged.
