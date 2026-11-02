# Integration equivalence matrix

Fresh ancestry, stable patch IDs and pairwise range-diff supplement the earlier ordered-addition/deletion proof. See integration-equivalence.json; the existing integration-history.json remains immutable.

| Source | Original → local application | Final implementation and regression evidence | Finding |
|---|---|---|---|
| #57 initial corpus | 1fcda649 → 21c1f66b | cases/inspection-*.json, immutable manifest; test_case_comparison.py | Equivalent |
| #57 plan docs | fa214d94 → ff6bf48a | CASE_BASED_INSPECTION and phase plan | Equivalent |
| #57 integrity | e19a0aec → 8b35454c | build_case_comparison.compare, material/standalone assertions | Equivalent |
| #57 reference provenance | 58231f66 → 4837f0c8 | reference manifest identities | Equivalent, frozen |
| #57 model binding | 09b07b35 → 6f91579f | model_identity, comparator binding; stale-model and rendered-money controls | Equivalent; strengthened by byte checks |
| #57 import/shim binding | ef3e8c79 → d59cc21e | load_model_modules/load_selected_file; cross-checkout and dirty-shim tests | Equivalent |
| #57 input/harness binding | cb7bce78 → 09640852 | verified_case_corpus, inspector_identity; stale inspector/external input tests | Equivalent; strengthened by byte checks |
| #58 final evidence | 49b2446f → 72fca7da | engine._final_selected_branch_evidence_gap; override-selected-branch regressions/M30 | Equivalent |
| #59 title route | 1e41c67c → 40008705 | engine total-loss route, Review eligibility, guard G_SALVAGE_XOR_TITLE_TRANSFER; Stage0/authority/M31/M37 | Runtime equivalent then deliberately strengthened with proof requirement |

All nine local applications are ancestors of the candidate exactly once under the earlier ordered-delta check. All seven #57 stable patch IDs and #58 match. #59 stable patch ID differs: range-diff identifies the intentionally regenerated combined mutation report and #58's surrounding mutation context. No additional #59 runtime delta is hidden. Inspect the full range-diff in JSON rather than accepting a commit count.

#48 remains the actual parent integration cd7fb39 and merge base. Final runtime diff from original #60 adds only assessment-intent preservation and unresolved notice/recovery gates; the provenance correction is inspection tooling. No title/salvage/franchise gate was relaxed, no duplicate branch implementation was introduced, and no frozen reference changed. Shared graph/question changes are regenerated into canonical/shipped Review docs. Financial boundaries require behavioral tests, not merely patch presence; final evidence is in VALIDATION_REPORT.md and CASE_DISPOSITIONS.json. This author audit is not a qualified independent human acceptance.
