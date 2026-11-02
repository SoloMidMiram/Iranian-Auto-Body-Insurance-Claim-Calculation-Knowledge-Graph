# Integration Acceptance RC-1 audit — 2026-11-02

Status: proposed integration published for review; independent acceptance PENDING; release BLOCKED.

The reviewed published candidate is `3c53e749eba679fa26f7d2a08cc17644b1e1283a`, PR #60. Its executable/input/test trees equal `5cee269`. All S03–S10 were freshly executed together at that exact published revision using `scripts/run_integration_rc1_audit.py`; full operands, classifications, Review decisions and amounts are in `rc1-published-candidate/`. S03 and S04 reach COMPUTE and classify PARTIAL_DAMAGE and TOTAL_LOSS; S05 yields 1,600; S06–S09 refuse payment; S10 retains 700/720 scenarios and no single payable. The three adversarial proof/applicability probes also pass.

GitHub's repository-gate for PR #60 completed successfully: run 41344190854, job 124960382074. The actual checkout was generated merge commit `21eb058f6ca9c824306f2dba4c16d71b97b5bff3`, combining published head `3c53e74` with base `cd7fb39`. Logs confirm 739 tests passed, 50/50 fixtures, current mutation report, and current documentation/FAQ. `github-ci.json` records selected actual log lines. This is automated integration evidence, not independent engineering approval. Inspection of run_mutation_gate.py confirms that --check-report reruns the baseline and all 38 mutants before comparing the generated report. The successful CI step therefore proves a fresh 38/38 result.

| Objective requirement | Evidence | Disposition |
|---|---|---|
| One pinned proposed integration | PR #60 head 3c53e74; executable candidate 5cee269 | Published draft; no merge or approval |
| Preserve 47 originals and frozen expectations | corpus-map.json; preservation-check.txt; two separate manifests | Preserved; no baseline replacement |
| Separate corpus with explicit synthetic contract terms | synthetic-v1; synthetic-reference-v1.json | Applicability supplied for identifiable terms; intentional negative controls preserved |
| Run both corpora without masking underlying behavior | original and synthetic observation/comparison files | Original 6 MATCH / 41 MISMATCH; synthetic 36 MATCH / 6 KNOWN_DEVIATION / 5 MISMATCH; both gates FAIL |
| Classify every changed outcome | rc1-published-candidate/case-dispositions.json | 41 historical differences provisionally EXPECTED_CONTAINMENT; 11 synthetic residuals UNRESOLVED_DOMAIN_ISSUE; all independent dispositions pending |
| Prove intended PR corrections applied once | integration-history.json | Nine ordered-delta equivalents found exactly once; generated combined mutation report excluded explicitly |
| S03–S10 on same candidate | rc1-published-candidate/s03-s04.json, s05-s10.json, manifest.json | Fresh assertions pass at 3c53e74 |
| Fresh tests and mutation evidence | GitHub CI summary; earlier local suite and mutation report | Automated pass; does not override corpus failures |
| Independent engineering review | GitHub reviews for PR #60: empty on 2026-11-02 | PENDING, per user instruction |
| Authenticated legal/contractual authority | Existing official-source captures and declared limitations | Amendment/circular authority pending; no insurer selected; VERIFIED remains external attestation |
| Qualified legal/domain signoff | Reviewer checklist | PENDING, per user instruction |

The author dispositions do not declare every residual a calculation bug. C61/C67 retain safety blocking but differ in uncertainty representation. C66 now refuses a scenario grant for unresolved salvage. C72 permits unresolved scenarios while refusing a single payable. C99 lacks an expected classification field. The six known deviations remain as listed in the reconciliation README, including nonzero computed results in several cases whose references require refusal. These need substantive independent adjudication; fail-closed original inputs cannot clear them. No new calculation features or reference changes were introduced.

Reproduce: set `PYTHONUTF8=1`, then run `.venv/Scripts/python.exe scripts/run_integration_rc1_audit.py --output <new-output-directory>`. The harness stamps the actual revision; it does not relabel older observations as newly executed corpora. Original/synthetic corpus observations remain pinned to their own recorded revision and equivalent model content.

The full acceptance milestone is not achieved: neither frozen comparator has passed independent disposition, and no independent engineering review or qualified domain signoff is recorded. Publishing the review package satisfies the bounded publication action. It does not supply the outstanding acceptance.


Current follow-up (2026-11-03): see docs/reconciliation-evidence/rc1-followup/CASE_DISPOSITIONS.md and VALIDATION_REPORT.md. The observations above remain pinned historical evidence; this pointer does not rebaseline or relabel them. Canonical release status: docs/RELEASE_STATUS.md, BLOCKED.
