# Body settlement authority acceptance — work in progress

Date: 2026-11-01. **Assignment active; release BLOCKED.**

User confirmed no insurer/product is selected. Insurer-specific contractual applicability remains unresolved. Synthetic test contracts must never be promoted into authenticated insurer authority.

## Baseline

Main `37b1765af89121bf04ef590f729f1cd861e3c254`; remote integration `cd7fb39a0b7859f2cec91b94770e240ab62e0b75`. PRs #48/#57/#58/#59 remain OPEN and unmerged at their previously pinned heads (fresh `gh pr view` reads). This isolated worktree is `F:/Git/body-model-settlement-authority`, branch `codex/settlement-authority-acceptance`, starting at `7cf77db` with existing locally combined #58/#59 and IA-14 corrections. Original user worktree and prior acceptance worktree were preserved. No remote merge or approval.

Python 3.11.4, local venv with existing system test dependencies. Fresh parent suite: **679 passed, 1 IA-08 xfail**, recorded in `settlement-authority-evidence/baseline-suite.txt`. Knowledge/schema/fixture revisions are unchanged at this stage. Prior Article 19 evidence remains under `article19-evidence/` and is not represented as a fresh run for this task.

## Source findings

Official national legislation portal: [Insurance Law of 1316](https://qavanin.ir/Law/TreeText/?IDS=10376248520204498197). Fresh rendered publication preserved in `settlement-authority-evidence/insurance-law-1316-rendered.txt`.

Article 10: «در صورتيكه مالي بكمتر از قيمت واقعي بيمه شده باشد بيمه‌ گر فقط بتناسب مبلغي كه بيمه كرده است يا قيمت واقعي مال مسئول‌ خسارت خواهد بود.» This states proportional responsibility; this clause does not explicitly specify franchise sequencing. This is a statement about the inspected clause, not proof that no other applicable instrument supplies an order.

Regulation 53 Articles 4/19/20, effective intervals, amendments, circulars and insurer procedures still require this task's source/applicability audit. Previous Article 19 captures are evidence to revalidate, not automatic current certification. No applicable insurer policy, endorsement, settlement worksheet or qualified domain approval has been supplied. Statute, regulation/circular, contractual terms, administrative practice and observed arithmetic must remain separate in the final matrix.

## Reproduced identity defect and first correction

Parent C101 pays **1,432,000,000 IRR** on an unversioned insurer manual. Parent Stage 0 fails IA-08 with `--runxfail`. The new 24-case identity regression fails **24/24** on an isolated exact-parent worktree, exercising absent/blank reference or version for POLICY/ENDORSEMENT/INSURER_MANUAL and zero/positive franchise. The same regressions pass on the correction. Baseline test evidence is `parent-identity-regressions.txt`; the test was copied into an otherwise unchanged parent checkout to avoid accidentally importing candidate code.

Shared `franchise_identity_gap` now requires nonblank instrument reference and explicit instrument version for every monetary term. Review blocks authorization with FRANCHISE_AUTHORITY_REQUIRED; direct engine returns the matching nonpayable authority result and U02. IA-08's repaired identity counterexample no longer has an xfail marker. Focused checks: **220 passed**, existing fixtures **50/50**. M34 removes the engine identity check and is targeted by a positive manual-franchise counterexample.

**This is only the identity layer. Reference/version do not authenticate a document or establish applicability.** Full insurer/product/coverage/date/source-status validation, conflicts and the final integrated suite remain incomplete. No final engineering or contractual acceptance is asserted.

## Remaining implementation and verification requirements

- Shared closed authority schema and context binding: insurer/product, coverage/claim type, policy/instrument reference/version, effective interval covering policy/event dates, source status, document identity/hash/locator, mode/rate/base/minimum/claim sequence where relevant.
- Compare policy/endorsement/manual terms and retain conflicts explicitly. A manual must demonstrably govern the contract. A supplied metadata token is not independent authentication.
- Review and direct engine tests for every S09 variant: wrong scope, expired or future version, source without date, conflicting endorsement, complete absolute/percentage/zero controls and missing terms.
- S07/S08 conflicting disposition/valuation evidence and source-without-bound-amount cases, retaining evidenced zero and all established positive controls.
- S10: exact 700/720 independent arithmetic; retain both scenarios and null single payable when order authority is absent. Parent C72 already has a Review-live uncertainty but returns no scenarios after authorization reconciliation; direct configured-order behavior needs a separate parent counterexample. Resolve neither by questionnaire token nor a universal default.
- Full S10 variants: ratio one, percentage/named base, missing values, conflicting declarations, different versions, equal outcomes without inventing universal authority.
- Exact integrated Python 3.11 suite, strict Stage 0, fixtures, graph/guards/plans, mutation gate, 47 original inspection cases and 14 diagnostic probes, generated docs/FAQ, clean-checkout reproducibility. Preserve original inspection identities/reference expectations and triage every changed result.
- Complete claim-to-source and legal/contractual/math/authorization matrix, exact revision/commands, regression and mutation evidence, and independent reviewer decisions before completion audit.

## Reviewer checklist

- Engineering: independently reproduce parent failures, exact-candidate checks, supported/direct boundary agreement, stable sourced controls and all changed corpus rows. PENDING final candidate.
- Domain interpretation: distinguish route-specific ownership requirements, rescue scopes/denominator and proportionality/order. PENDING named reviewer.
- Contractual authority: authenticate actual insurer/product policy/endorsement/manual, versions, dates, scope, precedence and term bindings. AUTHORITY_PENDING; insurer unselected.
- Release: no automatic approval, merge, issue closure or release-gate closure. BLOCKED.

Browser tools used so far: `mcp__playwright_global__browser_navigate`, `mcp__playwright_global__browser_snapshot`, `mcp__playwright_global__browser_fill_form`, `mcp__playwright_global__browser_click`, `mcp__playwright_global__browser_evaluate`.
