# FA-MAS research artifact

This repository contains model-free mechanism studies, deterministic service
checks, and one bounded live-model gate ablation for the FA-MAS paper. The live
evidence is a single frozen OpenAI GPT-6 Luna configuration operating authored
local HTTP/SQLite services; it is not evidence of production reliability,
model-family behavior, or multi-agent coordination.

## Documentation map

| Document | Use it for |
|---|---|
| `REPRODUCTION.md` | Replaying model-free evidence and re-deriving the frozen live analysis without a provider call |
| `docs/OPENAI_SINGLE_CONFIGURATION_PROTOCOL.md` | Frozen OpenAI configuration, passed preflight, cost accounting, and interpretation limits |
| `results/openai_luna/confirmatory_20261022_openai/REPORT.md` | Audited live gate-ablation result and artifact inventory |
| `docs/REVIEWER_RISK_AUDIT_2026-10-22.md` | Submission risks, evidence boundaries, and mandatory remediation |
| `docs/EVIDENCE_PIVOT_PLAN.md` | The bounded one-configuration safety-envelope study required for a credible LLM case study |
| `results/conformance_v1/REPORT.md` | Model-free bounded conformance evidence for the implemented contract gates |
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
end-to-end study documented below supersedes this historical path for the one
completed live-model case study; this harness is retained only for provenance.

Validate the historical Tier-2 protocol and task split:

```bash
PYTHONPATH=src python -m fa_mas.live_tier --mode validate
```

Exercise the historical Tier-2 control path without making model calls:

```bash
PYTHONPATH=src python -m fa_mas.live_tier --mode ci
```

This historical runner remains available for non-live validation and provenance;
it is not the executed OpenAI protocol and must not be used to create an
additional confirmatory result. The frozen execution record is documented in
`docs/OPENAI_SINGLE_CONFIGURATION_PROTOCOL.md`.

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

## Bounded contract conformance

The model-free conformance suite enumerates finite schema-valid one-action
proposals at empty local state for every authored workflow and inventory fault
family. It also executes six fixed state-dependent witness traces. Each trace
is paired between the feature-matched gate ablation and FA-MAS; the saved trace
records the proposal, gate decision, dispatched action, service observation,
and independently judged terminal state.

```bash
PYTHONPATH=src python -m fa_mas.conformance --output results/conformance_YYYYMMDD
```

The committed `results/conformance_v1` report records 406 paired schedules
(812 executions), 105 FA-MAS gate blocks, and zero blocked proposals dispatched
to a service. This supports a bounded implementation-conformance claim only; it
is not a live-model evaluation, external benchmark, production-safety proof, or
unbounded formal verification.

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

The active study uses one named configuration: **OpenAI GPT-6 Luna through Chat
Completions with `reasoning_effort: "none"`**. It compares a feature-matched
controller with FA-MAS contract enforcement on 32 held-out task instances, with
shared budgets, independent state judges, provider-failure retention, and
source/configuration locking. This evaluates one model controller at a time,
not multi-agent coordination. The protocol is locally prepared, not externally
registered.

Start with the two non-live checks:

```bash
PYTHONPATH=src python -m fa_mas.bounded_e2e --mode validate
PYTHONPATH=src python -m fa_mas.bounded_e2e --mode ci --output results/bounded_e2e/new_development_ci
```

The OpenAI configuration passed its reviewed eight-trajectory development
preflight and then completed the one permitted frozen 64-trajectory matrix.
The complete records are under `results/openai_luna/`; do not re-run the
commands below, which are retained only to document the executed sequence:

```bash
FA_MAS_OPENAI_API_KEY="$(security find-generic-password -a "$USER" -s "FA-MAS-OPENAI-EVAL" -w)" \
PYTHONPATH=src python -m fa_mas.bounded_e2e --mode development \
  --protocol configs/openai_single_e2e_v1.json \
  --access configs/openai_luna_preflight.json \
  --approve-spend-usd 1 \
  --output results/openai_luna/development_YYYYMMDD
```

Development evidence remains excluded from the confirmatory analysis. The
resulting matrix had 52 explicit finishes, 12 turn limits, no provider or budget
stops, and 64 retained trajectories. Its paired task-success contrast was zero;
the acceptable-outcome and unsafe-outcome differences were both 3.125 percentage
points in FA-MAS's direction, with cluster-resampled intervals spanning zero.

See `docs/OPENAI_SINGLE_CONFIGURATION_PROTOCOL.md` for the executed
configuration, preflight gate, cost accounting, and interpretation limits.
`FA_MAS_Bounded_Live_Study_Protocol.md` retains the earlier two-provider plan
for provenance only. Provider-specific assistant tool-call continuation
formatting is a declared, tested access setting; it is not inferred from or
written into saved model text.
