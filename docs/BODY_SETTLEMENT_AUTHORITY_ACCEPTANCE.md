# Body settlement authority acceptance: S05-S10

Review date: 2026-11-01, Asia/Tehran. **Broader release BLOCKED. Tests do not confer legal, contractual or human-review approval.** The user selected no insurer/product. Real contractual applicability remains AUTHORITY_PENDING; positive examples use explicitly synthetic software contracts.

## Baseline and revisions

Main `37b1765af89121bf04ef590f729f1cd861e3c254`; remote integration / PR #48 `cd7fb39a0b7859f2cec91b94770e240ab62e0b75`. Fresh final `git fetch`/`gh pr view` evidence: `settlement-authority-evidence/final-pr{48,57,58,59}.json`. All four PRs remain OPEN and unmerged. #57 head is `cb7bce78e8704378539f915f5d4ffd9be943a597`, #58 `49b2446f4ac2674f5bbbd81b5d3bc513e1e77133`, #59 `1e41c67c7f892526f52aecd40267709592383444`.

This isolated branch is `codex/settlement-authority-acceptance`, at `F:/Git/body-model-settlement-authority`. Parent `7cf77db` already combines #58/#59 and IA-14 corrections locally; those were reused. Original user work and previous acceptance worktrees were preserved. No remote push, merge, approval or issue closure occurred.

Reviewed executable candidate: `5cee269` (full hash in final manifest). Python 3.11.4; unchanged knowledge tree `770d11cd4a016b8e7173b896cd28f360f5f52527`. No monetary formula, universal rate or legal-source confidence was changed to make tests pass. Schemas now carry structured contract context and authority records. The clean checkout has a fresh virtual environment and test installation.

Fresh parent suite: **679 passed, 1 IA-08 xfail**. The 24 new identity regressions fail **24/24** on that parent and pass on the correction. Full parent/current inputs, digests, grants, guards, traces and origins are in `s05-s10-{parent,current}.json`. The runner's `--legacy` flag honestly uses the parent's older input vocabulary, rather than pretending it accepted new authority-record fields.

## Legal claim-to-source matrix

Artifact names below are under `settlement-authority-evidence/`; SHA-256 values are in `final-manifest.json`. They identify preserved rendered captures, not a signed publisher-original PDF. Original Persian wording is retained, including possible transcription defects.

| Proposition | Exact Persian wording / locator | Authority, dates and evidence | Decision |
|---|---|---|---|
| Underinsurance proportionality | Insurance Law Art. 10: «در صورتيكه مالي بكمتر از قيمت واقعي بيمه شده باشد بيمه‌ گر فقط بتناسب مبلغي كه بيمه كرده است يا قيمت واقعي مال مسئول‌ خسارت خواهد بود.» | [Official text](https://qavanin.ir/Law/TreeText/?IDS=10376248520204498197), مجلس شورای ملی, approved 1316/02/07. [Metadata](https://qavanin.ir/Law/Attribute/?IDS=10376248520204498197): notification 801; gazette 2512 dated 1316/03/20; execution 1316/03/31. Captures `insurance-law-1316-{rendered,metadata}.txt`. | Explicit proportionality principle; this clause does not explicitly prescribe franchise order. The rendered copy spells «يا» at this location; original gazette imagery has not been authenticated to resolve transcription. Amendment completeness/end of applicability remain unverified. |
| Strict economic threshold | Regulation 53 Art. 19 الف: «مجموع هزينه هاي تعمير و تعويض قسمتهاي خسارت ديده آن با احتساب هزينه هاي نجات از 75 درصد قيمت آن در روز حادثه بيشتر باشد» | [Official text](https://qavanin.ir/Law/TreeText/?IDS=12020232825033491345), شورای عالی بیمه, approval 1384/12/09, notification 32010 dated 1384/12/23. Captures `reg53-current-{rendered,metadata}.txt`. | Explicit strict `>` with rescue and event-date market value. Equality does not establish this ground; whole theft remains independently applicable. Execution metadata displays `0000/00/00`; do not substitute approval date for an authenticated effective date. |
| Total-loss value and salvage | Art. 19 الف تبصره 1: «ارزش معاملاتي موضوع بيمه در روز حادثه و حداكثر تا مبلغ بيمه شده»; «ارزش بازيافتي احتمالي و كسورات مقرر كسر» | Same Regulation 53 publication. | Explicit valuation/insured-limit and deduction principles. S05's 100 IRR franchise and precise contractual assumptions are software oracles, not universal statutory deductions. |
| Ownership after salvage disagreement | Art. 19 الف تبصره 2: «در صورت عدم موافقت بيمه‌ گذار با ارزش تعيين شده، بيمه‌گر پس از تملك موضوع بيمه و انتقال سند» | Same official text. | Explicit specified disagreement route. Completed transfer on an agreed insurer-ownership settlement is a route/evidence invariant requiring applicable agreement; not every physical total loss universally requires transfer. |
| Whole-theft transfer | Art. 19 الف تبصره 4: «قبل از پرداخت خسارت مربوط به سرقت كلي موضوع بيمه، سند مالكيت وسيله نقليه بيمه شده بايد به بيمه‌گر منتقل شود» | Same official text. | Explicit, separate from retained-wreck valuation; existing theft timing/transfer conditions remain. |
| Rescue ceiling | Art. 4: «حداكثر تا بيست درصد كل خسارت وارده قابل جبران خواهد بود» | Same official text. | Explicit ceiling for stated reasonable costs. Mapping «كل خسارت وارده» to every configurable engine denominator remains unresolved. Actual, classification and payable rescue stay separate; S05/S10 use zero settlement rescue. |
| Franchise and partial-loss components | Art. 2(6): «ميزان آن در بيمه‌نامه مشخص مي‌گردد»; Art. 19 ب names depreciation, franchise and rescue/transport. | Same official text. | Monetary term is policy-dependent. No universal Article-10/franchise order is inferred here. |
| Event-date proportional responsibility | Art. 20 تبصره 2: «بيمه‌گر فقط به تناسب مبلغ بيمه شده با قيمت واقعي آن در روز حادثه مسئول جبران خسارت خواهد بود» | Same official text. | Explicit principle; no second ratio is added to total-loss `min(market, insured)` settlement. |
| Salvage-before-franchise circular | Repository names circular 1400/401/146850, purported 1400/09/13. | Claimed issuer compilation `https://centinsur.ir/_douranportal/documents/2277/carinsurance.pdf` returned **403 Access Denied** in a fresh Playwright request; capture `circular-compilation-access-denied.txt`. | AUTHORITY_PENDING: original wording, page, publisher-artifact hash and effective interval unavailable. Repository metadata is not independent authentication. |
| Insurer policy, endorsement, procedure or worksheet | No actual insurer/product/period or document selected. | User explicitly chose to keep this unresolved. | AUTHORITY_PENDING. Observed worksheet practice would not independently establish legal or contractual authority. No secondary publication or familiar convention is promoted into a binding rule. |

The government publication evidences its displayed text; it does not prove every amendment, interpretation or claim-date application has been authenticated. Source gaps remain visible rather than being filled with invented intervals.

## Four separate questions

1. **Legal:** public texts support proportionality and the route-specific principles above; amendments, the inaccessible circular and disputed interactions remain pending.
2. **Contractual:** no actual insurer instrument is selected. Positive examples are SYNTHETIC_TEST assumptions; no real rate or sequence is certified.
3. **Mathematical:** S05 = `2,000 − 300 − 100 = 1,600`; S10 = `1,000 × 0.8 − 100 = 700` and `(1,000 − 100) × 0.8 = 720`. Expectations were not derived from engine output.
4. **Authorization:** both boundaries refuse unsupported settlement evidence/franchise authority. Unresolved S10 retains scenarios and null single payable. A synthetic model COMPUTE grant is not payment authorization.

## Bounded corrections and parent witnesses

| Defect / requirement | Exact-parent evidence | Correction and regression |
|---|---|---|
| IA-08 identity | Parent C101 pays 1,432,000,000 IRR; Stage 0 fails IA-08; missing/blank identity regressions fail 24/24. | Shared positive/zero identity gate at both boundaries; repaired IA-08 loses xfail. |
| Governing-contract applicability | Parent identified but unbound term pays 900 (`S09_IDENTIFIED_NO_APPLICABILITY`). | Bind insurer/product, policy reference/date, branch, instrument/version, effective interval, exact term fields, source status, hash/locator and recorded reviewer. A manual must govern this contract. Competing questionnaire terms cause FRANCHISE_TERMS_CONFLICT, not last-write selection. |
| Claimed completion without proof | Parent `S06_UNPROVED_COMPLETION` pays 1,900 with true flag and absent proof. | Common engine guard requires completed state AND supporting proof; Review agrees. False/pending/missing state still blocks even if a proof token exists. |
| Unevidenced zero salvage | Parent `S08_UNEVIDENCED_ZERO` pays 1,900. | Require bound valuation AND supporting evidence. Supported zero remains valid. Missing disposition stays UNRESOLVED instead of becoming NOT_APPLICABLE; conflicting disposition/title/monetary aliases reject structurally with locators. |
| S10 token and erased scenarios | Parent direct token pays 700; parent Review nulls payment but loses both scenarios as AUTHORIZED_UNCERTAINTY_UNRESOLVED. | Run a named order only with matching applicable record. Otherwise execute both existing plans, retain 700/720, block U01 and return ORDER_UNRESOLVED at both boundaries. Ratio one remains computable without asserting universal order; equal underinsured alternatives remain unresolved. |

`VERIFIED` is a recorded source-review attestation, not authentication performed by the calculator. Software checks completeness and binding; an external reviewer must authenticate the artifact and establish the record's truth. Synthetic records require matching synthetic context and remain labeled in results. No real governing document or qualified approval was fabricated.

The private fixture adapter compiles explicit authored assumptions only for software tests/fixtures; production Review never calls it. It preserves absent identity, never supplies an event date, and cannot turn an insurance-contract context into a synthetic one. Positive fixtures now explicitly state synthetic context, dates and supporting-document assumptions. Original 47 inspection inputs/reference expectations remain unchanged.

## Gates and reproducibility

See the comparison, flow and reviewer-checklist documents and `settlement-authority-evidence/final-manifest.json`. It pins candidate, graph/schema identities, commands, original inspection identities and artifact hashes. Intermediate failed files are diagnostic history; only named final evidence supports acceptance.

- Focused authority module: **59** regressions, including identity, zero, wrong scope/dates, exact terms, both bound orders, missing policy dates, equal alternatives and proof.
- Final clean-checkout suite: **739 passed, zero xfails**, in `clean-final-suite.txt`; fresh environment/install in `clean-install.txt`. Strict Stage 0: **13 passed** with `--runxfail`, in `final-strict-stage0.txt`.
- Mutations: **38/38 killed**; freshness in `final-mutation-check.txt`. M34 is retired because the full applicability gate independently rechecks identity; M35 mutates that controlling gate. M31/M37 cover transfer state/proof separately; M38 valuation proof; M36 order authority; M39 Review scope; M40 conflicting terms. Existing IA-14/final-branch mutants remain.
- Fifty synthetic fixtures retain their amounts; final graph/guard/plan, fixture and generated-doc checks are separately recorded. No golden amount or formula was rewritten to match output.
- Original corpus comparator: **6 MATCH / 41 MISMATCH, gate FAIL**. Every mismatch is nonpayable with FRANCHISE_AUTHORITY_REQUIRED because those original inputs lack applicability records. Fourteen internal probes remain separately diagnostic, not independent reference outcomes. This failure is not converted into a green legal/release gate.

Comparator tests require rejection of unsupported original inputs, and use explicitly sourced synthetic contracts in temporary copies to continue testing arithmetic/tamper detection. They do not rewrite original identities or the reference manifest.

Use Python 3.11; PowerShell `$env:PYTHONUTF8='1'`; fresh `python -m venv .venv` and `.venv/Scripts/python.exe -m pip install -e '.[test]'`.

```text
python -m pytest -o addopts='' -q -ra
python -m pytest tests/test_stage0_counterexamples.py --runxfail -q
python claim.py fixtures
python claim.py validate
python scripts/run_mutation_gate.py --check-report
python scripts/sync_review_docs.py
python scripts/sync_github_issues.py --repo SoloMidMiram/Iranian-Auto-Body-Insurance-Claim-Calculation-Knowledge-Graph
python -m compileall -q claim.py src scripts
python scripts/run_settlement_authority_acceptance.py --output docs/settlement-authority-evidence/s05-s10-current.json
python scripts/run_case_based_inspection.py --root . --cases cases --internal --output docs/settlement-authority-evidence/final-inspection.json
python scripts/build_case_comparison.py docs/settlement-authority-evidence/final-inspection.json docs/settlement-authority-evidence/final-comparison.json --model-root .
```

The comparator is expected to exit 1 against frozen references. Issue sync is a dry run without `--apply`. Parent witness command adds `--root F:/Git/body-model-settlement-authority-parent --legacy` to the same runner. Every run records actual protocol, digests, origin and revision.

Clean-checkout re-execution of the six cases is in `clean-s05-s10.json`; it preserves amounts, statuses, scenarios, guards and rule traces. `final-comparison-triage.json` records each of the 41 original-corpus changes. Unrelated historical findings are not declared fixed: the stricter authority gate can mask them until a properly sourced re-evaluation. The original 47 input blobs, reference manifest and all fifty fixture expectation objects were verified unchanged against `7cf77db`.

## Recommendation

Recommend independent engineering review of the bounded changes and parent witnesses, then qualified domain/contract review of remaining applicability questions. S05-S10 have reproducible software evidence under stated conditions; they are **not legally certified or release-authorized**. Keep broader release blocked. Do not automatically merge, approve PRs, close issues or adopt a new corpus baseline.

Browser tools invoked: `mcp__playwright_global__browser_navigate`, `mcp__playwright_global__browser_snapshot`, `mcp__playwright_global__browser_fill_form`, `mcp__playwright_global__browser_click`, `mcp__playwright_global__browser_evaluate`.
