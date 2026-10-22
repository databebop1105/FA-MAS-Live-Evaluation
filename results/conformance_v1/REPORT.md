# Bounded contract-conformance report

This is a model-free, bounded conformance check of the implemented controller. It enumerates schema-valid one-action proposals at empty local state for every authored fault family, plus fixed state-dependent witness traces. It is not a model evaluation, external benchmark, production-service test, or unbounded proof.

## Summary

- Paired schedules: 406
- Executions: 812
- FA-MAS gate blocks: 105
- Blocked proposals dispatched to a service: 0
- Baseline unsafe terminal outcomes: 107
- FA-MAS unsafe terminal outcomes: 24

A zero dispatched-blocked-action count demonstrates only that the implemented gate stopped the proposal before its service call under this finite enumeration. It is not a production-safety guarantee. Differences between the two policy counts are properties of the declared gate ablation, not an estimate of model or deployment performance.

## Gate-block reasons

- Contract rejected: alternate does not satisfy the requested effect: 9
- Contract rejected: prerequisite is not observed committed: 61
- Contract rejected: replacement requires observed original compensation: 16
- Contract rejected: requested SKU hold not observed: 19

## State-dependent witnesses

| Witness trace | Baseline unsafe | FA-MAS unsafe | FA-MAS safe termination | FA-MAS gate blocks |
|---|---:|---:|---:|---:|
| `inventory-capture-without-observed-hold` | 0 | 0 | 1 | 1 |
| `inventory-reconcile-before-capture` | 0 | 0 | 0 | 1 |
| `inventory-wrong-sku-alternate` | 1 | 0 | 1 | 2 |
| `workflow-incompatible-alternate` | 1 | 0 | 1 | 1 |
| `workflow-prerequisite-step-2` | 1 | 0 | 1 | 1 |
| `workflow-replacement-before-compensation` | 1 | 0 | 1 | 1 |

Every row, proposal, gate decision, service observation, terminal state, and trace digest is retained in `conformance_traces.jsonl`.
