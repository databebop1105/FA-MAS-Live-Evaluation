# Development amendment: Qwen assistant tool-call continuation

**Date:** 2026-10-22

**Status:** Final development-only adapter correction; not a confirmatory
protocol freeze

## Reason

The Qwen candidate development matrix recorded provider failures after valid
initial tool calls. The runner permits a provider-returned `content: null`
field to be forwarded unchanged in the assistant tool-call message; the safe
diagnostic record deliberately does not retain the raw field value. Together's
published Qwen multi-turn example instead sends an explicit `content: ""`
alongside the assistant tool call before appending the tool result.

This amendment tests that documented wire-format difference. It does not
reinterpret a free-text response as an action, discard a failure, or change
the generic dispatcher.

## Change

For the named Qwen development configuration only, set
`assistant_tool_content` to `empty_string`. The adapter will send
`content: ""` in its next assistant tool-call history message, regardless of
whether the provider returned null or omitted content. The value is constant,
transient, and never written to result records.

The model ID, endpoint, prices, output limit, temperature, tool schema,
forced dispatcher, policies, services, task bank, gates, scoring, and analysis
plan are unchanged.

Source consulted on 2026-10-22:

- https://docs.together.ai/docs/inference/function-calling/agentic

## Decision rule

The earlier Qwen development matrix is retained as a pre-adapter diagnostic
and cannot be used as evidence. A fresh development-only matrix will test this
single correction. It remains ineligible for a confirmatory freeze unless the
open-weight configuration completes its development episodes without provider
failures, malformed tool responses, or output-cap truncation, and the complete
pre-freeze checklist is satisfied for both configurations.

If this correction fails, no further model or adapter changes will be made for
this submission. The live-model study will be deferred and no live-model
outcome will be reported.
