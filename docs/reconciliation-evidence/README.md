# Settlement evidence reconciliation — 2026-11-01

Release BLOCKED. This package is author-prepared evidence for independent review, not acceptance or payment authority.

## Two distinct corpora

The original 47 inputs and `docs/case-reference-manifest-v1.json` are unchanged. Fresh `original-observation.json` and `original-comparison.json` reproduce **6 MATCH / 41 MISMATCH**. Every one of those 41 mismatches remains nonpayable, without a calculation grant, with `FRANCHISE_AUTHORITY_REQUIRED`.

`synthetic-v1/` is a separate, explicitly synthetic applicability variant with a separate manifest ID. `corpus-map.json` links each original and new input by SHA-256. `synthetic-reference-v1.json` retains every original expected object and known-deviation envelope; only input digests and corpus identity/provenance change. No expected outcome is learned from observed results.

For identifiable franchise terms, the authored software contract binds the existing exact terms, instrument/version, synthetic insurer/product/policy, policy/event dates, branch, effective interval, clause locator and term-content hash. The helper in `tests/contract_assumptions.py`, using the fixture-only compiler, supplies these records. The synthetic interval 1300–1500 is an explicit test assumption. `source_status=SYNTHETIC_TEST` and the reviewer label disclaim domain approval. No actual insurer policy or circular is authenticated. The unversioned identity control intentionally remains incomplete. Other negative-case evidence gaps are deliberately preserved; this corpus must not be described as authority-complete for every case.

Fresh synthetic comparison: **36 MATCH / 6 KNOWN_DEVIATION / 5 MISMATCH**, gate FAIL. The 36 matches demonstrate preserved calculations/decisions under supplied applicability. Known deviations remain release-blocking: C104 theft clock, C35 battery question triggering, C48 assessed depreciation, C64 settlement-base authority, C97 late notice, C98 recourse. Applicability must not mask these older findings.

Five additional differences are retained for independent disposition, without changing reference outcomes:

- C61: transfer still blocks payment; the original uncertainty label differs from the new blocking-condition representation.
- C66: unresolved salvage disposition now refuses authorization rather than issuing a scenario-set grant.
- C67: invalid physical-loss disposition still blocks payment; the original uncertainty label differs.
- C72: an unauthenticated order token yields unresolved scenarios and no single payable rather than refusing the scenario-set grant entirely.
- C99: structural third-party result does not expose the expected classification field. No synthetic body authority is treated as third-party financial authority.

These residuals mean corpus reconciliation is documented, but full independent acceptance is still incomplete. No old reference baseline is adopted or replaced.

## Classification inspection

`exact-s03-s04.json` retains full inputs, emitted engine case, classification, Review decision and calculation. Exact S03 uses repair 7,500, rescue 0 and market 10,000: PARTIAL_DAMAGE, COMPUTE, 6,750 IRR under the explicit 10% synthetic partial-loss contract. Exact S04 uses repair 7,400, rescue 200 and market 10,000: TOTAL_LOSS, COMPUTE, 9,200 IRR under a separately explicit AFTER_SALVAGE 10% contract with evidenced zero retained salvage. These are software amounts, not legal entitlements. Both examples reach calculation; the authority gate does not mask classification.

## Local integration and publication

`integration-history.json` pins original candidate `5cee269bce51653adb4b1e216ee0fad15db5144e` and proves exactly one equivalent application for each of seven #57 commits, the #58 correction, and the #59 correction. The algorithm compares ordered added/deleted lines per file, ignoring hunk locations, context and blob IDs. Only generated `docs/MUTATION_REPORT.md` is excluded: its combined-state content is covered by the existing mutation evidence, not claimed patch-identical to either isolated PR. #59's other changes match exactly despite the stacked #58 prerequisites moving contexts. Current source, knowledge, schemas, fixture and test trees remain equal to that executable candidate.

GitHub connector `github_get_pr_info` freshly confirmed #48/#57/#58/#59 OPEN and unmerged, with the heads recorded in the earlier acceptance report. Local `git fetch origin` succeeded. Publishing this branch proposes the local combined history for review; it does not independently accept those PRs or merge them. The new PR targets `fix/body-runtime-blockers` to expose the proposed integration relative to #48.

## Authority and validation limits

The existing `VERIFIED` semantics remain an externally recorded reviewer attestation, not calculator authentication. No actual insurer/product was selected. Amendment completeness and circular authority remain pending. This run attempted official Article 10 metadata navigation and received exactly `browserBackend.callTool: net::ERR_CONNECTION_CLOSED at https://qavanin.ir/Law/Attribute/?IDS=10376248520204498197`; browser-dependent verification stopped as instructed. The earlier 403 circular result is historical, not freshly reverified.

Browser tools invoked this run: `mcp__playwright_global__browser_navigate`.

Reproduce using Python 3.11 and PowerShell `$env:PYTHONUTF8='1'`:

```text
.venv/Scripts/python.exe scripts/reconcile_settlement_corpus.py
.venv/Scripts/python.exe scripts/reconcile_integration_history.py
.venv/Scripts/python.exe scripts/run_case_based_inspection.py --root . --cases cases --output docs/reconciliation-evidence/original-observation.json
.venv/Scripts/python.exe scripts/run_case_based_inspection.py --root . --cases docs/reconciliation-evidence/synthetic-v1 --output docs/reconciliation-evidence/synthetic-observation.json
.venv/Scripts/python.exe scripts/build_case_comparison.py docs/reconciliation-evidence/original-observation.json docs/reconciliation-evidence/original-comparison.json --model-root .
.venv/Scripts/python.exe scripts/build_case_comparison.py docs/reconciliation-evidence/synthetic-observation.json docs/reconciliation-evidence/synthetic-comparison.json --manifest docs/reconciliation-evidence/synthetic-reference-v1.json --cases docs/reconciliation-evidence/synthetic-v1 --model-root .
.venv/Scripts/python.exe -m pytest -o addopts='' -q -ra
```

Both comparator commands deliberately exit 1. The first attempt at inspection/tests omitted the documented UTF-8 setting and failed on Windows cp1252 decoding; `pytest.txt` records the corrected run. Observations identify their actual pre-publication HEAD and model content; they are not relabeled as exact published-head CI evidence. Independent engineering and qualified domain/contract review remain outstanding.
