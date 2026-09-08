# Web Full-Stack Delivery Contract

<!-- GENERATED DELIVERY FIELDS START -->
## Generated field contract

The optional outer `delivery` value uses `schema_version=1` and
`profile=web-fullstack`. Its closed sections are `contract`, `slices`,
`criteria`, `evidence`, and `invalidations`.

| Constraint | Value |
| --- | --- |
| delivery target | `deployable`, `deployed`, `local-runnable` |
| surface applicability | `changed`, `not_applicable`, `reused` |
| criterion status | `blocked`, `fail`, `in_progress`, `not_applicable`, `pass`, `pending`, `stale` |
| slices | at most 128 |
| criteria | at most 512 |
| evidence | at most 2048 |
| invalidations | at most 256 |
| canonical UTF-8 JSON | at most 2 MiB (2097152 bytes) |

The exact nested required fields and machine validation remain authoritative in
`source/goal-enforcement/scripts/delivery_contract.py`.
<!-- GENERATED DELIVERY FIELDS END -->
