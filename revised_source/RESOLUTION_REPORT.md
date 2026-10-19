# FA-MAS resolution report — 11 October 2026

Status: checked research draft, not ready to submit. No live outcomes, funding facts, author assent, license grant or DOI were inferred from the supplied audit.

## Completed and verified

- Compiled the official IEEEtran 1.8b journal/compsoc branch locally, rather than the preview fallback. Final document: 14 pages including references. No undefined references or overfull boxes. All rendered pages visually checked. Filling declarations or adding content requires a new build/page check.
- Preserved the strengthened Proposition 1 finality assumption. Definition 2 now requires final non-commit, and implementation limits explicitly exclude late in-flight commits/fencing/eventual consistency. This is a specification argument, not a newly validated controller guarantee.
- Corrected the proposed dominance relation to include SLO-violation probability. The implemented selector remains four-dimensional with no probability estimate and lambda_V=0. No software results were relabeled as validation of the broader objective.
- Replaced ambiguous implemented “recomposition” with alternate invocation at the same workflow step; full subgraph and multi-agent execution remain design only.
- Clarified the simulator's abstract security-denial flag. Tenant identities, scope resolution, and data residency are not claimed as simulated.
- Explained identical ablation arms with paired raw-row comparisons and independent local regeneration. First-feasible/no-compensation have zero changed rows; full has 173 and no-gates 661. “Independent” here means recomputing each arm separately on this host, not an outside team's reproduction. Shared unchanged arms do not constitute extra evidence.
- Added all-run diagnosis and SLO attainment for all three full-policy studies; complete outcomes for every policy are in complete_outcomes.csv. Added the corrected full-minus-first-feasible unsafe interval: −1.356 percentage points, conditional 95% interval −1.733 to −1.022.
- Defined the conditional paired bootstrap (2,000 matched-study resamples), with fixed authored cells/parameters/seeds. Historical analysis uses its separately stated 3,000 resamples.
- Reported every inventory policy, including FA-MAS's tie with stable-key retry, and explained partial policy display in Fig. 4.
- Redrew Fig. 2 using the protocol's state names, including SafelyTerminated and Escalated; it shows selected proposed transitions, not a complete implemented machine.
- Current local rerun: 44 tests pass; 52,500 historical and both 18,000 matched studies replay byte for byte. Separately regenerated 72 single-step, 135 workflow and 35 inventory HTTP rows (242 total) byte for byte. See http_regeneration.json and arm_comparison.json.
- Removed unsupported blanket assertions of completed human review and unspecified model/version identities from the AI statement. Historical ChatGPT/Codex version details were not recorded. The supplied Claude identifier remains explicitly attributed to the supplied report, not authenticated here.

## Reference and pricing checks

The Li paper exists and its arXiv abstract supports the episode count, ledger grading, late-commit impossibility boundary and overclaiming statistic: https://arxiv.org/abs/2609.29095. Mansoor's cited record resolves: https://arxiv.org/abs/2608.02645. Full-text retrieval failed here; unsupported claims that these works lack compensation/selection were removed rather than inferred from abstracts.

McNemar metadata matches the primary publisher record (https://link.springer.com/article/10.1007/BF02295996). Holm matches the archived original (https://www.jstor.org/stable/4615733). The Efron/Tibshirani citation retains the original 1993 edition; the current publisher landing page exposes a 1994 edition. An exhaustive independent semantic audit of all 50 entries has NOT been completed in this session. The supplied audit is useful evidence, not human sign-off or proof that every characterization is verified. In particular, full-text claims about DART, Cordon and ACRFence, venue upgrades and current specification versions still merit author checking.

The official OpenAI developer pricing table retrieved today lists standard short-context input/output rates of $2/$10 per million for gpt-6.1-sol and $0.10/$0.50 for gpt-6-luna (https://developers.openai.com/api/docs/pricing). Under the supplied 768-calls-per-model, 15,000-input/800-output assumption, estimated cost is $30.6432, not a guaranteed cap. Reasoning tokens, context growth, retries and rate classes require configuration and a verified ceiling. A recommendation to approve $150 is not approval. More importantly, two hosted models do not satisfy the existing one-hosted/one-open-weight protocol. They require a disclosed pre-freeze amendment if chosen. No model requests were made; no recognized API credential variable was present.

## Author-controlled inputs still needed

1. Confirm both author identities, affiliations, e-mails, order and corresponding author; actual contributions; Shivam Desai's assent; both authors' final approval; both ORCIDs.
2. Actual funding, conflicts, originality/related or concurrent submissions, and artifact rights. “No funding” and “no conflicts” cannot be filled from a recommendation.
3. Choose an artifact license only if both authors can grant the rights. Upstream MIT remains upstream MIT. Authorize publication through an accessible account if a DOI/public release is wanted. No Zenodo/GitHub publication, DOI or container build was performed here.
4. For a live run: legitimate credentials/endpoints, pinned model IDs/classes, applicable rates and an explicit approved maximum spend. Or explicitly choose descriptive model-free submission. Do not insert keys in this package.

The byline supplied in the upload is retained for review but does not establish authorship consent. Red placeholders remaining: two e-mails, funding (each in both class branches) and artifact DOI/URL. Known acronym expansion was filled from the established project direction. No portal submission or outside-team reproduction has happened.

## What this changes about the four original gates

Live evaluation is still unexecuted. Declarations are still unconfirmed. Repeatability is verified; independent reproduction is pending. The broader multi-agent architecture remains unimplemented but is now clearly excluded from measured contributions. These are distinct scientific, operational and author-controlled limits; none is an automatic promise of acceptance or a claim that only declarations matter to peer review.

## Author-authorized wording revision

Dhrumil authorized these edits on 11 October 2026. Added the verified 606 retry decisions per first-feasible arm; clarified the simulator does not gate unresolved non-idempotent retry; identified the 131 security-fault runs and 94 safe/unsafe changes behind the corrected no-gates contrast; described H2 as following by construction; disclosed redundant completion/SLO outcomes; quantified hypothetical alpha=0.05 power as approximately 5–8%; and replaced internal acknowledgment wording with a factual description of AI assistance and author responsibility. Used “provided artifacts” pending public release. This consent is not co-author assent, confirmation of funding/conflicts, approval of the live-study cost, or a claim that final human reference review has occurred. The PDF still has 14 pages and 50 references, with no undefined references or overfull boxes.

## E-mails supplied by author

Dhrumil confirmed dhrumil2496@gmail.com and shivamdesai047@gmail.com. Both were inserted in both LaTeX class branches and the official PDF. The PDF remains 14 pages; page 1 was visually checked and pages 2–14 are pixel-identical to the previously inspected rendering. Remaining placeholder categories are funding and artifact DOI/URL. Other declarations and approvals remain unconfirmed.

## Full names and funding confirmed by author

On 11 October 2026, the author supplied the full names Dhrumil Dutia and Shivam Desai and confirmed: “This work received no external funding.” Both LaTeX branches now include the full names, matching e-mails, and this funding statement. The final official PDF was rebuilt and visually checked; it remains 14 pages with no undefined references or overfull boxes. Earlier statements about missing e-mails or unconfirmed funding are superseded by these author confirmations. The sole remaining manuscript placeholder is the artifact DOI/URL. Co-author assent, ORCIDs, conflicts, final approval, artifact licensing/publication and the live-evaluation decision remain separate outstanding matters.
