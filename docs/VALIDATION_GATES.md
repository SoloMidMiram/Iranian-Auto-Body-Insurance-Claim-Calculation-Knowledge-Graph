# Validation gates and case criteria

## Gate policy

Passing tests is necessary but not sufficient. Each phase produces an evidence
bundle containing command output, reviewed source records, case results, and any
approved exceptions. A gate fails when evidence is missing or indirect.

The standard repository gate is:

```bash
python -m compileall -q claim.py src scripts
python claim.py validate
python claim.py fixtures
python -m pytest
python scripts/sync_github_issues.py \
  --repo SoloMidMiram/Iranian-Auto-Body-Insurance-Claim-Calculation-Knowledge-Graph
```

The issue sync command is a dry run unless `--apply` is explicitly supplied.

## Universal invariants

Every supported calculation must satisfy all of these:

1. Money is finite, non-negative integer IRR at persistence boundaries.
2. Units are explicit; `_irr` fields cannot be interpreted in another unit.
3. Payable is never negative and never exceeds applicable actual-loss,
   contractual, statutory, or insured-sum ceilings.
4. Missing required economics produce a refusal or scenario set, never zero.
5. A blocking uncertainty cannot coexist with a single payable.
6. A declared classification must agree with evidence or carry a reviewed
   override.
7. Every amount-affecting input and operator appears in the audit trace.
8. Every source and policy term is effective for the event/policy snapshot.
9. Repeating a calculation against the same frozen snapshot is deterministic.
10. Invalid input and guard violations are machine-visible failures.

## Minimum boundary corpus

### Input and money

- Missing unit; unknown unit; conflict between unit and `_irr` field.
- Negative, boolean, `NaN`, infinite, over-precision, and extremely large money.
- Missing one of insured sum/market value where the ratio is assessed.
- Production year after claim year and unsupported Iranian year.
- Unknown fields, categories, branches, variants, and enum spellings.

### Partial damage

- Fully insured claim where ratio order is immaterial.
- Underinsured claim returning both approved U01 scenarios.
- Missing franchise terms must block on U02.
- Mixed glass, lamp glass, repair-only, ordinary part, battery, and tire items.
- Battery/tire old enough for U04; each approved resolution mode.
- Depreciation boundary at production-year indices 4, 5, and the 25% ceiling.
- Rescue below, equal to, and above its cap; unresolved denominator surfaced.
- Franchise greater than loss; percent with minimum; invalid/unsourced percent.

### Total loss

- Repair plus rescue below, exactly at, and one IRR above 75%.
- Missing repair/threshold evidence must not settle a declared total loss.
- Market below/equal/above insured sum without a second ratio application.
- Salvage retained, insurer takes title, and unresolved disposition.
- Salvage before franchise and insured-sum ceiling after rescue.
- Whole-vehicle theft at days 59, 60, and 61; title absent/present.

### Glass and theft endorsements

- Collision-caused glass routes to partial damage.
- Standalone glass without endorsement is outside cover.
- Endorsement token without economic wording blocks on U03/U11/U02.
- Underinsured standalone glass returns the approved scenario set.
- Attempted theft damage versus partial-parts theft; missing endorsement terms.

### Third-party and Article 8

- Non-vehicle property bypasses the passenger-car Article 8 classification.
- Passenger vehicle one IRR below, equal to, and above annual threshold.
- Actual loss below/equal/above policy limit.
- Missing Article 8 correspondence assessment blocks on U06.
- Actual loss zero and actual loss below corresponding damage never overpay.
- `min(actual, corresponding, policy_limit)` boundary combinations.
- Whole-car proportional method is always refused.
- Dual coverage with absent/present/disclosed body-policy franchise terms.

### Legal recovery

- Recovery below/equal/above prior body-insurer payment.
- Article 8 cap applied to recourse where applicable.
- Insured release or impaired subrogation produces human review, not a number.

### Knowledge ingestion

- Duplicate IDs within one file and across node classes.
- Unknown and stale references, invalid dates, expired validation cycles.
- Nested object/list contradiction and explicit non-conflicting extension.
- Lower, equal, and higher authority with effective-date precedence.
- Injected failure after each planned write proves atomic rollback.
- Concurrent writers cannot lose or interleave updates.

## Phase acceptance metrics

| Phase | Required evidence |
|---|---|
| 0 | All known unsafe paths reproduced then fixed; CI green on supported Python versions |
| 1 | 100% amount-affecting dependencies traced to source/derivation and effective interval |
| 2 | 100% branch-plan operators/guards proven invoked; graph mutation changes or invalidates execution |
| 3 | At least 5 approved worksheets per adapter, including boundary and missing-term cases |
| 4 | Independent golden corpus covers every supported branch and universal invariant |
| 5 | At least 100 dual-reviewed shadow claims; zero hidden blocking uncertainties |
| 6 | Multi-discipline sign-off, tested rollback, and machine-readable supported scope |

## Severity policy

- **P0:** potential wrong eligibility/payment, hidden uncertainty, corrupt audit,
  or unrecoverable knowledge mutation. Blocks all releases.
- **P1:** broad provenance, versioning, or operational-control failure. Blocks
  phase acceptance.
- **P2:** branch-specific correctness or material workflow gap. Must be scheduled
  before the affected scope is supported.
- **P3:** improvement with no known current correctness impact.
