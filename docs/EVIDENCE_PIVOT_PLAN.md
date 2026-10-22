# FA-MAS evidence pivot plan

**Objective:** turn FA-MAS into a defensible bounded case study of LLM-directed
service recovery, without claiming a vendor comparison, production reliability,
or validation of the proposed multi-agent architecture.

## Target paper in one sentence

FA-MAS constrains an LLM's recovery proposals at action time using explicit
service contracts and independently audited state; the study measures which
unsafe effects are prevented and what completion or safe-termination cost that
enforcement introduces in two local stateful services.

## Evidence layers

| Layer | Question | What counts as evidence | What it cannot establish |
|---|---|---|---|
| 1. Contract conformance | Can a declared gate prevent an impermissible effect in the implemented controller? | Deterministic, bounded state/action/fault enumeration and independent terminal-state checks. | Natural model behavior, provider reliability, or production safety. |
| 2. Service mechanism | Does the controller operate against persistent state rather than only simulator variables? | Existing HTTP/SQLite workflow and inventory services; direct public-tool reference checks. | External benchmark performance or representative production failure rates. |
| 3. LLM integration | Can a real model select and execute actions through the generic dispatcher without bypassing the controller? | One named model-provider configuration that completes the development acceptance suite. | A population-level model comparison or multi-agent coordination. |
| 4. Bounded gate ablation | Under the same task, initial state, and fault schedule, what trade-off follows from enabling the gates? | One frozen held-out matrix with all launched episodes retained and independently judged. | Broad FA-MAS superiority, production reliability, or causal differences between model families. |
| 5. Independent reproduction | Can somebody outside the author team rerun the artifact? | A dated report from a non-author using a tagged release on a separate machine. | Generalization beyond the reproduced setup. |

Layers 1 and 2 are the paper's engineering foundation. Layers 3 and 4 make it
appropriate for the LLM-and-service-ecosystems special issue. Layer 5 makes the
artifact credible rather than merely available.

## Phase A - repair and freeze the deterministic foundation

**Deliverables**

1. Keep the SQLite portability fix and record the final full-suite result.
2. Completed: `fa_mas.conformance` enumerates finite schema-valid one-action
   proposals at empty local state for every authored service/fault family,
   together with six state-dependent witness traces. It records proposed
   action, gate decision, executed action, terminal state, and invariant
   verdict. The v1 report contains 406 paired schedules / 812 executions.
3. Make the auditor independent of the controller's success flag. A controller
   declaration of completion must never create a successful result.
4. Completed: the generated, machine-readable report is committed under
   `results/conformance_v1`. The manuscript still needs a concise table:
   property, service, fault family, traces explored, violations detected,
   violations executed by FA-MAS, and expected safety-preserving blocks.

**Paper wording**

Use conditional language: “Under the declared contracts and local-service
semantics, no enumerated FA-MAS trace executed a gated-forbidden effect.” Do
not translate bounded enumeration into “FA-MAS guarantees production safety.”

## Phase B - establish one valid LLM integration

Use **one** named model-provider configuration. The hosted OpenAI configuration
is the only candidate currently worth considering because the Together/Qwen
configuration did not clear development preflight. Do not switch models or
providers repeatedly after observing held-out outcomes.

Development acceptance is about the integration, not about achieving a good
task score. All of the following must be true across the four development
fixtures and both policy arms:

- the exact pinned model identity is returned;
- the endpoint accepts only the frozen request fields;
- each assistant-tool-assistant cycle preserves the provider tool-call ID;
- the model can select multiple distinct operations, including explicit finish;
- the dispatcher follows the tool arguments rather than substituting a scripted
  action;
- malformed arguments, refusals, empty output, truncation, rate limits, and
  timeouts are retained as operational outcomes;
- output/reasoning token accounting and local reservations stay below the
  approved ceiling; and
- no response, tool observation, error record, or artifact contains a secret
  or unredacted provider payload.

If the model's own proposed action is rejected by an explicit contract, that is
a valid experimental event. If the provider emits unusable tool calls or the
adapter cannot serialize the continuation, that is a failed integration check,
not a negative FA-MAS result.

## Phase C - frozen one-configuration gate ablation

After Phase B passes, amend the protocol before execution to name a **single
model-provider configuration** and retain the 32 development-disjoint authored
task instances. The resulting matrix is 32 tasks x 2 policies = 64 complete
trajectories, at most 768 model turns under the current limits.

The only intended policy difference is enforcement of the declared contract
gates. Both arms must have the same:

- model, system prompt, tool schema, observations, termination operation,
  budgets, state reset, and fault schedule;
- recovery operations, including reconciliation, compensation, release, and
  replacement; and
- independent terminal-state judge.

Predeclare one primary outcome: **any audited unsafe executed effect per
trajectory**. Report task completion, acceptable outcome, safe termination,
attempted unsafe actions, blocked actions, actual unsafe effects, provider
failures, token use, and turn counts as secondary outcomes. Pair the two arms
within task/fault family and report configuration-specific, cluster-resampled
descriptive uncertainty. With 16 authored clusters, statistical significance
is supplementary at most.

The results section must say that a safety difference is expected when a gate
blocks a predefined disallowed action. Its scientific value is the measured
trade-off under live model proposals and real persistent service state, not a
claim that the gate discovered safety autonomously.

## Phase D - manuscript reconstruction

The main paper has a 14-page ceiling. Reserve space for the following rather
than adding more historical simulator detail.

| Manuscript element | Change |
|---|---|
| Title | Prefer “Contract-Aware Recovery for LLM-Directed Stateful Service Workflows: An Audited Safety-Envelope Case Study.” |
| Abstract | Lead with the safety-envelope problem, the implemented controller, independent state judge, bounded conformance result, and one-configuration live case study. State the limits in one clear sentence. |
| Introduction | State the exact contribution before the background: model proposals are constrained at action time; this is not a multi-agent or provider-comparison paper. |
| Method | Separate proposed architecture from implemented controller. Make the contract, gate, event log, and terminal judge precise. |
| Evaluation | Give the bounded conformance table and the live gate-ablation table priority. Move the unequal historical simulator table/figure and extensive protocol minutiae to supplemental material. |
| Results | Report the live outcome matrix honestly, including gate costs and operational failures. Keep the negative compensation result. |
| Discussion | State that the no-gates arm is a gate ablation, the services/tasks are authored, and the study does not estimate real-world reliability. |
| Reproducibility | Give the tagged artifact, environment, independent rerun status, and reproducibility limits. |

Mandatory manuscript correction: replace “No live model calls have been made”
with an accurate development-versus-held-out statement. Example:

> Development-only provider compatibility checks were performed before protocol
> freeze. They did not qualify an additional configuration for held-out
> analysis; consequently, no outcome from those checks is reported as evidence.

Use this only while it remains factually accurate. If a configuration later
passes and the frozen matrix is run, replace it with the exact date, model
configuration, protocol lock, and audited result status.

## Phase E - external scrutiny before submission

1. Have a non-author reproduce the release on another machine.
2. Audit every citation against its primary source and check each novelty claim
   against the verified related work.
3. Confirm author order, contributions, affiliations, funding, conflicts,
   originality, prior/concurrent work, data rights, artifact license, and
   ORCIDs directly with every author.
4. Make the AI acknowledgement precise: identify ChatGPT/Codex, the exact
   sections/code/figures it helped draft, its role, and the authors' independent
   verification. AI systems are not authors.
5. Compile the final template and keep it below the 14-page submission limit,
   with enough margin for final template reflow.

## Go / no-go decision

**Go for this special issue only if:** the deterministic conformance layer,
one valid LLM configuration, frozen complete trajectory matrix, and author
declarations are all complete and auditable.

**No-go or venue pivot if:** the single configuration cannot pass development
acceptance soon enough, the held-out task bank is contaminated by implementation
tuning, or the manuscript cannot honestly make an LLM-in-the-loop claim. In
that case, the work can still become a narrower service-recovery/controller
artifact paper, but it is not yet a strong match for this LLM special issue.
