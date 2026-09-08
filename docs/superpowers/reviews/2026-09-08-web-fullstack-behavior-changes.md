# Web Full-Stack Behavior Changes

This record captures the Task 8 delivery changes authorized by the user
reviewed implementation plan and the design/specification documents.

## Task 8

- Goal and Harness now name Web full-stack as the shared delivery scope while
  preserving the seven layers and narrow maintenance treatment for local API
  work.
- Harness owns execution-reference loading after classification; Goal retains
  intake, classification, and handoff references.
- Capability discovery distinguishes legacy runs from explicitly requested
  delivery runs. The latter require `delivery_feature_available` and
  `web-fullstack-delivery-v1`; a missing feature yields `CAPABILITY_DISABLED`
  before initialization or writes.
- Delivery state handoff documents raw-byte SHA-256 compare-and-swap and the
  required re-read flow after stale rejection.
- Surface applicability remains explicit: `changed`, `reused`, and
  `not_applicable`; reused surfaces are still evaluated.

## Confirmation Sources

- Design: `docs/superpowers/specs/2026-09-08-web-fullstack-delivery-design.md`
- Implementation plan: `docs/superpowers/plans/2026-09-08-web-fullstack-delivery-implementation.md`
- User review: `docs/superpowers/reviews/2026-09-08-web-fullstack-plan-self-review.md`
- Capability entry: `source/goal/references/capability-discovery.md`
