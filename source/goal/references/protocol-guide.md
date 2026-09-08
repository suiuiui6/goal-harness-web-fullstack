# Goal Protocol v2 Guide

## Authority boundary

`protocol.json` is the normative machine contract for phases, transitions,
owners, record fields, invalidation events, capabilities, and error codes.
This guide explains when the controller reads that contract and how it selects
supporting references. It does not redefine any normative list.

Harness remains the sole project executor. Goal owns intake, classification,
confirmation, handoff, and response shape. Guard owns atomic state, mutation
receipts, and workspace freshness. GSD is an optional Layer 6 adapter.

## Progressive loading

1. During intake, read only enough evidence to decide whether the request is a
   project goal, a bare goal-intake, or an explicitly invoked focused redirect.
2. During classification, load `layer-execution.md` and the classification
   fields from `protocol.json`; do not discover host capabilities yet.
3. After required confirmation, load Harness runtime references.
4. Before the first governed mutation, verification, closure, or an explicit
   host-mode question, load `capability-discovery.md` and then `host-modes.md`.
5. Load `gsd-adapter.md` only after a Layer 6 proposal and Harness approval.

`output-contract.md` renders the record field names from `protocol.json` for
human-facing replies. Harness owns its own layer-gate and closure templates.

## Persisted-state compatibility

Goal Protocol v2 accepts workspace goal-state schema version 1. The protocol
upgrade changes controller and dependency contracts; it does not rewrite an
existing `.codex/goal-state.json` merely because the Skill version changed.
Every transition still requires current evidence, an adjacent state change,
and Guard validation when Guard-managed state is in scope.

If a dependency is missing or its reported protocol major is incompatible,
emit the structured blocker defined by `protocol.json` and
`output-contract.md`. Optional GSD absence falls back to Harness Layer 6;
required Harness or Guard absence blocks only the operation that needs it.
