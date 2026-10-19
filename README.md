# Current evidence status — 9 October 2026

Start with REPRODUCTION.md and FA_MAS_Remaining_Priorities_Verification.md. The corrected exploratory simulator study, 150 public retail/airline direct-tool checks, 44 passing tests and fresh hash-locked installation are now included. Historical results below are retained and superseded only where explicitly stated. Live-model evaluation remains unexecuted. Compensation superiority, full multi-agent/subgraph implementation and author declarations remain unresolved.

## Retained earlier documentation

# Current evidence status — 9 October 2026

The bounded end-to-end protocol in `FA_MAS_Bounded_Live_Study_Protocol.md` supersedes the older one-decision Tier-2 plan below. Its 128 live episodes are prepared but unexecuted. The original simulator is historical authored evidence with unequal capability parameters and a weaker terminal judge. The new 18,000-row matched exploratory study does **not** show a safety advantage for full FA-MAS. See `REPRODUCTION.md` for read-only verification and `SUBMISSION_READINESS.md` for open gates.

# FA-MAS reproducible prototype

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
# FA-MAS prototype

The repository contains two deliberately separate evidence tiers. Tier 1 is the
controlled stochastic simulator reported in the manuscript. Tier 2 is a
version-pinned live-model harness with resettable transactional state and
deterministic post-run judges.

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

```bash
PYTHONPATH=src python -m fa_mas.bounded_e2e --mode validate
# Non-live infrastructure check; use a fresh development output folder:
PYTHONPATH=src python -m fa_mas.bounded_e2e --mode ci --output results/bounded_e2e/new_development_ci
```

See `FA_MAS_Bounded_Live_Study_Protocol.md` for exact launch commands, model
access settings, billing verification, bounds, and interpretation limits.
Before adding credentials or freezing a live run, complete
`docs/PREFREEZE_LIVE_EVALUATION_CHECKLIST.md`; it separates development-only
endpoint acceptance checks from the held-out execution.
`--mode development` runs only the four development fixtures under a separately
approved budget; it cannot be analyzed as confirmatory evidence.
No live end-to-end outcomes have been collected.
