# FA-MAS reviewer-risk audit

**Audit date:** 22 October 2026
**Decision:** do not submit the current manuscript unchanged.

This is a submission-quality audit, not an acceptance prediction. It separates
defects that could invalidate the current artifact from limitations that must be
stated plainly. The intended venue welcomes LLM-enabled service orchestration,
reliability, and practical case studies. The manuscript is relevant, but its
current evidence reads primarily as a simulator and deterministic-controller
study. The decisive upgrade is one valid, bounded LLM-in-the-loop case study,
not a comparison of model vendors.

## The paper reviewers should receive

The central claim should be:

> FA-MAS is an action-time safety envelope for stateful service recovery. For
> the declared contract model and service assumptions, it prevents a controller
> from executing disallowed recovery effects, while exposing the resulting
> completion and safe-termination trade-offs.

This is intentionally narrower than claims of general FA-MAS superiority,
production reliability, exactly-once behavior, or multi-agent coordination.
The language model proposes actions. The controller and the independent terminal
judge determine whether those actions may execute and whether the resulting
state is safe.

## Risks and required disposition

| Priority | Reviewer risk | Evidence observed | Required disposition before submission |
|---|---|---|---|
| P0 | **Venue fit remains narrow.** The artifact now has one closed-loop live-model result, but only on authored local services. | OpenAI GPT-6 Luna completed all 64 frozen trajectories after a passed development preflight. The task-success contrast is zero and both nonzero primary contrasts have 16-cluster intervals spanning zero. | Report this as one bounded gate ablation; do not imply model-family, vendor, benchmark, or production superiority. |
| P1 | **Evidence labels must stay synchronized.** | The paper and artifact record the exact date, configuration, passed preflight, frozen-matrix completeness, and inconclusive audited result. | Recheck that wording against the lock, manifest, and analysis before final rendering and submission. Preserve development-only records as distinct evidence. |
| P0 | **Artifact portability was broken.** | A fresh run on the current SQLite build rejected double-quoted string literals in `inventory_services.py`, causing seven tests to fail. | Corrected on this branch by using SQL string literals that are portable across SQLite builds. Require the full suite to pass in a fresh environment before freezing any study. |
| P0 | **The no-gates condition is an ablation, not a competitive recovery system.** | It keeps the same controller and removes declared enforcement. A reduction in unauthorized effects can follow directly from the definition of the gate. | Call it a *gate ablation* throughout. Report its recovery, safe-termination, and false-blocking costs alongside blocked unsafe effects. Do not call it a broad recovery baseline. |
| P0 | **Authorship and submission declarations are incomplete.** | The artifact has unconfirmed authorship, contribution, funding, conflict, licensing, and originality inputs. | Obtain author-by-author approval, contribution statements, ORCIDs, funding/compute disclosure, conflicts, rights, and prior/concurrent-work confirmation. Do not infer any of these from repository history. |
| P1 | **The claimed architecture exceeds the implementation.** | Full recomposition, calibrated diagnosis, write-ahead/checkpoint behavior, and multi-agent coordination are proposed rather than exercised. | Put the implemented reduced controller in the contribution sentence and figures. Move the broader architecture to “design extensions” and delete any wording that implies validation. |
| P1 | **Historical simulator results are easy to misread as efficacy evidence.** | The manuscript already discloses unequal diagnosis, a weaker judge, a negative matched sensitivity, and post-audit corrected exploratory results. | Lead with the matched/corrected limitation, not the 52,500-row historical headline. Move the unequal-control table and figure to supplemental material or a compact audit sidebar. |
| P1 | **The live design has limited inferential scope.** | The task bank has 16 authored service/fault clusters; turns are dependent; policies can produce different trajectory lengths. | Use complete trajectories as outcomes. Pair task, initial state, fault schedule, and configuration; report configuration-specific cluster-resampled descriptive intervals. Do not use call-level tests or market it as a proprietary-versus-open-weight comparison. |
| P1 | **“Held out” may be misunderstood.** | The bank is authored, shares known fault families, and lives in the project artifact. | Describe it as *development-disjoint authored task instances*. Record who could inspect it before execution. It is not a blind external benchmark or a sample from a real task population. |
| P1 | **External evidence is narrower than its label can suggest.** | The tau2 work contains direct tool-level replay over public retail/airline components, not conversations or benchmark rewards. | Retain it as a reference-action compatibility check. Do not call it tau2-bench performance, a conversational benchmark, or real-world deployment validation. |
| P1 | **Reproducibility is not yet independent.** | Same-host clean installation and hashes are valuable, but are not an external reproduction. | Ask a non-author to follow the reproduction guide on a separate machine. Archive their command, platform, commit, result, and any divergence. Only then use the term “independent reproduction.” |
| P1 | **References and related-work claims remain high-risk.** | Several recent works are preprints and the manuscript itself says final citation verification remains required. | Verify every bibliographic record and every novelty/comparator claim against the primary publisher or official repository. Remove any unverified citation rather than relying on an AI-generated-looking reference list. |
| P1 | **AI-use disclosure must be precise.** | The acknowledgement identifies ChatGPT and Codex but makes a broad all-sections statement. | Keep an acknowledgement that names each system, identifies the sections/code/figures affected, states its drafting or implementation role, and confirms human authors verified all scientific content. IEEE requires disclosure of AI-generated article content. |
| P2 | **The paper is at 13 pages against a 14-page ceiling.** | A late method/result addition can cause overflow after template conversion. | Target 12.5-13 pages before final conversion. Use supplemental material for protocol detail, historical simulator tables, extended traces, and the complete evidence audit. |
| P2 | **Artifact and manuscript counts drift.** | The manuscript says 44 tests; the current source suite has 52 tests. | Generate counts and test-status wording from a final reproducibility manifest. Do not hand-edit these figures in multiple places. |
| P2 | **Release readiness is incomplete.** | No confirmed archival DOI, final license, built container, or release review. | Create a tagged, credential-free release after the final rerun. Add a clear license and archive only material that is legally redistributable. Keep secrets, raw provider payloads, and any protected evaluation material out of the public release. |

## Evidence that is already useful

The existing artifact is not empty. It already supports a modest but useful
claim: deterministic contract checks, reconciliation, and an independent
terminal-state judge expose unsafe recovery states that completion-only scoring
would miss. The corrected study's lack of a resolved compensation effect is a
strength when reported plainly: it shows the authors did not retain a preferred
claim after the audit.

The two local HTTP/SQLite services and the direct public-component checks help
demonstrate the mechanism. They do not prove model generality. Treat them as
the implementation and conformance layer underneath the live case study.

## Non-negotiable stop conditions

Do not launch a held-out run, revise claims upward, or submit until all of the
following are true:

1. A full fresh-environment test suite passes, including both local services.
2. Exactly one named model-provider configuration completes all development
   acceptance checks without hidden fallback or tool-history corruption.
3. The source, prompts, tasks, schemas, model identifier, request settings,
   costs, analysis code, and stopping rule are frozen before held-out execution.
4. The held-out matrix is complete or is reported as incomplete without an
   outcome comparison; no failed cells are silently rerun.
5. The independent terminal-state auditor agrees with the saved result rows.
6. The manuscript, repository, declarations, and supplementary artifact all
   use the same evidence labels and counts.

## What not to do

- Do not add a rushed external benchmark adapter merely to claim a benchmark.
- Do not replace model choices with a scripted recovery plan and call that a
  live-model result.
- Do not keep a two-provider comparison if one adapter is unstable.
- Do not relabel development calls as confirmatory or omit provider failures.
- Do not claim that a contract gate has demonstrated emergent model safety
  merely because it blocks an action the gate explicitly prohibits.

## Immediate remediation completed on this branch

The inventory-service SQL now uses single-quoted string literals. The full
52-test suite passes on Python 3.12 with the repository's local loopback
services. The repository records a bounded model-free conformance check: 406
paired schedules (812 executions) exercise finite action proposals and six
state-dependent witness traces; 105 FA-MAS blocks were recorded and no blocked
proposal reached a service. It also records one frozen, complete 64-trajectory
OpenAI GPT-6 Luna gate ablation. The latter adds model-in-the-loop evidence only
within the declared local semantics; its cluster-level contrasts are inconclusive.
