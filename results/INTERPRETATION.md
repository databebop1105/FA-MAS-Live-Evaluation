# Pilot interpretation and go/no-go decision

## What was run

The artifact executed 10,500 deterministic, paired-seed observations over two
stateful workflow domains, seven fault classes plus no-fault controls, two fault
intensities, seven baselines, and five FA-MAS ablations. Each stochastic cell has
30 repetitions. These are simulator results, not measurements from live LLMs or
external services.

## Headline finding

The preregistered reliability hypothesis is not supported by this pilot's current
mechanism and outcome definition. FA-MAS achieved lower aggregate task success
than the strongest adaptive baselines, while reducing unsafe side effects from
roughly 9.4–10.6% for adaptive baselines to 5.2%. Raw task success penalizes safe
security abstention as failure, creating a real reliability-versus-safety tradeoff.

The `no_compensation` ablation produced higher completion than the full system.
Inspection explains why: compensation restores a safe state but the prototype
does not yet recompose and resume the compensated step. This is a prototype gap,
not evidence that compensation is undesirable.

## Required changes before the confirmatory experiment

1. Freeze separate primary outcomes for goal completion, safe termination, and
   utility-weighted acceptable outcome. Never relabel the pilot retrospectively.
2. Implement `compensate -> reconcile -> substitute/recompose -> resume` rather
   than treating compensation as terminal.
3. Add real service adapters and at least two version-pinned LLM planners. Retain
   the deterministic simulator as an oracle-controlled unit benchmark.
4. Calibrate detection and recovery probabilities from pilot traces or an
   independently labeled development set rather than hand-set parameters.
5. Add Holm correction for the primary comparison family and mixed-effects
   models with task/model random effects for the confirmatory analysis.
6. Record semantic and state ground truth at each step, then audit a blinded
   sample of success and failure labels.

## Publication boundary

These pilot numbers may be reported as simulator validation or used for debugging
the evaluation harness. They should not be presented as evidence that FA-MAS
outperforms real agent systems. A TSC empirical claim requires the confirmatory
live-model/service experiment above.
