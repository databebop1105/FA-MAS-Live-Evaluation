# Pre-freeze live-evaluation checklist

This checklist applies only to the active single-configuration bounded
live-model gate-ablation study. It does not authorize a held-out run by itself.

## Development-only acceptance checks

- [ ] The named OpenAI GPT-6 Luna endpoint accepts the generic
  `execute_service_action` tool with `reasoning_effort: "none"`,
  `temperature: 0`, the 512-token output limit, disabled parallel tool calls,
  and one returned tool call per turn. Preserve the provider-issued tool-call
  ID in the corresponding tool response.
- [ ] The configuration completes multiple assistant-tool-assistant turns,
  preserves tool-call IDs, returns usable token counts, and reports the exact
  expected model identity.
- [ ] The four development tasks complete with resettable service state. Record
  malformed arguments, refusals, truncation, tool-call cardinality, provider
  failures, and all token usage.
- [ ] Development failure records retain only a bounded, scrubbed provider error
  code/message. Never retain authorization headers, API keys, or raw provider
  response bodies in files that could be shared.
- [ ] For a rejected model response, retain only a safe response shape: a
  recognized finish category, bounded tool-call count, content-present flag,
  and names (not values) of supported reasoning fields. The response-shape
  summary must exclude assistant text, tool arguments, opaque reasoning, and
  provider response identifiers.
- [ ] The 512-token output limit produces valid actions. Any limit or
  reasoning-setting change is a dated protocol amendment made before freezing.
- [ ] The 16,000-byte request cap is verified as an upper bound on billable
  input tokens, and the configured output cap is verified to bound every billed
  output/reasoning token.
- [ ] A local budget reservation covers development and every possible
  held-out request. Provider hard limits are an additional control, not the
  sole cost guard.
- [ ] `fa_mas.preflight` produces a passed, immutable report with the exact
  development trace hash and source/configuration hash. A failure report is a
  stop condition, not a prompt to modify held-out tasks.

Run these checks only through `--mode development`, which executes eight
development-only policy/configuration episodes and cannot enter confirmatory
analysis. Give it its own explicit USD 1 ceiling and a new output directory for
each development attempt.

## Freeze only after every check passes

- [ ] Preserve and inspect the passed preflight report produced by
  `fa_mas.preflight`. It binds the model ID, endpoint, request options, output
  parameter, prices, source, task bank, and development trace to the freeze.
- [ ] Freeze the source, task bank, generic tool schema, prompts, policies,
  pricing, retry/stopping rules, cluster map, and analysis plan.
- [ ] Commit the configuration-specific generated lock with the eventual result
  artifact. Do not commit API keys or a credential-bearing local file.
- [ ] Run the held-out matrix exactly once. Retain every launched episode,
  including provider failures and budget stops.

## Reporting boundary

Report the named OpenAI configuration's gate contrast only. The pooled and
service-specific rows are descriptive. Do not claim broad model family,
production, external-benchmark, or multi-agent superiority.
