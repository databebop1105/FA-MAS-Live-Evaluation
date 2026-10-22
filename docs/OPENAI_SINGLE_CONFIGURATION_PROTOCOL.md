# OpenAI single-configuration protocol

**Status:** executed once on 22 October 2026. The development preflight passed,
the exact protocol was frozen, and the complete 64-trajectory held-out matrix
was retained and independently analyzed.

This is the active live-evaluation protocol for the submission-week study. It
replaces the earlier two-provider confirmatory plan, which is retained only as
historical development documentation. The study still evaluates FA-MAS; the
named OpenAI model is only the action proposer. This protocol must not be
re-run or amended after its held-out execution.

## Named configuration

| Field | Executed frozen configuration |
|---|---|
| Provider | OpenAI |
| Model | `gpt-6-luna` |
| Endpoint | Chat Completions at `https://api.openai.com/v1` |
| Function-calling reasoning setting | `reasoning_effort: "none"` |
| Tool interface | Forced generic `execute_service_action`; operation remains a model-selected argument |
| Sampling | `temperature: 0.0`, accepted in development preflight |
| Output ceiling | `max_completion_tokens: 512` |
| Parallel tool calls | disabled |

OpenAI documents that GPT-6 Luna supports function calling through Chat
Completions with `reasoning_effort` set to `none`. The development preflight
established that the exact request fields and continuation serialization worked
for this account and endpoint. No model alias, provider, parameter, or fallback
was changed after the held-out result was observed.

## Matrix and cost ceilings

| Stage | Matrix | Maximum calls | Conservative token-price reservation |
|---|---:|---:|---:|
| Development preflight | 4 tasks × 2 policies | 96 | USD 0.178176 |
| Confirmatory gate ablation | 32 tasks × 2 policies | 768 | USD 1.425408 |
| Both stages | — | 864 | USD 1.603584 |

The reservations use the frozen 16,000-byte input ceiling, 512 completion-token
ceiling, and current configuration rates of USD 0.10/M input and USD 0.50/M
output. They are local conservative limits, not a provider invoice guarantee.
The development run used an explicit USD 1 ceiling; the confirmatory run used
an explicit USD 2 ceiling.

## Execution record

The eight development trajectories passed `fa_mas.preflight` with the exact
returned model identity, multi-turn tool continuations, explicit finish actions,
multiple selected operations, usable token accounting, and no credential-like
trace content. The held-out run recorded all 64 planned trajectories, 607 model
requests, 52 explicit finishes, 12 turn limits, zero provider failures, and
zero budget stops. Its local usage-priced cost was USD 0.055423; its conservative
reservation was USD 1.126592 under the USD 2 ceiling.

The paired primary result is descriptive: task success had a 0.0-point
FA-MAS-minus-feature-matched difference; acceptable outcome was +3.125 points
(16-cluster bootstrap interval -6.25 to +12.50); unsafe outcome was -3.125
points (-12.50 to +6.25). All supplementary Holm-adjusted cluster-sign p-values
were 1.0. These data do not establish a reliable gate advantage in this authored
bank.

The passed preflight, lock, execution marker, manifests, trajectory records,
and analysis are retained under `results/openai_luna/`. The two legacy boolean
access flags remain false because this protocol's actual acceptance gate is the
immutable passed preflight report and exact freeze hash, not a manually asserted
configuration flag.

## Executed sequence

The key remains in macOS Keychain under `FA-MAS-OPENAI-EVAL`; it is exposed only
to the process through `FA_MAS_OPENAI_API_KEY` and is never written to a file.

```bash
FA_MAS_OPENAI_API_KEY="$(security find-generic-password -a "$USER" -s "FA-MAS-OPENAI-EVAL" -w)" \
PYTHONPATH=src python -m fa_mas.bounded_e2e --mode development \
  --protocol configs/openai_single_e2e_v1.json \
  --access configs/openai_luna_preflight.json \
  --approve-spend-usd 1 \
  --output results/openai_luna/development_YYYYMMDD

PYTHONPATH=src python -m fa_mas.preflight \
  --protocol configs/openai_single_e2e_v1.json \
  --tasks configs/bounded_tasks_v1.jsonl \
  --access configs/openai_luna_preflight.json \
  --runs results/openai_luna/development_YYYYMMDD/development_live_runs.jsonl \
  --manifest results/openai_luna/development_YYYYMMDD/development_live_manifest.json \
  --report results/openai_luna/development_YYYYMMDD/preflight_report.json
```

Only a passed report permits freeze. It bound the development trace to the exact
source, task bank, protocol, and non-secret access configuration.

```bash
PYTHONPATH=src python -m fa_mas.bounded_e2e --mode freeze \
  --protocol configs/openai_single_e2e_v1.json \
  --access configs/openai_luna_preflight.json \
  --preflight-report results/openai_luna/development_YYYYMMDD/preflight_report.json

FA_MAS_OPENAI_API_KEY="$(security find-generic-password -a "$USER" -s "FA-MAS-OPENAI-EVAL" -w)" \
PYTHONPATH=src python -m fa_mas.bounded_e2e --mode live \
  --protocol configs/openai_single_e2e_v1.json \
  --access configs/openai_luna_preflight.json \
  --approve-spend-usd 2 \
  --output results/openai_luna/confirmatory_YYYYMMDD

PYTHONPATH=src python -m fa_mas.bounded_analysis \
  --runs results/openai_luna/confirmatory_YYYYMMDD/live_runs.jsonl \
  --manifest results/openai_luna/confirmatory_YYYYMMDD/live_manifest.json \
  --tasks configs/bounded_tasks_v1.jsonl \
  --output results/openai_luna/confirmatory_YYYYMMDD/analysis
```

The freeze created a configuration-specific lock and execution-start marker next
to the protocol. A complete live matrix was required before the analysis command
reported a confirmatory comparison. No automatic retries, provider switching,
or reruns are permitted after confirmatory execution starts.

## Development acceptance criteria

`fa_mas.preflight` passes only when all eight development policy/configuration
episodes finish without an operational error, preserve exactly one provider
tool call and its identifier per turn, contain an explicit model-selected
`finish`, demonstrate multiple non-finish operations, match the exact returned
model identity, retain valid usage accounting, and contain no credential-like
strings. It is an integration check, not a task-quality result.

If it had failed, the study would have stopped. The report passed; preserve it
and the development traces as development-only integration evidence.
