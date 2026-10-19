# FA-MAS prespecified simulator report

**Evidence boundary:** controlled stochastic service simulation; not live LLM or production-service evidence.

Run-level observations: **52,500**.

## Headline aggregates

| baseline | success | acceptable | safe_termination | slo | unsafe | latency | cost |
| --- | --- | --- | --- | --- | --- | --- | --- |
| fa_mas | 0.850 | 0.884 | 0.034 | 0.850 | 0.049 | 783.566 | 7.779 |
| react | 0.832 | 0.832 | 0.000 | 0.832 | 0.110 | 755.415 | 7.556 |
| replan | 0.860 | 0.860 | 0.000 | 0.860 | 0.098 | 780.236 | 7.777 |
| retry | 0.821 | 0.821 | 0.000 | 0.821 | 0.119 | 747.202 | 7.471 |
| self_heal | 0.866 | 0.866 | 0.000 | 0.866 | 0.091 | 783.104 | 7.817 |
| static | 0.757 | 0.757 | 0.000 | 0.757 | 0.172 | 706.760 | 7.068 |
| unconstrained | 0.863 | 0.863 | 0.000 | 0.863 | 0.093 | 781.361 | 7.800 |

## Paired primary comparisons

| baseline | metric | effect_fa_mas_minus_baseline | ci_low | ci_high | mcnemar_exact_p | fa_only_success | baseline_only_success | n_pairs | holm_p |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| static | task_success | 0.0933 | 0.0847 | 0.1018 | 0.0000 | 420 | 0 | 4500 | 0.0000 |
| static | acceptable_outcome | 0.1276 | 0.1176 | 0.1373 | 0.0000 | 574 | 0 | 4500 | 0.0000 |
| static | slo_attained | 0.0933 | 0.0851 | 0.1018 | 0.0000 | 420 | 0 | 4500 | 0.0000 |
| static | unsafe_side_effect | -0.1238 | -0.1333 | -0.1144 | 0.0000 | 0 | 557 | 4500 | 0.0000 |
| retry | task_success | 0.0291 | 0.0204 | 0.0376 | 0.0000 | 255 | 124 | 4500 | 0.0000 |
| retry | acceptable_outcome | 0.0633 | 0.0547 | 0.0720 | 0.0000 | 359 | 74 | 4500 | 0.0000 |
| retry | slo_attained | 0.0291 | 0.0204 | 0.0378 | 0.0000 | 255 | 124 | 4500 | 0.0000 |
| retry | unsafe_side_effect | -0.0702 | -0.0778 | -0.0627 | 0.0000 | 0 | 316 | 4500 | 0.0000 |
| react | task_success | 0.0184 | 0.0102 | 0.0264 | 0.0000 | 228 | 145 | 4500 | 0.0001 |
| react | acceptable_outcome | 0.0527 | 0.0440 | 0.0611 | 0.0000 | 324 | 87 | 4500 | 0.0000 |
| react | slo_attained | 0.0184 | 0.0102 | 0.0269 | 0.0000 | 228 | 145 | 4500 | 0.0001 |
| react | unsafe_side_effect | -0.0616 | -0.0691 | -0.0549 | 0.0000 | 0 | 277 | 4500 | 0.0000 |
| replan | task_success | -0.0096 | -0.0187 | -0.0007 | 0.0459 | 200 | 243 | 4500 | 0.0459 |
| replan | acceptable_outcome | 0.0247 | 0.0156 | 0.0340 | 0.0000 | 282 | 171 | 4500 | 0.0000 |
| replan | slo_attained | -0.0096 | -0.0184 | -0.0004 | 0.0459 | 200 | 243 | 4500 | 0.0459 |
| replan | unsafe_side_effect | -0.0498 | -0.0569 | -0.0427 | 0.0000 | 29 | 253 | 4500 | 0.0000 |
| self_heal | task_success | -0.0158 | -0.0249 | -0.0062 | 0.0009 | 186 | 257 | 4500 | 0.0026 |
| self_heal | acceptable_outcome | 0.0184 | 0.0093 | 0.0284 | 0.0001 | 271 | 188 | 4500 | 0.0001 |
| self_heal | slo_attained | -0.0158 | -0.0247 | -0.0067 | 0.0009 | 186 | 257 | 4500 | 0.0026 |
| self_heal | unsafe_side_effect | -0.0420 | -0.0489 | -0.0351 | 0.0000 | 30 | 219 | 4500 | 0.0000 |
| unconstrained | task_success | -0.0129 | -0.0222 | -0.0038 | 0.0066 | 192 | 250 | 4500 | 0.0133 |
| unconstrained | acceptable_outcome | 0.0213 | 0.0120 | 0.0309 | 0.0000 | 281 | 185 | 4500 | 0.0000 |
| unconstrained | slo_attained | -0.0129 | -0.0222 | -0.0038 | 0.0066 | 192 | 250 | 4500 | 0.0133 |
| unconstrained | unsafe_side_effect | -0.0440 | -0.0511 | -0.0373 | 0.0000 | 30 | 228 | 4500 | 0.0000 |

## FA-MAS ablations

| ablation | task_success | acceptable_outcome | safe_termination | slo_attained | unsafe_side_effect | latency_ms | cost_units | detected | localized |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| fixed_rules | 0.816 | 0.852 | 0.037 | 0.816 | 0.059 | 772.919 | 7.682 | 0.220 | 0.198 |
| full | 0.840 | 0.876 | 0.037 | 0.840 | 0.052 | 783.910 | 7.778 | 0.220 | 0.198 |
| no_compensation | 0.880 | 0.916 | 0.037 | 0.880 | 0.054 | 787.438 | 7.849 | 0.220 | 0.198 |
| no_provenance | 0.840 | 0.876 | 0.037 | 0.840 | 0.052 | 783.910 | 7.778 | 0.220 | 0.158 |
| no_semantic_contracts | 0.847 | 0.883 | 0.037 | 0.847 | 0.066 | 779.017 | 7.765 | 0.198 | 0.178 |
| no_substitution | 0.816 | 0.852 | 0.037 | 0.816 | 0.059 | 772.919 | 7.682 | 0.220 | 0.198 |

Primary outcomes and analysis were loaded from `configs/confirmatory_simulator_v2.yaml`. Seeds are paired across systems. Confidence intervals are paired bootstrap 95% intervals; p-values are two-sided exact McNemar tests for paired binary outcomes with Holm correction within each metric family.