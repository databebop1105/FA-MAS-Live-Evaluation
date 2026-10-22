# Development amendment: open-weight model-provider configuration

**Date:** 2026-10-22
**Status:** Development-only amendment; not a confirmatory protocol freeze

## Reason

The originally selected Together configuration, `openai/gpt-oss-120b`, did
not satisfy the pre-freeze multi-turn tool-use acceptance check. In bounded
development runs, it returned no tool call on later turns under the fixed
generic dispatcher. These local development records are not confirmatory
evidence and will not be analyzed or reported as such.

## Replacement candidate

The candidate configuration is Together serverless
`Qwen/Qwen3.5-9B`, an open-weight Apache-2.0 model. Together's current
catalog marks this exact model as supporting function calling, and its
multi-turn function-calling guide uses the same model in a tool-result
continuation example.

- Endpoint: `https://api.together.xyz/v1`
- Input/output prices recorded for development: $0.17 / $0.25 per million
  tokens
- Temperature: `0.0`
- Request options: `parallel_tool_calls: false`
- Reasoning setting: none sent
- Tool contract: the unchanged, forced generic `execute_service_action`
  dispatcher with model-selected operation arguments

Sources consulted on 2026-10-22:

- https://docs.together.ai/docs/serverless/models
- https://docs.together.ai/docs/inference/function-calling/agentic
- https://huggingface.co/Qwen/Qwen3.5-9B

## Invariants and acceptance rule

This amendment changes only the named open-weight model-provider
configuration. It does not change the task bank, services, generic schema,
policies, gates, outcomes, scoring, clustering, or analysis plan.

The candidate is eligible for a frozen confirmatory run only if a fresh,
development-only 16-episode matrix completes and both configurations satisfy
every item in the pre-freeze checklist. In particular, it must complete
multiple assistant-tool-assistant turns with valid tool-call IDs, expected
model identity, bounded token usage, and no systematic truncation or malformed
tool response. Failure ends the live-model study; it does not trigger an
unreported model substitution or held-out retry.

Until those checks pass, `configs/bounded_access.local.json` remains an
ignored local development file and no frozen access configuration exists.
