# Local HTTP service evaluation

The study executes **72 real HTTP request sequences** against a local SQLite-backed service. Each policy receives the same 18 engineered domain-by-fault cases. This is deterministic service conformance evidence, with no language model or external provider.

| Policy | Cases | Complete | Safe stop | Acceptable | Unsafe | HTTP invokes |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| static | 18 | 0 | 3 | 3 | 3 | 18 |
| retry | 18 | 6 | 3 | 9 | 3 | 33 |
| verify_before_retry | 18 | 3 | 12 | 15 | 3 | 24 |
| fa_mas | 18 | 15 | 3 | 18 | 0 | 33 |

## Scope and controls

- The six cases are timeout after commit, timeout before commit, stale first status, partial commit, unavailable primary, and denied permission.
- A fresh database state is established through the HTTP reset endpoint for each run. The post-run judge reads the actual ledger, not the controller's response text.
- The retry policy uses the same stable idempotency key across retries. This is a strong retry control, so no policy produced a duplicate effect.
- The verify-before-retry control performs one status read and retries only after authoritative non-commit. FA-MAS performs a second status read if the first is stale and can compensate a partial effect or substitute when the primary is unavailable.
- All policies stop on an explicit permission denial, which is judged a safe refusal; the denied invocation is separately counted.
- Cases test one failing state-changing service call each. They do not test full multi-step agent planning, calibrated risk ranking, live LLM decisions, production fault incidence, or provider behavior. The stronger outcome for FA-MAS reflects capabilities encoded in this scenario design; no p-values or population inference apply.

## Reproduce

`PYTHONPATH=src python -m fa_mas.local_services`

The raw run table, event traces, and protocol digest are alongside this report.
