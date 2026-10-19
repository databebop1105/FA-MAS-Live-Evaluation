# FA-MAS research artifact

This repository contains model-free mechanism studies, deterministic service
checks, and a bounded live-model evaluation harness for the FA-MAS paper. The
committed evidence does not include live-model outcomes. The live harness is
prepared for development-only compatibility checks and a later, separately
frozen confirmatory run; it is not evidence of production reliability or
multi-agent coordination.

## Documentation map

| Document | Use it for |
|---|---|
| `REPRODUCTION.md` | Recreating the recorded model-free evidence and the non-live validation path |
| `FA_MAS_Bounded_Live_Study_Protocol.md` | Scope, safeguards, cost assumptions, and launch sequence for the bounded live study |
| `docs/PREFREEZE_LIVE_EVALUATION_CHECKLIST.md` | Development acceptance checks required before freezing the held-out run |
| `FA_MAS_Remaining_Priorities_Verification.md` | Evidence audit, limits, and work that remains outside the current artifact |
| `SUBMISSION_READINESS.md` | Submission-facing status and author-controlled open items |

Historical results remain in place and are superseded only where an artifact
states that explicitly. The corrected 18,000-row exploratory study does **not**
establish a safety advantage for full FA-MAS; compensation superiority, the
full multi-agent architecture, independent replication, and author declarations
remain unresolved.

## Model-free simulator

This artifact implements a controlled, stochastic simulation of contract-aware,
SLO-constrained recovery for stateful agent/service workflows. It is intended as
the first experimental tier for the TSC paper. It does **not** represent live LLM
or production-service evidence.

Run:

```bash
python -m pip install -e .
python -m fa_mas.experiment --config configs/confirmatory_simulator_v2.yaml
```

The command writes run-level CSV data, summary tables, paired bootstrap confidence
intervals, plots, and a Markdown report to `results/`.

## Historical Tier-2 controller harness

The repository retains an earlier version-pinned controller harness with
resettable transactional state and deterministic post-run judges. The bounded
end-to-end study documented below is the current path for any future live-model
work; this historical harness is retained for provenance rather than used to
make new live claims.

Validate the Tier-2 protocol and task split:

```bash
PYTHONPATH=src python -m fa_mas.live_tier --mode validate
```

Exercise the complete Tier-2 control path without making model calls:

```bash
PYTHONPATH=src python -m fa_mas.live_tier --mode ci
```

Before a confirmatory live run, replace every `${...}` model and endpoint
placeholder in `configs/live_model_tier_v1.yaml`, set only the named credential
variables, and run `--mode freeze` to create the protocol lock. Then run
`--mode live`. The runner
rejects unpinned model identifiers, uses only the confirmatory task split, and
labels scripted CI rows `ci_non_live` so they cannot be reported as live-model
evidence.

## Local HTTP service evaluation

This third, model-free study runs actual HTTP calls against a SQLite-backed
transactional service with deterministic injected faults. It compares static,
stable-key retry, verify-before-retry, and FA-MAS recovery on the same
domain-by-fault cases. It tests one state-changing service step at a time and
does not measure language-model behavior or a complete agent workflow.

```bash
PYTHONPATH=src python -m fa_mas.local_services
PYTHONPATH=src python -m unittest discover -s tests -v
```

See `results/local_services/REPORT.md` and the accompanying raw traces and
manifest. The fault cases are constructed conformance examples; their counts
are descriptive, not estimates of population failure rates.

## Three-step service workflows

The follow-up conformance suite executes three persistent writes per workflow
and injects one fault at the middle step. The post-run judge requires all three
valid effects for completion, or no active effects for safe termination. It
includes a feature-matched controller with the same reconciliation, retry,
substitution, compensation, and rollback operations as FA-MAS; the difference
is the substitute compatibility gate. A failed compensation is reported as an
unsafe outcome even for FA-MAS.

```bash
PYTHONPATH=src python -m fa_mas.workflow_services
PYTHONPATH=src python scripts/audit_workflow.py
```

See `results/workflow_services/REPORT.md`, `workflow_runs.csv`, and
`workflow_traces.jsonl`. The nine fault conditions and three domain labels are
authored tests, not independent samples of production failures. The workflow
uses deterministic controllers rather than language-model planning or agent
messages; the three domain names share the same state machine.

## Distinct inventory service

Run `PYTHONPATH=src python -m fa_mas.inventory_services`. The 35 saved cases
exercise a separate SQLite stock and hold schema through loopback HTTP; the
terminal judge checks stock capacity and exact SKU after capture. Each fault
is an authored mechanism test. The feature-matched substitute can capture a
wrong SKU; FA-MAS rejects it and safely stops, except when release itself is
unavailable. See `results/inventory_services` and `SUBMISSION_READINESS.md`.

The paper is rendered from an official IEEE Transactions on Services Computing
original-research Word template; re-run `python build_manuscript.py` after
placing the official template in `official_template/`.

## Bounded end-to-end model study

The new `fa_mas.bounded_e2e` runner exposes both service implementations to a
multi-turn tool-using model. It compares a feature-matched controller with
FA-MAS contract enforcement on 32 held-out task instances, with shared budgets,
independent state judges, provider-failure retention, and source/configuration
locking. This evaluates one model controller at a time, not multi-agent
coordination. The protocol is locally prepared, not externally registered.

Start with the two non-live checks:

```bash
PYTHONPATH=src python -m fa_mas.bounded_e2e --mode validate
PYTHONPATH=src python -m fa_mas.bounded_e2e --mode ci --output results/bounded_e2e/new_development_ci
```

After credentials, model identifiers, provider pricing, and a development
spending ceiling are available, run only the four development fixtures first:

```bash
PYTHONPATH=src python -m fa_mas.bounded_e2e --mode development \
  --access configs/bounded_access.local.json \
  --approve-spend-usd DEVELOPMENT_USD \
  --output results/bounded_e2e/development_YYYYMMDD
```

That mode produces 16 policy/configuration episodes under a 192-call cap. Its
rows are intentionally excluded from confirmatory analysis. After every
pre-freeze check passes, create a reviewed, credential-free
`configs/bounded_access.frozen.json`, set the verification flags to `true`, and
freeze that exact configuration before the one confirmatory matrix run.

See `FA_MAS_Bounded_Live_Study_Protocol.md` for exact launch commands, model
access settings, billing verification, bounds, and interpretation limits.
Before adding credentials or freezing a live run, complete
`docs/PREFREEZE_LIVE_EVALUATION_CHECKLIST.md`; it separates development-only
endpoint acceptance checks from the held-out execution.
No live end-to-end outcomes have been collected.
