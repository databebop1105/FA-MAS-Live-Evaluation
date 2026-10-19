# Pre-freeze live-evaluation checklist

This checklist applies only to the bounded live-model gate-ablation study. It
does not authorize a held-out run by itself.

## Development-only acceptance checks

- [ ] The hosted endpoint accepts the generic `execute_service_action` tool
  with `reasoning_effort: "none"`, `temperature: 0`, the frozen output limit,
  and one returned tool call per turn.
- [ ] The selected open-weight endpoint accepts the same generic tool schema.
  Record only provider-supported reasoning and parallel-tool options; do not
  copy hosted-model options without a successful development test.
- [ ] Each provider completes multiple assistant-tool-assistant turns,
  preserves tool-call IDs, returns usable token counts, and reports the
  expected model identity.
- [ ] The four development tasks complete with resettable service state. Record
  malformed arguments, refusals, truncation, tool-call cardinality, provider
  failures, and all token usage.
- [ ] The 512-token output limit is retained only if both configurations
  produce valid actions. Any limit or reasoning-setting change is a dated
  protocol amendment made before freezing.
- [ ] The 16,000-byte request cap is verified as an upper bound on billable
  input tokens for each provider, and the configured output cap is verified to
  bound every billed output/reasoning token.
- [ ] A local budget reservation covers development, retries, and every
  possible held-out request. Provider hard limits are an additional control,
  not the sole cost guard.

## Freeze only after every check passes

- [ ] Fill a non-secret access configuration with exact model IDs, endpoints,
  expected returned IDs, token prices, output parameter names, and verified
  request options.
- [ ] Freeze the source, task bank, generic tool schema, prompts, policies,
  pricing, retry/stopping rules, cluster map, and analysis plan.
- [ ] Commit the frozen configuration and generated lock. Do not commit API
  keys.
- [ ] Run the held-out matrix exactly once. Retain every launched episode,
  including provider failures and budget stops.

## Reporting boundary

Report gate contrasts separately for each named model-provider configuration.
The pooled and service-specific rows are descriptive. Do not claim broad model
family, production, external-benchmark, or multi-agent superiority.
