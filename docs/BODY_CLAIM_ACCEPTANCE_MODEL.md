# Body Claim Acceptance Model (Regulation 53)

Status: research and adjuster decision support; not an unattended payment authority.

This is the compact operational architecture for a FAQ or conversational intake.
The complete questionnaire, parameter matrix, generated diagrams, and worked traces
remain in [BODY_CASE_REVIEW_MODEL.md](BODY_CASE_REVIEW_MODEL.md).
For a single end-to-end flowchart and concise recognition, acceptance,
authorization, calculation, and response patterns, see
[BODY_MODEL_OVERVIEW.md](BODY_MODEL_OVERVIEW.md).

## 1. Purpose, scope, and governing principle

Purpose: recognize a motor-body claim, decide whether it is sufficiently supported
to calculate, select the correct calculation branch, and return a traceable outcome.

Scope: **body insurance only** (`BODY`) — monetary damage to the insured vehicle.
The model excludes bodily injury, third-party financial liability, Article 8
non-conventional-vehicle calculations, and legal recovery. If one event contains
one of those issues, the FAQ must split it into another case rather than import its
rules into the body calculation.

Core principle: **decide whether calculation is allowed before calculating**.
Recognition is not acceptance, and acceptance is not a payable. The FAQ may collect
facts and select graph nodes; it may not invent a rate, policy term, clock anchor, or
operator order.

## 2. The core architecture

```text
Evidence
  -> Investigation
  -> Coverage decision
  -> Branch classification
  -> Parameter lock
  -> Issue decision
  -> Calculation engine
  -> Result + provenance + confidence
```

There are two execution layers, and the second one cannot be reached without a
ticket issued by the first:

| Layer | Responsibility | Must not do |
|---|---|---|
| Review/acceptance | Establish facts, evidence, cover, branch, and parameter completeness | Calculate with defaults or guess missing terms |
| Calculation | Execute the selected branch and operators | Repair an incomplete file or silently change its branch |

The boundary between them is a typed object, not a convention.
`compute()` accepts a `CalculationAuthorization` (`src/iran_auto_claim/admission.py`)
and refuses a raw case payload, a `Case`, or anything else:

```text
raw claim -> review gate -> CalculationAuthorization -> compute() -> result
```

- `Review.authorize()` is the only normal claim-file authorization producer. It raises
  `AuthorizationNotGranted` on `REFUSE` and `INSUFFICIENT_INFORMATION`, so those
  two outcomes cannot reach the calculator at all.
- The authorization owns immutable canonical JSON snapshots of the exact validated
  claim and its provenance. Its private factory grant is `init=False`, so
  `dataclasses.replace()` creates an unissued object instead of transplanting the
  capability. `compute()` verifies the grant, decodes a fresh payload, validates it,
  and calculates only from that fresh `Case`. Returned payload/provenance copies may
  be mutated without changing later calculations. This is architectural in-process
  enforcement, not cryptographic security against hostile interpreter introspection.
- `claim.py calc` and `json` accept review-answer files and obtain their capability
  from `Review.authorize()`; a raw claim case is rejected. The legacy fixture
  corpus uses a private, schema-validating internal authorization helper and records
  issuer and authorization kind as `INTERNAL_TEST_DIRECT` in provenance. That
  helper is not exported by the package API and is never a production fallback.
- Every result carries `authorization` provenance: issuer, decision, claim hash,
  issue timestamp, reviewer, tier, classification record, snapshot id, live
  uncertainties and blocking conditions.

The FAQ is an adapter over the review layer. It is not a second rule engine.

## 3. Acceptance pipeline

```text
FILE -> COVER -> BRANCH -> PARAMETERS -> ISSUE
```

| Gate | Question | Pass condition |
|---|---|---|
| `FILE` | Is this an identifiable body-policy event? | Event, awareness and declaration dates; policy version; vehicle; driver; territory |
| `COVER` | Is there a covered causal event with no established defeating condition? | Policy in force, causation supported, exclusion state resolved, required endorsement identified |
| `BRANCH` | Which body engine applies? | Evidence-derived branch reconciles with any declared branch |
| `PARAMETERS` | Is every amount-affecting input sourced? | Values, franchise, year, order, caps, disposition and policy wording are locked or expressly unresolved |
| `ISSUE` | What may the system safely issue? | Exactly one of the four outputs below |

The only terminal review decisions are:

| Decision | Meaning | Calculation permitted? |
|---|---|---|
| `COMPUTE` | Branch and required inputs are complete and no material uncertainty is live | Yes, one result |
| `SCENARIO_SET` | Facts are complete, but a sourced rule/order has multiple defensible interpretations | Yes, every approved scenario; never average or select one silently |
| `REFUSE` | A coverage-defeating fact is established | No |
| `INSUFFICIENT_INFORMATION` | A fact, document, measurement, or policy term needed for the decision is missing | No |

`PENDING_60_DAY_CRITERION` and `TITLE_TRANSFER_REQUIRED` are engine outcomes inside
the theft branch, not substitutes for an incomplete intake.

## 4. Decision tree: body-claim branch classification

```text
Body claim after the coverage gate
|
|-- Whole-vehicle theft?
|     |-- clock not yet at 60 days -> THEFT / PENDING
|     |-- at least 60 days, title not transferred -> TITLE_TRANSFER_REQUIRED
|     `-- at least 60 days, title transferred -> THEFT total settlement
|
|-- Attempted-theft damage? -> PARTIAL_DAMAGE
|
|-- Partial-parts theft? -> endorsement terms required
|
|-- Repair + replacement + rescue strictly > 75% of event-date market value?
|     `-- yes -> TOTAL_LOSS
|
|-- Glass broke independently and the standalone endorsement applies?
|     `-- yes -> GLASS_ONLY
|
`-- otherwise -> PARTIAL_DAMAGE
```

Boundary rules:

- Exactly 75% is not total loss; it remains outside the total-loss branch.
- Glass damaged together with another covered event is part of the partial-damage
  claim. Only independent glass breakage can enter `GLASS_ONLY`.
- Whole-vehicle theft, attempted theft, partial-parts theft, and parts stolen after
  an accident are four different routes.
- The engine independently derives the branch and reconciles it with any declaration.
  Outcomes are `MATCH`, `CONFLICT`, `INSUFFICIENT_EVIDENCE`, or
  `AUTHORIZED_OVERRIDE`; only the first and last may reach branch arithmetic.

## 5. Knowledge graph to engine architecture

```text
Sources
  -> Rules and policy terms
  -> Knowledge graph
  -> Branch/operator graph
  -> Validation gate
  -> Review decision
  -> Calculation engine
  -> Result + provenance + confidence + unresolved variables
```

Source priority is statute, regulation, circular, applicable policy/endorsement,
dated insurer procedure, then educational material. A lower source may identify a
question but cannot override a higher source or create a formula.

### Verdict integration

A judgment or award becomes executable knowledge only after the repository records:

- issuing authority, chamber, case/decision number, date, and finality;
- the exact issue and holding, not only the final amount;
- whether the holding is general, case-specific, or evidentiary;
- temporal and policy-version scope;
- source file or stable URL, retrieval date, and document hash;
- conflicts with Regulation 53, circulars, or policy wording.

No distinct pair of verdict documents is present in this workspace. Therefore this
model does not assign either unnamed verdict a rule, formula, or precedence. Once the
two documents are supplied, they should enter through the source/contradiction review
path before they affect acceptance or arithmetic.

## 6. The critical safety gates

| Problem | Correct behavior | Current enforcement |
|---|---|---|
| Missing franchise terms | U02 with no single payable; never zero | Enforced at the shared engine boundary for review-to-engine and the synthetic fixture corpus; explicit zero requires versioned, referenced policy evidence |
| Missing production year where depreciation can apply | `INSUFFICIENT_INFORMATION`; never assume 0% | Review gate enforced and regression-tested. The claim schema also refuses an itemised-parts case with no `regulatory_snapshot.iranian_year` and no production year |
| Theft-clock anchor ambiguity | Return pending/anchor scenarios or request the dated source; never pick a clock silently | U13 blocks every whole-vehicle theft in review; no engine handoff until explicit clock inputs are modeled |
| Underinsurance order unresolved | Return both approved scenarios; never choose or average | Enforced by `U01` and the partial-loss engine |
| Unresolved risk intensification | No payable; never substitute the underinsurance ratio | `Q-S3-07` is a hard review gate: `YES` activates blocking `U15`, while `UNKNOWN` or omission leaves the material fact unresolved. The engine also fails closed on `coverage_gate.risk_intensified` for every body branch. |

These gates separate two kinds of uncertainty:

- Missing fact or contract term -> `INSUFFICIENT_INFORMATION`.
- Complete facts but unresolved rule/operator order -> `SCENARIO_SET`.

## 7. Calculation model

All persisted and engine-boundary amounts are non-negative integer IRR. The
repository converts them to `million_toman` only for human-readable output;
production data must never mix rial, toman, and million toman.

### Partial damage

Parts are **added**, not subtracted, and allowable rescue is **added**, not deducted:

```text
eligible_parts = sum(min(assessed_loss, special_part_cap_if_any))
gross_eligible = labour + eligible_parts
after_depreciation = gross_eligible - replacement_part_depreciation
ratio = min(1, insured_sum / event_date_market_value)
allowable_rescue = min(actual_rescue, 20% * sourced_cap_base)
```

Fully insured, resolved case:

```text
payable = max(0, after_depreciation - policy_franchise + allowable_rescue)
```

Underinsured case with unresolved order:

```text
Scenario A = max(0, after_depreciation * ratio - franchise + allowable_rescue)
Scenario B = max(0, (after_depreciation - franchise) * ratio + allowable_rescue)
```

Operator rules:

- Glass and lamp glass: 0% depreciation. This does not automatically exempt them
  from underinsurance or from the applicable endorsement franchise.
- Other replaced parts: 0% before the fifth production-year index, then 5% per
  year, capped at 25%. The engine uses
  `event_year - production_year + 1`; this calendar interpretation is recorded as
  an implementation interpretation, not primary text.
- Battery and tyre: eligible loss is capped at 50% of new price. On an older vehicle,
  interaction between this cap and age depreciation remains unresolved (`U04`).
- Repair-only work: no replacement-part depreciation.
- Franchise: comes from the applicable policy/endorsement, including mode, rate or
  amount, base, minimum, coverage line, claim sequence, and source version. There is
  no universal statutory rate.
- Rescue: actual reasonable cost capped at 20% of the selected `total damage` base;
  the denominator is unresolved in edge cases (`U05`).

### Total loss

```text
is_total = repair_and_replacement + rescue_for_threshold
           > 0.75 * event_date_market_value

settlement_base = min(event_date_market_value, insured_sum)
```

If the insured retains the wreck:

```text
payable = max(0, min(insured_sum,
    settlement_base - probable_salvage - franchise + allowable_rescue))
```

If the insurer takes title, do not also deduct salvage. Do not apply the
underinsurance ratio a second time after `min(market value, insured sum)`.

### Theft and standalone glass

- Whole-vehicle theft reaches total settlement only after the 60-day condition and
  title transfer. The clock anchor must be sourced.
- Attempted-theft damage uses partial-damage arithmetic.
- Partial-parts theft requires its endorsement limit and franchise.
- Standalone glass requires its endorsement wording. The only universal arithmetic
  rule currently established is zero depreciation for glass/lamp glass.

## 8. Uncertainty is a feature, not a failure

```text
Unknown operator order
  -> do not guess
  -> calculate every approved scenario
  -> return differences, provenance, and confidence
  -> request insurer/source resolution
```

A scenario set is valid only when every factual and monetary input is complete. It is
not a way to hide a missing franchise, year, valuation, endorsement, or document.

Each FAQ answer must distinguish:

- `missing_information`: what must be obtained before calculation;
- `live_uncertainties`: what the authorities or contract do not yet resolve;
- `scenarios`: formulas and amounts for each approved interpretation;
- `resolution_artifact`: the exact circular, endorsement, worksheet, or verdict that
  would collapse the scenarios to one answer.

## 9. Validation ladder

| Rung | Capability added | Permitted result |
|---|---|---|
| T0 | Basic fully specified payable or zero with reason | one number / zero |
| T1 | Depreciation, categories, special-part cap, rescue ceiling | one number |
| T2 | Branch and boundary decisions | one number / pending / refusal |
| T3 | Underinsurance and unresolved operator order | scenario set |
| T4 | Missing policy or endorsement wording | insufficiency / escalation |
| T5 | Multiple policies, contribution, recourse | one number / review / refusal |
| T6 | Anything not certified | not certified / human review |

Passing a rung certifies only that outcome class. A scenario test does not certify a
single payable, and a 50-case arithmetic corpus does not prove that a real file's
documents are authentic or legally sufficient.

## 10. Current status and next engineering steps

Validated on 2026-10-05:

- knowledge graph integrity passes: 261 registered nodes;
- all 50 synthetic calculation fixtures pass;
- the complete automated suite passes: 467 tests;
- generated review documentation matches the graph;
- worked T1 review computes 165.70 million toman;
- worked T3 review returns 139.625 and 144.6875 million-toman scenarios;
- missing franchise terms or authority stop every body settlement path on U02;
- explicit zero franchise is accepted only from versioned, referenced policy evidence;
- no calculation path reaches the engine without an authorization, and the
  mutation gate kills hash, decision, and review-issuance bypass mutants (16/16).

Remaining gaps, in priority order:

1. Make structured event clocks first-class (`start_event`, `start_date`, `as_of`,
   calendar, elapsed days) and calculate every material theft-clock scenario. The
   engine still reads `days_vehicle_missing`, which is a derived output rather than
   a structured clock. The review gate blocks unanchored whole-vehicle theft before
   authorization, but the underlying field should still be redesigned.
2. The evidence id list's `if_absent` token is enforced. Document contents are still
   not verified: the gate trusts `evidence_present` rather than recording identity,
   issuer, date, version, and hash.
3. Classification still derives the glass and base-peril signals from free-text
   substring matching (`_looks_like_glass`, `glass_damage_from_base_peril`), which
   is why the Phase 2 exit clause "no branch relies on uncontrolled free-text
   classification" is not yet met.
4. Replace documented caller-supplied classification overrides with signed,
   role-authorized artifacts when the authenticated workflow is built.
5. Drive uncertainty liveness from graph predicates instead of duplicating it in
   Python.
6. Ingest the two verdicts after their actual texts and metadata are available.

### FAQ response contract

Every answer should use this shape, even when no amount is produced:

```json
{
  "scope": "BODY_ONLY | OUT_OF_SCOPE",
  "decision": "COMPUTE | SCENARIO_SET | REFUSE | INSUFFICIENT_INFORMATION",
  "branch": "PARTIAL_DAMAGE | TOTAL_LOSS | GLASS_ONLY | THEFT | null",
  "reason_codes": [],
  "missing_questions": [],
  "missing_evidence": [],
  "parameters": {
    "resolved": {},
    "unresolved": []
  },
  "calculation": {
    "unit": null,
    "formula": null,
    "inputs": {},
    "deductions": {},
    "additions": {},
    "payable": null,
    "scenarios": []
  },
  "provenance": {
    "rules": [],
    "policy_documents": [],
    "verdicts": []
  },
  "confidence": null,
  "next_action": null
}
```

The natural-language response should lead with the decision, explain why, list only
the next necessary questions, and show arithmetic only after the acceptance gate.
