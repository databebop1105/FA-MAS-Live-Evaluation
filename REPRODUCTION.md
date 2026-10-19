# FA-MAS reproduction instructions

The scientific evidence remains model-free. The public-tool check supplies reference actions and is not an official tau-bench agent evaluation.

## Clean installation

Use CPython 3.12 on Linux x86_64. The binary-wheel hashes target this platform.

```bash
python -m venv .venv
.venv/bin/python -m pip install --require-hashes -r requirements-reproduction.lock
PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -q
PYTHONPATH=src .venv/bin/python scripts/verify_evidence.py
.venv/bin/python scripts/external_service_study.py --output /tmp/fa_mas_external_replay
PYTHONPATH=src .venv/bin/python -m fa_mas.bounded_e2e --mode validate
```

Verified on this host in a new virtual environment with no inherited site packages: 29 hash-locked distributions installed; 44 tests pass; 52,500 historical, 18,000 initial matched and 18,000 corrected simulator rows replay byte for byte. All 150 public-tool traces also reproduce exactly. Workflow/inventory verdicts are rejudged. Reports are under `results/`. This is clean installation on the same host/interpreter build, not independent third-party replication or cross-platform bitwise portability.

The pinned upstream business-tool subset is in `third_party/tau2`, with its own MIT license and source commit. Its orchestration-heavy parent initializers are bypassed by namespace loading; imported business and utility modules are unmodified. No public dataset conversation or official benchmark reward is executed.

The container recipe pins its Linux amd64 base image by digest and enforces wheel hashes. It has not been built: Docker is unavailable here. The dependency lock covers executable evaluation, not Word/LibreOffice manuscript rendering, which additionally needs python-docx and the official template.

## Evidence revisions

`results/runs.csv` remains the historical 52,500-row study. `results/matched_controls/` retains the initial negative strict-judge sensitivity. `results/matched_controls_v2/` adds a separately labeled effect-aware defect correction. Its changes are compensation prerequisites, shared selection/budgets and correct judgment of detected unauthorized execution. No older CSV is silently relabeled. Historical pre-correction source is retained under `historical_source/`.

Regenerating a study intentionally overwrites its own result folder. Run regeneration in a separate copy if preserving originals. Read-only replay writes only verification reports. No command above calls a live model or modifies held-out tasks.

## Release facts still required

The upstream MIT notice applies to upstream material. It does not decide ownership or grant a public license for the FA-MAS manuscript/code. Author identity/order, affiliation, contributor consent, funding, conflicts, related submissions, permissions and preferred artifact license remain factual author inputs. A public archival DOI and independent preregistration have not been created. See `AUTHOR_DECLARATIONS_TO_CONFIRM.md` and `AUTHOR_SUBMISSION_INPUTS.json`.
