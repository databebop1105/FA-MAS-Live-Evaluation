# FA-MAS bounded end-to-end live study

Prepared 9 October 2026. Implementation and development verification are complete. **No live model calls or held-out model outcomes have been collected.** This is a locally prespecified protocol, not an independently registered experiment.

## What changed

The new runner lets a tool-calling model choose every operation from the initial task through completion or cleanup. It executes actual loopback HTTP calls into two separately implemented SQLite services. It replaces the former one-recovery-decision sandbox for this bounded study, while retaining the original unexecuted protocol as a separate historical plan. The manuscript must not report results from this study until live execution and auditing finish.

The first service executes a sequence of three or four persistent writes with stable intent keys, authoritative status reads, partial outcomes, compensation, and replacement. The second service allocates inventory holds and captures or releases them under SKU and capacity invariants. It uses its own stock/hold schema and handler. Initial background stock usage is included in the independent inventory judge, so another customer's inventory does not become a controller error.

A single tool-using model acts as the controller in each episode. This is end-to-end service workflow execution, not a test of multi-agent coordination or production providers. It evaluates hard contract enforcement, not the full proposed Recomposition Frontier, probabilistic diagnosis, or SLO optimization algorithm.

## Design

| Item | Prespecified choice |
|---|---|
| Services | Persistent-write workflow; inventory hold/capture/release |
| Development tasks | Four, excluded from the held-out matrix |
| Development live matrix | 4 tasks × 2 configurations × 2 policies = 16 non-confirmatory episodes; at most 192 model calls |
| Held-out tasks | 32: two parameter variants for each of eight scenario families in each service |
| Model-provider configurations | One named proprietary hosted configuration; one named open-weight configuration served through a pinned OpenAI-compatible endpoint |
| Policies | FA-MAS contract enforcement; feature-matched model controller without enforcement |
| Episodes | 32 tasks × two models × two policies = 128 |
| Sampling / reasoning | Development-validated per-configuration settings; temperature starts at 0.0, but is not described as guaranteed determinism |
| Per-episode limits | 12 model turns, 12 HTTP tool calls, 600-second elapsed limit checked between turns |
| Per-model-call limits | 16,000 UTF-8 request bytes, 512 billed output tokens, 45-second request timeout |
| Global upper bound | 1,536 model requests; additional approved USD ceiling enforced conservatively |
| Primary outcomes | Task completion, acceptable outcome, unsafe outcome |
| Secondary evidence | Safe termination, token usage, service calls, wall time, provider/runner status, contract rejections |
| Stopping | Preserve every launched episode; stop at budget exhaustion or three consecutive provider failures |
| Failure retries | No automatic provider-call retries; no reruns or post-response exclusions |

The held-out parameter variants differ from development in workflow length, requested SKU, and capacity. Scenario families are authored and known during implementation. This is held-out task-instance evaluation; it is not an unseen-fault benchmark or independently sampled real-world task population. The variants do not create 32 independent failure mechanisms.

The model receives the task, declared service contracts, tool schema, and observed responses. It receives no injected-fault name, private database state, test judge, or policy label. Both policies use the same system prompt, model, schemas, service capabilities, stable intent keys, permission scope, limits, and starting database state. Cells execute in a deterministic shuffled order. FA-MAS enforces substitute equivalence, prerequisite completion, safe replacement after compensation, and capture of an observed correct-SKU hold. The baseline may use every recovery operation and the same contract information, but its chosen actions are not subject to those extra gates. A strong model may voluntarily honor contracts under both policies; a null treatment effect is a valid result.

No controller receives automatic cleanup. A stopped episode with unresolved effects remains unsafe. A model's claimed completion cannot override the terminal judge. Safe termination is operationalized as a clean task-specific database state; provider failure before any write may therefore leave safe state, and the provider-failure count must be reported alongside the safety metric.

## Verification already run

- 44 unit tests pass across the full repository. New tests cover multi-step HTTP execution, model-selected reconciliation and replacement, independent cleanup verdicts, SKU gates, capacity invariants, provider failures, shared prompts and schema, budgets, task separation, protocol hashing, and live-only analysis.
- A loopback mock of an OpenAI-compatible provider performed four sequential calls with tool-response history and reconciled a lost hold reply. Its adapter was explicitly marked non-live; it made no real model requests.
- Eight development trajectories completed under scripted actions on both services and both policies. All rows remain `ci_non_live` and all task IDs belong to the development split.
- Live analysis rejects CI evidence, mixed locks, duplicate or incomplete matrices, different model identities, changed traces, and saved outcomes that disagree with the terminal database judge.

These checks validate the experiment infrastructure. They provide no evidence about live-model performance or acceptance likelihood.

## Analysis and interpretation

The primary contrast is FA-MAS minus the feature-matched controller within each task and named model-provider configuration. The primary report is configuration-specific: it does not present the two configurations as independent draws from a model population or as a proprietary-versus-open-weight causal comparison. Uncertainty resamples the service-by-scenario families within each configuration, retaining both task variants and policies together. Pooled and service-specific rows are descriptive sensitivities only. Exact cluster-sign randomization tests are supplementary and conditional on exchangeability; Holm adjustment covers the three outcomes within each scope. With only 16 authored clusters, intervals and tests describe this bank and do not establish population reliability. The study is bounded and has no demonstrated statistical power for small effects.

Provider failures, invalid responses, timeouts, and budget stops remain in the launched data. A partial matrix cannot enter the completed confirmatory comparison. Outcome rates must be accompanied by completion, safe-stop, unsafe-state, and operational-failure counts. No paper claim should promote this local service study into production reliability, general multi-agent superiority, or full-algorithm validation.

## Exact execution gate

The current environment has no hosted API key, pinned model settings, or supplied local inference endpoint. The runner cannot provision another person's credentials, account credits, or model server. To proceed, the author must make available:

1. The exact proprietary hosted model alias or snapshot, endpoint base including its API prefix, expected returned model ID, and `HOSTED_API_KEY` configured securely in the execution environment.
2. The exact open-weight model/revision, one pinned compatible provider endpoint, its expected returned model ID, and any required `OPEN_WEIGHT_API_KEY`.
3. Development checks confirming each endpoint accepts the frozen generic dispatcher, call-history serialization, one-action-per-turn behavior, and that model-selected operation arguments reach the service dispatcher unchanged. Explicit `finish` remains available to both policies.
4. Development checks confirming each configuration's sampling/reasoning and output-limit fields are accepted and logged, with no silent fallback. The runner records only frozen non-secret request options; options are not copied from one provider to another without validation.
5. Verified input/output billing rates, confirmation that the request-byte bound covers billed input tokens and the output parameter bounds all billed output/reasoning tokens, plus an explicitly approved USD ceiling. Independently billed server/GPU time is outside the token-cost calculation and needs its own authorization.

Use `configs/bounded_access.example.json` as the schema. Create the ignored `configs/bounded_access.local.json` for development attempts, then create a reviewed, credential-free `configs/bounded_access.frozen.json` for the freeze and confirmatory commands. Both files contain only model/provider settings and environment-variable names; API keys remain in environment variables and never enter files, locks, prompts, or logs. `base_url` must already include `/v1` if the server requires it: this runner appends `/chat/completions` once. Set `expected_response_model` when the server's returned ID differs from its requested model ID. `request_options` is a deliberately narrow per-configuration allowlist for the development-validated reasoning setting and parallel-tool-call control; it is included in the frozen manifest without credentials. `temperature` can be a finite non-negative value or `null` to omit the field only after a dated protocol amendment. The runner preserves the provider-issued tool-call ID in every assistant/tool message pair.

For each model, the maximum token-cost reservation for the complete matrix is:

`12.288 × input_USD_per_million + 0.393216 × output_USD_per_million`.

Sum both models' bounds to budget for the full study. A lower approved ceiling is allowed but may stop the study early, leaving an incomplete matrix. This bound is valid only under the verified billing assumptions; provider account limits remain the final financial control.

From the artifact root:

```bash
python -m pip install -e .
PYTHONPATH=src python -m fa_mas.bounded_e2e --mode validate
# Fill configs/bounded_access.local.json; set keys securely outside the command.
# Run this first. It only uses the four development fixtures and does not create
# the confirmatory execution marker or qualify for confirmatory analysis.
PYTHONPATH=src python -m fa_mas.bounded_e2e --mode development --access configs/bounded_access.local.json --approve-spend-usd DEVELOPMENT_USD --output results/bounded_e2e/development_YYYYMMDD
# Create and review configs/bounded_access.frozen.json from the validated
# non-secret settings. Set its two verification flags to true only after the
# development checks establish the billed-token and parameter guarantees.
PYTHONPATH=src python -m fa_mas.bounded_e2e --mode freeze --access configs/bounded_access.frozen.json
# Replace APPROVED_USD with the author's explicitly authorized positive ceiling.
PYTHONPATH=src python -m fa_mas.bounded_e2e --mode live --access configs/bounded_access.frozen.json --approve-spend-usd APPROVED_USD
PYTHONPATH=src python -m fa_mas.bounded_analysis
```

Development rows use a distinct evidence class and the analysis command rejects them. The local development access file may retain false verification flags while testing compatibility, but the reviewed frozen access file must carry true flags before `freeze` or `live` will proceed. Commit the frozen access file and generated lock, but never a credential-bearing local file. The confirmatory lock covers all package source, task bank, protocol, endpoint/model/rate settings, and Python/dependency versions. A global execution-start marker prevents a new output folder from authorizing a second confirmatory run. Any legitimate rerun requires a documented amendment; changing or deleting the marker is not a way to hide failed outcomes. After confirmatory live execution, audit raw state and usage, report negative results, and update the manuscript before making empirical live-model claims.
