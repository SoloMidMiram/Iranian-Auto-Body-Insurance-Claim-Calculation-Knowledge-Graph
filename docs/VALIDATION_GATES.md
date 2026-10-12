# Validation gates and case criteria

## Gate policy

Passing tests is necessary but not sufficient. Each phase produces an evidence
bundle containing command output, reviewed source records, case results, and any
approved exceptions. A gate fails when evidence is missing or indirect.

Python 3.11 is the only supported interpreter for installation and validation.
Virtual environments, dependency installation, repository commands and evidence
must use the same Python 3.11 interpreter; historical results from other Python
versions are not current acceptance evidence.

The standard repository gate is:

```bash
python -m compileall -q claim.py src scripts
python claim.py validate
python claim.py fixtures
python -m pytest
python scripts/run_mutation_gate.py --check-report
python scripts/sync_review_docs.py
python scripts/sync_github_issues.py \
  --repo SoloMidMiram/Iranian-Auto-Body-Insurance-Claim-Calculation-Knowledge-Graph
```

The issue sync command is a dry run unless `--apply` is explicitly supplied.

`python claim.py validate` also checks the body-operator authority chain:
operator, rule, source, authority class, effective date, and branch scope.
Source tiers are not rewritten. A missing reviewer or a `PRIMARY_MIRROR`
source is printed as a finding and does not by itself fail the gate.
Incomplete source metadata (locator, content hash, retrieval date, effective
interval, revalidation date) is also printed as a finding. A past revalidation
date does not fail the release gate in this phase.
Incomplete source metadata (locator, content hash, retrieval date, effective
interval, revalidation date) is also printed as a finding. A past revalidation
date does not fail the release gate in this phase.

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
11. No calculation runs without an authorization. `compute()` accepts a
    `CalculationAuthorization` only; `REFUSE` and `INSUFFICIENT_INFORMATION`
    cannot produce one, and a payload edited after issuance fails its hash check.

Monetary calculations retain exact decimal intermediates. The engine rounds only
final payable amounts and payable scenarios to the nearest IRR, using
`ROUND_HALF_UP`. Conversion to toman-based units is explicit presentation logic
and never changes a persisted or engine input.

## Minimum boundary corpus

### Input and money

- Missing unit; unknown unit; conflict between unit and `_irr` field.
- Negative, boolean, `NaN`, infinite, over-precision, and extremely large money.
- Missing one of insured sum/market value where the ratio is assessed.
- Production year after claim year and unsupported Iranian year.
- Declared/derived classification match, conflict, insufficient evidence, and a
  documented authorized override with actor, reason, source, and timestamp.
- Unknown fields, categories, branches, variants, and enum spellings.
- Numeric strings and string booleans rejected at the claim boundary; JSON `false`
  and numeric zero preserved through normalization.
- Malformed itemised and shorthand parts rejected rather than skipped or defaulted.
- Itemised depreciation rejected until both event year and production year are sourced.

### Partial damage

- Fully insured claim where ratio order is immaterial.
- Underinsured claim returning both approved U01 scenarios.
- Missing franchise terms or authority must block on U02 with no single payable;
  explicit zero requires a versioned, referenced policy or endorsement term.
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

### Case review and parameter selection

- A question id outside the procedure, an inadmissible choice token, and a non-numeric
  money answer are each refused rather than ignored.
- `UNKNOWN`, `NOT_STATED` and `NOT_REVIEWED` bind nothing and must change the decision.
- A question whose trigger condition has not been met is reported as "not asked", never
  as an omission; and one gated off must not contribute evidence demands.
- No questionnaire binding may carry a numeric literal: answers select tokens, amounts
  come from a policy slot with a named source.
- Every slot a body branch requires is reachable by a question, a declared supplier, or
  derivation from evidenced slots.
- An authorized review's emitted case exactly matches the payload bound to its
  authorization; `calc` accepts the review-answer file and rejects the raw emitted
  case, while incomplete and refused reviews cannot export.
- Ladder assignment excludes the `always` fallback rung, so a well-formed file is not
  reported as uncertified; every `example_cases` entry must exist in the corpus.
- Licence state keeps its three-way distinction: void, wrong class and absent defeat
  cover, expired does not.
- Refusal, insufficiency and scenario-set decisions each have a worked file in `cases/`
  and a test that pins the outcome, not only the happy path.

## Calculation admission boundary

No amount may be produced without an authorization that names its issuer. The
boundary is a type, so a caller that skips the review gate fails at the call site
rather than silently computing:

- `compute()` refuses a raw payload, a `Case`, and any object that is not a
  `CalculationAuthorization`.
- `Review.authorize()` raises `AuthorizationNotGranted` on `REFUSE` and
  `INSUFFICIENT_INFORMATION`, so neither outcome can reach the engine.
- The authorization owns immutable canonical JSON snapshots of the validated claim
  and provenance. Its private `init=False` factory grant is lost on
  `dataclasses.replace()`, and `compute()` materializes a fresh validated `Case`
  after verification instead of consuming any mutable pre-issuance view.
- Returned claim and provenance values are detached copies. Mutating them cannot
  change a later calculation or its emitted review record. This is an architectural
  Python API boundary, not cryptographic hostile-process security.
- A forged decision token (`REFUSE`, `INSUFFICIENT_INFORMATION`, or any value
  outside the authorized set) fails `verify()` before any arithmetic runs.
- Every result reports `authorization` provenance: issuer, decision, claim hash,
  reviewer, tier, classification record, snapshot id, live uncertainties.
- Risk intensification is a hard review gate: `YES` activates blocking `U15`,
  while `UNKNOWN` or omission leaves the material fact unresolved. The engine
  independently fails closed on
  `coverage_gate.risk_intensified` for every body branch, returning
  `RISK_INTENSIFICATION_PREMIUM_RATIO_UNRESOLVED` with no payable and no scenario
  collapse. The underinsurance ratio is never substituted for the premium ratio.
- `claim.py calc` and `json` accept review-answer files and use
  `Review.authorize()`. Raw claim cases are rejected. The fixture corpus and
  mutation probe use the private, schema-validating internal path and report
  issuer and authorization kind as `INTERNAL_TEST_DIRECT`; no production path
  falls back to it.

## Body calculation properties and mutation gate

The deterministic examples remain regression anchors. Generated cases use fixed
seeds so failures reproduce exactly and enforce these properties across a wider
input range:

- Holding all other facts fixed, increasing eligible partial loss cannot reduce
  the payable.
- Holding all other facts fixed, increasing the franchise cannot increase the
  payable.
- Removing required franchise economics cannot improve a claim from blocked to
  a single payable.
- A total-loss or whole-theft payable is non-negative and cannot exceed the
  insured sum.
- For each real partial and glass sequence, the graph walk equals the independent
  legacy parity oracle; swapping ratio and franchise still changes the amount.

The calculation-module mutation gate is defined in
`docs/MUTATION_REPORT.md`. Its curated high-risk mutation set must score at least
90%; the report is regenerated and checked by `scripts/run_mutation_gate.py`.

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
