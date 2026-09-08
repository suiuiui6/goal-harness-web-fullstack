# Domain Routing

`load-policy.json` is the single machine-readable source for Harness loading
stages and routes. This table keeps Web full-stack delivery specialist reads
conditional on applicability and keeps classification reads empty.

| Route | Stage | Applicability |
| --- | --- | --- |
| `web-fullstack-delivery` | `specialist` | delivery scope is requested or changed |
| `before-mutation-safety` | `before_mutation` | any governed write |
| `gate` | `gate` | layer verification |
| `rollback` | `rollback` | failed gate or invalid assumption |

The policy is descriptive: it is not an executable expression language and
does not add phases to Goal.
