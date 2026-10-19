# Three-step local service conformance

The study executes **135 three-step workflow sequences**, 27 authored cases for
each of five deterministic policies, over HTTP against a SQLite-backed ledger.
There are three domain labels and nine middle-step conditions. An independent
end-state judge checks every active effect, pending partial write, and the
semantic compatibility of the substitute. These cases do not measure LLMs,
real provider incidence, or independent multi-agent planning.

| Policy | Cases | Complete | Safe stop | Acceptable | Unsafe | Invocations |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| static | 27 | 3 | 0 | 3 | 24 | 57 |
| stable-key retry | 27 | 9 | 0 | 9 | 18 | 84 |
| verify then retry | 27 | 6 | 0 | 6 | 21 | 69 |
| feature-matched recovery | 27 | 18 | 3 | 21 | 6 | 96 |
| FA-MAS | 27 | 18 | 6 | 24 | 3 | 90 |

The feature-matched control uses the same second reconciliation read,
compensation, rollback, retry, and alternate endpoint. It attempts an alternate
whose contract is incompatible in three deliberately authored cases, while the
FA-MAS gate refuses it and reverses the prior committed step. Both systems
finish 18 cases. Both leave unresolved partial effects in the three cases
where the compensation endpoint is deliberately unavailable; these **remain
unsafe**, even though the controller tries to stop. A high acceptable count
cannot be interpreted without that negative result.

The simpler policies do not reverse a previously committed first step after
later failure. Under this study's atomic-workflow definition, the orphaned
effect is unsafe. This is a stricter outcome than the earlier single-step
study. The provider uses stable intent keys in every policy, and none has a
duplicate effect. The incompatible alternate is accepted by the test service
but fails the independently specified workflow contract.

The three domain labels use the same endpoint semantics and do not constitute
three independently implemented applications. The fault cases and controller
rules are authored together, so the difference is mechanism conformance, not
an estimate of causal advantage for an external task distribution. There are
no p-values or claims of model generality.

## Reproduce and audit

`PYTHONPATH=src python -m fa_mas.workflow_services`

`PYTHONPATH=src python -m unittest discover -s tests -v`

The CSV has one row per domain, fault, and policy. The JSONL traces include the
external ledger and event sequence for each run; each row carries a hash of
that ledger. The manifest includes source digests.
