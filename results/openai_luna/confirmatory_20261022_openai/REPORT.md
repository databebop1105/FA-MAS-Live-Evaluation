# OpenAI GPT-6 Luna bounded live gate ablation

## Scope

This one-time, locally frozen study evaluated FA-MAS against a feature-matched
gate ablation using OpenAI GPT-6 Luna through Chat Completions with
`reasoning_effort: "none"`, `temperature: 0.0`, a forced generic
`execute_service_action` tool, disabled parallel tool calls, and a 512-token
completion ceiling. The operation remained a model-selected tool argument.

The services are authored local HTTP/SQLite workflow and inventory
implementations. The study is not a vendor comparison, external benchmark,
production-service evaluation, repeated-sampling reliability study, or
multi-agent architecture evaluation.

## Integrity record

- Development preflight: 8 planned and 8 observed trajectories; passed.
- Frozen protocol digest:
  `ff14f48fe3b01871675395424de1cfd9e7a08f3742bcc80466c15e2eb32786e4`.
- Held-out matrix: 32 development-disjoint authored tasks × 2 policies = 64
  retained trajectories across 16 authored service/fault clusters.
- Execution: 607 model requests; 52 explicit finishes; 12 turn limits; zero
  provider failures; zero budget stops.
- Token accounting: USD 0.055423 usage-priced cost from reported token counts;
  USD 1.126592 conservative reservation under the approved USD 2 local ceiling.

`live_manifest.json` binds the trace hash, configuration, runtime, budget, and
protocol digest. `paired_comparisons.csv` is produced only after the separate
terminal-state auditor re-judges every saved final service state.

## Results

| Outcome | Feature-matched | FA-MAS | FA-MAS minus feature-matched | 16-cluster bootstrap interval |
|---|---:|---:|---:|---:|
| Task success | 18.75% | 18.75% | 0.000 points | 0.00 to 0.00 |
| Acceptable outcome | 90.625% | 93.75% | +3.125 points | -6.25 to +12.50 |
| Unsafe outcome | 9.375% | 6.25% | -3.125 points | -12.50 to +6.25 |

The supplementary cluster-sign tests, Holm-adjusted across these endpoints,
were 1.0. The data therefore do not support a reliable gate advantage in this
authored bank. Do not use the numerical direction as evidence of general
FA-MAS superiority.

## Artifact files

- `../development_20261022_openai/`: development-only live traces, manifest,
  and passed preflight report.
- `live_runs.jsonl`: sanitized trajectory records; no assistant free text or
  credential is retained.
- `live_manifest.json`: execution integrity and token-accounting record.
- `analysis/`: independently re-judged terminal outcomes and paired analysis.
- `configs/openai_single_e2e_v1_lock.json` and
  `configs/openai_single_e2e_v1_execution_started.json`: immutable freeze and
  launch markers.
