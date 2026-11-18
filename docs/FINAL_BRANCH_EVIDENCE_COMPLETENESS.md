# Final-selected-branch evidence completeness remediation

This document records a bounded correction to classification reconciliation.
It does not change a settlement formula, resolve a legal interpretation, close
IA-05/IA-08/IA-14, approve PR #48, or authorize release. Release remains
**BLOCKED**.

## Baseline and environment

- Target: `fix/body-runtime-blockers`
- Verified parent: `cd7fb39a0b7859f2cec91b94770e240ab62e0b75`
- Parent tree: `4c594155cf9404def9bb32896c711985f3abccb8`
- Parent is the PR #56 integration merge; no newer remote integration commit
  existed at preparation time.
- Dedicated local branch: `fix/final-branch-evidence-completeness`
- Python: 3.11.15
- Environment: `/tmp/body-model-final-branch-venv311`
- Installation: interpreter-bound editable `.[test]` installation from the
  isolated worktree.

The case-inspection branch and its large documentation corpus remain separate.
Only the focused synthetic facts needed for this correction are represented in
the runtime tests below.

## Parent reproduction

The reproduction used the repository's schema-validating
`INTERNAL_TEST_DIRECT` authorization helper. Each authorization reported
`issuer=INTERNAL_TEST_DIRECT`, `decision=COMPUTE`, a claim hash, and the exact
synthetic payload snapshot. This is boundary evidence, not a production path.

Common facts: evidence derives `THEFT`; declared `TOTAL_LOSS`; documented
override with actor, reason, source and timestamp; market and insured value
10,000 unless removed; versioned absolute franchise 1,000; retained salvage
explicitly zero; established causation and zero prior recovery.

```bash
/tmp/body-model-final-branch-venv311/bin/python \
  /tmp/body-model-runtime-inspection-corpus/scripts/investigate_total_loss_override.py \
  --root /tmp/body-model-integration-cd7fb39 \
  --cases /tmp/body-model-runtime-inspection-corpus/cases \
  --output /tmp/total-loss-override-parent-cd7fb39.json
# exit 0 on parent cd7fb39; exact synthetic payloads and authorization/classification
# fields are defined by the script at inspection commit fa214d940cbfe79389ff1269800e52a69bff13b8
```

| Variant | Parent classification | Parent result | Financial defect |
|---|---|---|---|
| Repair missing; classification rescue explicitly 0 | `THEFT` → `AUTHORIZED_OVERRIDE` | **9,000 IRR payable** | Override supplies branch authority but no repair assessment |
| Repair missing; actual rescue 200 | `THEFT` → `AUTHORIZED_OVERRIDE` | **9,200 IRR payable** | Rescue expense does not establish repair evidence |
| Repair and rescue omitted | `THEFT` → `AUTHORIZED_OVERRIDE` | **9,000 IRR payable** | Two missing operands become effective zero/irrelevant |
| Market missing | `THEFT` → `AUTHORIZED_OVERRIDE` | `INPUT_ERROR`, no payable | Contained only after authorization and eligibility guards |
| Actual rescue 200 conflicts with threshold rescue 0 | `INSUFFICIENT_EVIDENCE` | no payable | Existing correct control |
| Complete repair/market/rescue override | `AUTHORIZED_OVERRIDE` | 9,000 IRR payable | Existing supported control |
| Ordinary theft without override | `MATCH` | `PENDING_60_DAY_CRITERION`, no payable | Existing theft control |

The three payable defect rows executed the total-loss guard and plan chain,
including causation, recovery, no-double-underinsurance, salvage XOR, rescue
ceiling, franchise-source, insured-sum ceiling and uncertainty guards. Passing
those settlement guards did not cure the missing classification evidence.

Parent-fail test command after adding regressions but before the correction:

```bash
python -m pytest \
  tests/test_engine.py::test_override_selected_total_loss_requires_repair_assessment \
  tests/test_engine.py::test_override_selected_total_loss_requires_event_market_value \
  tests/test_engine.py::test_theft_derived_total_loss_override_with_complete_operands_remains_available \
  tests/test_engine.py::test_missing_classification_rescue_does_not_block_whole_vehicle_theft \
  tests/test_engine.py::test_total_loss_override_cannot_bypass_unresolved_rescue \
  tests/test_review.py::test_supported_theft_review_does_not_manufacture_threshold_evidence_or_override \
  tests/test_review.py::test_supported_theft_review_missing_market_cannot_authorize -q
# exit 1: four defect assertions failed; six controls passed
```

## Invariant and boundary separation

A documented classification override supplies authority to choose a conflicting
branch. It does not manufacture facts required by that final branch.

- **Classification authority:** actor/source/reason/time may resolve which
  branch is selected.
- **Evidence completeness:** the selected threshold route still needs a
  repair/replacement assessment, event-date market value and a resolved,
  separately scoped classification-rescue operand.
- **Calculation authorization:** only follows when branch authority and required
  evidence are both complete.
- **Settlement eligibility:** coverage, recovery, disposition, franchise,
  rescue ceiling and other branch guards remain downstream and independent.

This correction uses the existing PR-03 threshold contract. It does not decide
what rescue scope is legally controlling, invent a repair value, treat omission
as zero, or strengthen the known unsafe salvage/title/franchise paths.

## Implementation

`engine.py` now has one reusable final-selected-branch evidence validator for
override-selected threshold routes (`PARTIAL_DAMAGE`, `TOTAL_LOSS`, and
`GLASS_ONLY`). It checks:

1. repair/replacement assessment is present;
2. event-date market value is present;
3. classification rescue is resolved, preserving explicit zero and the explicit
   legacy compatibility source; and
4. existing conflicting/embedded rescue reasons retain precedence.

The resulting evidence gap is non-overridable, just like the existing material
rescue gate. Complete overrides proceed unchanged. Ordinary theft never invokes
the validator because theft is not an override-selected threshold route.

The supported Review questionnaire has no input that can mint
`classification.override`. Review tests therefore establish that it emits
neither an override nor invented repair/rescue operands for an ordinary theft
file, and that missing market evidence prevents authorization. They do not
simulate an impossible supported-path override.

## Before/after matrix

| Variant | Parent | Corrected requirement |
|---|---|---|
| Missing repair + rescue 0 | 9,000 payable | `CLASSIFICATION_EVIDENCE_REQUIRED`; no payable |
| Missing repair + actual rescue 200 | 9,200 payable | `CLASSIFICATION_EVIDENCE_REQUIRED`; no payable |
| Missing repair + omitted rescue | 9,000 payable | `CLASSIFICATION_EVIDENCE_REQUIRED`; no payable |
| Missing market | late `INPUT_ERROR` | early `CLASSIFICATION_EVIDENCE_REQUIRED`; no payable |
| Conflicting rescue | evidence required | unchanged |
| Complete documented override | 9,000 payable | unchanged |
| Ordinary theft | pending theft criterion | unchanged |
| Explicit compatibility zero with complete operands | supported and traced | unchanged |
| Strict 75% boundary | equality is partial; only greater is total | unchanged |

## Mutation coverage

M30 removes the final-selected-branch non-overridable condition. The dedicated
theft-derived / total-loss-selected / missing-repair probe then reaches a
payable, so the mutant is killed. Survivor triage established that M27 exposed
missing no-override coverage; a new ordinary threshold-route probe now kills
it. M29 duplicated the final-selected-branch validator and is retired as
equivalent after removing that redundant candidate-side condition. The curated
report records this triage and is regenerated; historical reports are not
rewritten.

## Corrected-revision validation

All acceptance commands used `/tmp/body-model-final-branch-venv311/bin/python`
3.11.15 from the isolated remediation worktree.

| Command or corpus | Exit/result |
|---|---|
| `python -m compileall -q claim.py src scripts` | exit 0 |
| `python claim.py validate` | exit 0; graph valid; 22 recorded body-authority and 48 source-metadata findings |
| `python claim.py fixtures` | exit 0; 50/50 passed |
| `python -m pytest` | exit 0; 628 passed, 4 expected failures |
| `python scripts/run_mutation_gate.py --check-report` | exit 0; current report, 29/29 active mutants killed (100%); M27/M29 triage recorded |
| `python scripts/sync_review_docs.py` | exit 0; current |
| `python scripts/sync_customer_faq.py` | exit 0; current |
| `python scripts/sync_github_issues.py --repo SoloMidMiram/Iranian-Auto-Body-Insurance-Claim-Calculation-Knowledge-Graph` | exit 0; dry-run manifest valid |

The four preserved expected failures are IA-05 incomplete title transfer,
IA-08 unversioned manual franchise, and both IA-14 missing-salvage variants.

The separately committed inspection corpus at
`fa214d940cbfe79389ff1269800e52a69bff13b8` ran 47 supported cases and 14
internal probes against this worktree. Its complete output matches the recorded
integration case-result sections; revision, tree and absolute import-path
metadata differ as expected for the corrected worktree. The focused override
investigation blocks all incomplete final-branch variants, retains the 9,000
IRR evidence-complete override, and leaves ordinary theft pending on its theft
criterion. No inspection documentation was imported into this runtime change.

## Risk, rollback, and review

The behavioral risk is intentional fail-closed expansion: a previously payable
override with incomplete threshold evidence now blocks. Amounts for complete
cases do not change. The main compatibility risk is a caller that used an
override as a substitute for missing classification facts; that use violated
the documented evidence contract and must provide the missing operands rather
than receive a legacy bypass.

Rollback is one local commit reverting the validator, its reconciliation gate,
tests, mutation and this evidence record. Such rollback would reopen a
demonstrated payment vulnerability and must keep release blocked.

Independent engineering review must inspect candidate-branch selection,
non-overridability, Review/engine boundary distinctions, mutation adequacy and
unchanged complete controls. Domain review must confirm only that an override
does not substitute for a required assessment; it must not use this PR to
approve rescue scope, disposition, title, salvage, franchise, or theft-clock
interpretations. Passing tests alone do not satisfy either review requirement.
