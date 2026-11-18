# Phase B remediation plan — disposition, salvage, and franchise authority

This plan is bounded preparation. It changes no runtime behavior, removes no
expected-failure marker, resolves no legal interpretation, and grants no release
authority. Proposed parent is accepted integration
`cd7fb39a0b7859f2cec91b94770e240ab62e0b75`, or its inspected successor after
the residual override remediation below. Release remains **BLOCKED**.

## Prerequisite: residual threshold-override containment

Before the four Phase B findings, land a small independent remediation for the
confirmed theft-to-total-loss override defect recorded in
`CASE_BASED_INSPECTION_CURRENT_2026-10-12.md`.

- Boundary: `reconcile_classification()` final candidate selection, before
  total-loss dispatch.
- Invariant: selecting a threshold-dependent branch by override does not waive
  repair/replacement assessment, event-date market value, or resolved
  classification rescue.
- Parent-fail evidence: `DIR-01`, `DIR-05`, and `DIR-09` settle 9,000 / 9,200 /
  9,000 with missing repair evidence.
- Fix-pass controls: all three become structured nonpayable; missing market and
  conflicting rescue stay contained; the complete override still settles;
  ordinary theft without an override remains governed only by theft evidence.
- Scope exclusion: do not redesign override authority, theft clocks, salvage,
  title transfer, or franchise terms in this remediation.

## PR-B1 — closed total-loss disposition contract (IA-05, IA-14A, IA-14B)

These findings should be one PR because they are three failures of the same
exclusive state machine at Review and engine boundaries. Splitting them would
temporarily permit one boundary to reinterpret a state rejected by the other.

### Current failures and risk

Fresh parent command:

```bash
python -m pytest -q --runxfail \
  tests/test_stage0_counterexamples.py::test_ia05_incomplete_title_transfer_cannot_pay_total_loss \
  tests/test_stage0_counterexamples.py::test_ia14_internal_total_loss_missing_salvage_cannot_pay
# exit 1: 3 failed
```

| Finding | Current reproduction | Financial risk |
|---|---|---|
| IA-05 | Supported Review accepts `INSURER_TAKES_TITLE` + `NOT_TRANSFERRED`; pays 7,300,000,000 | Salvage is waived before the insurer has acquired title |
| IA-14A | Internal total loss with missing disposition and salvage pays 1,900 | `Case.salvage_disposition` converts absence to `NOT_APPLICABLE`; settlement deducts zero |
| IA-14B | Internal `INSURED_RETAINS` with missing valuation pays 1,900 | `_settle_total_loss()` converts missing salvage to zero |

### Required invariant and evidence

Every physical total-loss settlement must select exactly one complete route:

1. `INSURER_TAKES_TITLE`: completed transfer is true and bound transfer proof is
   present; salvage is not deducted.
2. `INSURED_RETAINS`: an explicit, source-supported salvage valuation is present
   (including an explicit evidenced zero where legitimately supported); salvage
   is deducted before the applicable franchise.
3. Missing, `UNRESOLVED`, in-progress/not-transferred, or `NOT_APPLICABLE` in a
   physical total loss is nonpayable. `NOT_APPLICABLE` remains blocked without
   deciding RQ-07.

Evidence dependencies: authenticated Regulation 53 Article 19 text and
applicability; the title-transfer checklist/evidence standard; salvage
assessment artifact with issuer/page/hash binding; circular
1400/401/146850 and repeal/applicability history for deduction order; human
domain acceptance. Containment does not require guessing the unresolved RQ-07
interpretation.

### Smallest safe implementation boundary

- Schema and `Case`: preserve absence distinctly; do not default disposition to
  `NOT_APPLICABLE` or missing salvage to zero.
- Review: make transfer completion and the matching evidence mandatory for the
  insurer-title route; require valuation evidence for retained salvage.
- Engine/guard: validate the complete exclusive route before `_settle_total_loss`
  calculates `after_salvage`, rescue, franchise, or payable.
- Provenance: trace selected route, transfer/valuation evidence identity, and
  explicit-zero status.
- Do not choose franchise base, settle RQ-07, alter the total-loss threshold, or
  activate a new disposition.

### Regression and acceptance matrix

| Case | Required result |
|---|---|
| Insurer takes title; transfer missing/false/in progress | Structured nonpayable; no arithmetic dispatch |
| Insurer takes title; completed transfer but proof absent | Structured nonpayable |
| Insurer takes title; completed, evidence-bound transfer | No salvage deduction; existing calculation control unchanged |
| Insured retains; valuation missing | Structured nonpayable |
| Insured retains; valuation document present but amount unbound | Structured nonpayable |
| Insured retains; positive supported valuation | Deduct exactly once before the already selected franchise base/order |
| Insured retains; explicit supported zero | Distinct from omission; permitted only with valuation provenance |
| Disposition missing, unresolved, or not applicable | Structured nonpayable for physical total loss |
| Reclassified partial → total loss | Same disposition gate applies; classification alone never authorizes payment |
| Whole theft settlement | Preserve its existing completed-title requirement and add no threshold rule |

Parent-fail/fix-pass: the IA-05 test and both IA-14 parameter IDs must fail on
the pinned parent and pass without `xfail` after the fix. C61 must stop paying;
C62 and C63 remain positive controls; C65/C66 remain blocked; INT-07/08 block;
INT-09 remains a valid control only when explicit zero is evidence-bound. Add a
mutation for each default-to-zero/default-to-not-applicable bypass. Run the full
Python 3.11 gate and the 47+14 inspection matrix.

Engineering review must inspect schema/default semantics, guard ordering,
Review/engine parity, and mutations. Domain review must accept the evidence
standard and the exact point at which title transfer is complete. Neither review
may infer RQ-07 from a passing test.

## PR-B2 — minimum applicable franchise authority (IA-08)

This follows PR-B1 so disposition containment is not obscured by a separate
contractual-authority change.

### Current failure and risk

```bash
python -m pytest -q --runxfail \
  tests/test_stage0_counterexamples.py::test_ia08_unversioned_manual_franchise_cannot_pay
# exit 1: pays 1,657,000,000
```

`Review._franchise_complete()` requires reference/version only when the amount
or rate is zero. A positive `INSURER_MANUAL` rate therefore passes on its source
enum alone. Engine source validation likewise checks the source class, not an
applicable instrument. A deduction can change payment without proof that its
rate, base, minimum, claim sequence, product, or effective period governs the
claim.

### Required invariant and evidence

Every monetary franchise—zero or nonzero, absolute or percentage—must bind to
an accepted policy, endorsement, or insurer-manual term with:

- insurer/product/coverage identity;
- stable instrument reference and version;
- effective interval covering the event/policy snapshot;
- mode, rate/amount, named base, minimum when applicable, and claim-sequence
  rule as distinct typed terms; and
- reviewer acceptance/provenance sufficient to show applicability.

A source enum, free-text label, undated web page, or unversioned manual is not
authority. This PR does not choose a universal rate or resolve Article 10,
salvage/franchise ordering, RQ-03, or RQ-04.

### Smallest safe implementation boundary

- Extend the franchise contractual term schema only as needed to carry typed
  reference, version, applicability, and accepted-term provenance.
- Apply one shared completeness/applicability validator in Review and engine;
  remove the current positive-versus-zero asymmetry.
- Preserve omission versus explicit zero and existing named-base behavior.
- Fail closed before `_resolve_franchise()` changes a payable; emit stable
  authority-required status and trace missing fields.
- Do not ingest or activate any new insurer rate in this PR.

### Regression and acceptance matrix

| Case | Required result |
|---|---|
| Positive manual rate with no reference/version | Structured nonpayable (IA-08) |
| Zero rate with no reference/version | Structured nonpayable; existing control preserved |
| Reference but no version/effective interval | Structured nonpayable |
| Wrong insurer/product/coverage | Structured nonpayable |
| Event outside effective interval | Structured nonpayable |
| Conflicting policy and endorsement terms | Structured conflict; no precedence guess |
| Complete applicable absolute term | Existing amount unchanged |
| Complete applicable percentage/base/minimum term | Existing amount unchanged and provenance traced |
| Missing franchise | Existing U02 block remains; never defaults to zero |

Parent-fail/fix-pass: IA-08 and C101 fail on the parent and pass nonpayably after
the correction; C13D and every versioned positive/zero control retain their
amounts. Add engine-boundary equivalents so a direct authorization cannot avoid
the same validator. Add mutations removing reference, version, applicability,
and accepted-term checks. Run the full Python 3.11 gate and inspection matrix.

Engineering review must examine type/schema compatibility, all callers,
effective-date matching, and fail-closed statuses. Domain review must approve
the contractual evidence standard and applicability logic; it must not approve
any rate merely because the model can calculate it.

## Ordering and release gate

1. Residual override operand-completeness remediation.
2. PR-B1: IA-05 + IA-14A + IA-14B closed disposition state machine.
3. PR-B2: IA-08 applicable franchise authority.
4. Clean-checkout Python 3.11 repository gate, 47 supported inspection cases,
   14 original boundary probes, the residual investigation matrix, fresh
   mutations, and independent engineering/domain review.

Remove only the corresponding `xfail` markers after parent-fail/fix-pass proof.
PR #48 stays open against `main`; issue #49 remains authoritative. None of these
PRs grants production payment authority. Release remains **BLOCKED**.
