# FA-MAS remaining-priorities verification

Evidence audit baseline: 9 October 2026. Live-study status updated 22 October
2026. This is not acceptance certification.

## Resolved in this revision

- Corrected three simulator defects: compensation without an existing uncertain effect, inconsistent selector/budget paths, and authorization detection masking unsafe execution. Historical defaults/source/results remain preserved.
- Executed a separate, explicitly post-audit 18,000-row corrected matched study. Unsafe rates: full 7.58%, no gates 9.67%, first feasible 8.93%, no compensation 7.60%. Full versus no compensation: −0.022 percentage points, conditional 95% interval −0.156 to +0.111. Compensation's aggregate benefit remains unresolved. These are authored simulator distributions, not live-model effects.
- Added 150 deterministic direct-tool checks over all 25 eligible cancellation tasks in pinned public tau2-bench retail/airline code. Both wrappers pass all retail cases. After lost airline replies, retry-first changes refund history in all seven cases; reconciliation preserves the one-write reference state. This is ledger divergence, not demonstrated net financial loss. No conversation, model, official benchmark reward or full policy evaluation was run.
- Retained upstream MIT notices, exact source/data hashes, reference-state snapshots, events and provenance.
- Installed 29 distributions into a fresh virtual environment using enforced
  wheel hashes. The recorded clean-install audit passed 44 tests; 52,500
  historical simulator rows, both 18,000-row matched studies and all 150
  public-tool traces reproduce byte for byte. The current source suite contains
  52 tests, including later non-live runner and portability coverage. This is
  same-host clean installation, not independent third-party replication.
- Added 18 hypothetical power-planning scenarios. Reference approximations flag poor sensitivity to a two-percentage-point difference. Inputs are assumptions; this is not observed power or the exact planned live statistical test.
- Completed a bounded live-model gate ablation: OpenAI GPT-6 Luna through Chat
  Completions completed an eight-trajectory development preflight, then 64
  frozen held-out local-service trajectories. All rows were retained: 52
  explicit finishes, 12 turn limits, and no provider or budget stops. Task
  success was unchanged; the +3.125-point acceptable-outcome and -3.125-point
  unsafe-outcome FA-MAS contrasts have 16-cluster intervals spanning zero.
- Updated the official-template manuscript, cover-letter draft, reproduction instructions and unconfirmed author-input form. The final PDF is 13 pages, within the checked 14-page ceiling; every page was visually inspected. This does not certify all final portal requirements.

## Remaining scientific work

1. Live study reporting: preserve the passed development report, exact lock,
   execution-start marker, 64 trajectory records, manifest, and terminal-state
   analysis. Describe this as one named model-provider configuration and a gate
   ablation, not a vendor comparison, external benchmark, or broad FA-MAS
   superiority result. Never put credentials in the manuscript or shared input
   form.
2. Power/generalization: 16 authored service/fault clusters cannot support population-level or adequately powered small-effect claims. Consider additional genuinely different service families before freezing; disclose amendments and cost. Public component checks reduce shared-source dependence but do not establish conversational generality.
3. Full architecture: subgraph enumeration, calibrated diagnosis and multi-agent coordination remain proposed. Current claims cover reduced gates and finite-action selection only.
4. Independent replication, a built container, archival DOI and rights-cleared artifact license remain absent. A pinned container recipe is supplied but was not built.

## Author-controlled submission facts

Confirm all authors/order/affiliations/contact information/contributions/consent; funding; conflicts; related and concurrent submissions; originality; artifact/data rights and license; AI-use disclosure. Existing title-page identity is inherited, not newly verified. Complete AUTHOR_SUBMISSION_INPUTS.json and AUTHOR_DECLARATIONS_TO_CONFIRM.md. The cover letter is a draft and was not sent. No submission was made.

## Evidence locations

Corrected study: results/matched_controls_v2. Public tools: results/external_services. Fresh-install record: results/clean_install_verification.json. Replay: results/evidence_verification.json. Planning: results/power_planning. Live preflight and matrix: results/openai_luna. Source/data pin: third_party/tau2/SOURCE.json. Reproduction: REPRODUCTION.md.

No acceptance guarantee is justified. The strongest supported case is transparent, reproducible mechanism evidence with preserved negative findings and explicit limits.
