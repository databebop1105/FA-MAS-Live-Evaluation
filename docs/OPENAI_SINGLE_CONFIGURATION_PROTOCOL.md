# OpenAI single-configuration protocol

**Status:** prepared for development preflight; no qualifying preflight or
held-out outcome has been recorded.

This is the active live-evaluation protocol for the submission-week study. It
replaces the earlier two-provider confirmatory plan, which is retained only as
historical development documentation. The study still evaluates FA-MAS; the
named OpenAI model is only the action proposer.

## Named configuration

| Field | Frozen candidate for preflight |
|---|---|
| Provider | OpenAI |
| Model | `gpt-6-luna` |
| Endpoint | Chat Completions at `https://api.openai.com/v1` |
| Function-calling reasoning setting | `reasoning_effort: "none"` |
| Tool interface | Forced generic `execute_service_action`; operation remains a model-selected argument |
| Sampling | `temperature: 0.0` during preflight; acceptance depends on the endpoint accepting it |
| Output ceiling | `max_completion_tokens: 512` |
| Parallel tool calls | disabled |

OpenAI documents that GPT-6 Luna supports function calling through Chat
Completions with `reasoning_effort` set to `none`. The preflight must still
establish that the exact request fields and continuation serialization work for
this account and endpoint. No model alias, provider, parameter, or fallback is
changed after a held-out result is observed.

## Matrix and cost ceilings

| Stage | Matrix | Maximum calls | Conservative token-price reservation |
|---|---:|---:|---:|
| Development preflight | 4 tasks × 2 policies | 96 | USD 0.178176 |
| Confirmatory gate ablation | 32 tasks × 2 policies | 768 | USD 1.425408 |
| Both stages | — | 864 | USD 1.603584 |

The reservations use the frozen 16,000-byte input ceiling, 512 completion-token
ceiling, and current configuration rates of USD 0.10/M input and USD 0.50/M
output. They are local conservative limits, not a provider invoice guarantee.
The development command uses an explicit USD 1 ceiling; a complete
confirmatory run requires an explicit USD 2 ceiling.

## Exact sequence

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

Only a passed report permits freeze. It binds the development trace to the
exact source, task bank, protocol, and non-secret access configuration.

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

The freeze creates a configuration-specific lock and execution-start marker
next to the protocol. A complete live matrix is required before the analysis
command will report a confirmatory comparison. No automatic retries, provider
switching, or reruns are permitted after confirmatory execution starts.

## Development acceptance criteria

`fa_mas.preflight` passes only when all eight development policy/configuration
episodes finish without an operational error, preserve exactly one provider
tool call and its identifier per turn, contain an explicit model-selected
`finish`, demonstrate multiple non-finish operations, match the exact returned
model identity, retain valid usage accounting, and contain no credential-like
strings. It is an integration check, not a task-quality result.

If it fails, stop. Preserve the report and development traces, explain the
failure in the artifact, and do not freeze or run the 64 confirmatory episodes.
