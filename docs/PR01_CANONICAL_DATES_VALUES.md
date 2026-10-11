# PR-01 preparation and acceptance — canonical dates and monetary inputs

Release verdict: **BLOCKED**

Scope: IA-07 and IA-15 only. This change validates represented facts; it does
not activate a new insurance rule, choose a legal clock anchor, or alter
franchise/threshold authority.

## Integration baseline

The remote state was independently queried before implementation. PR #50 was
merged into `fix/body-runtime-blockers` on 2026-10-10. Its merge commit is
`f1a675f825bef484634c964d657d138c51ea40a3`, with parents
`a159aaedaae8a0f8142f3c45675e8b11a9cd0fd8` and
`9a65179abe9b0c400ac44d0d86d76003cc43c844`, and tree
`24d9659af753ec0dd78db32dad6ea7b9d690089e`. The PR-01 branch is
`fix/pr01-canonical-dates-values`, created at that exact merge commit in an
isolated worktree. The source worktree's unrelated changes were not staged or
modified.

Remote merge state and local reproduction are different evidence: the former
was observed from GitHub; all command results below were produced locally from
the named tree under CPython 3.11.15. PR #50's merge pins the audit above the
runtime branch; it does not approve PR #48, merge that work to `main`, or lift
the release block.

## Counterexample inventory

The three cases repaired by this PR are:

1. `tests/test_stage0_counterexamples.py::test_ia07_invalid_chronology_cannot_pay[invalid-event-date]`
2. `tests/test_stage0_counterexamples.py::test_ia07_invalid_chronology_cannot_pay[production-after-event]`
3. `tests/test_stage0_counterexamples.py::test_ia15_conflicting_part_aliases_are_rejected`

The eight remaining strict expected failures are:

1. `tests/test_stage0_counterexamples.py::test_ia01_prior_compensation_blocks_a_single_payable`
2. `tests/test_stage0_counterexamples.py::test_ia02_asserted_only_causation_blocks_a_single_payable`
3. `tests/test_stage0_counterexamples.py::test_ia03_repair_only_component_has_no_replacement_depreciation`
4. `tests/test_stage0_counterexamples.py::test_ia04_rescue_crossing_the_strict_threshold_classifies_total_loss`
5. `tests/test_stage0_counterexamples.py::test_ia05_incomplete_title_transfer_cannot_pay_total_loss`
6. `tests/test_stage0_counterexamples.py::test_ia08_unversioned_manual_franchise_cannot_pay`
7. `tests/test_stage0_counterexamples.py::test_ia14_internal_total_loss_missing_salvage_cannot_pay[disposition-absent]`
8. `tests/test_stage0_counterexamples.py::test_ia14_internal_total_loss_missing_salvage_cannot_pay[retained-value-absent]`

## Calendar and chronology contract

| Field | Calendar identification | Validation/role |
|---|---|---|
| Review `Q-S0-02`, `Q-S0-03`, `Q-S0-07` | Compatibility contract: `YYYY/MM/DD` is Shamsi; dash years 1300–1500 are legacy Shamsi; dash years 1600–9999 are Gregorian; all other combinations reject | Event, awareness and declaration facts |
| Claim `event.event_date`, `awareness_date`, `declaration_date` | Same compatibility contract | Same facts at the engine boundary; no Review-only bypass |
| Review `Q-S2-11`, `Q-S2-12`; claim `event.theft_clock.start_date`, `as_of_date` | Explicit `SHAMSI`/`GREGORIAN` metadata from `Q-S2-13`/`calendar`; canonical `YYYY-MM-DD` | Theft clock only; does not choose another legal/payment clock |
| Review top-level `as_of` | Dash compatibility spelling | Review provenance only; no event-effective or legal-clock comparison |
| `regulatory_snapshot.as_of_date` | Gregorian ISO date (`format: date`) | Evaluation/provenance cutoff; not an event snapshot selector |
| `classification.override.timestamp` | ISO Gregorian timestamp with offset/Z | Override provenance only |
| `regulatory_snapshot.iranian_year`, `vehicle.production_year_shamsi`, `damage.production_year` | Explicit Shamsi year integers | Derived claim year and production chronology |
| Knowledge effective dates used for body snapshots | Shamsi `YYYY/MM/DD` | Event dates are converted to this calendar before interval selection |

Explicitly calendared theft dates use `YYYY-MM-DD`. The slash form remains only
the documented legacy Shamsi compatibility spelling for non-theft claim dates.
Impossible Gregorian dates, impossible Shamsi month/day combinations, common-
year Esfand 30, and ambiguous years reject with stable `invalid_date` paths.
The 1600–9999 interval identifies the spelling as Gregorian; occurrence dates
outside the converter's supported Shamsi interval then refuse instead of
guessing an Iranian claim year or snapshot.

Shamsi validation and conversion use the same break-table leap predicate over
the complete supported interval (years 1–3177). Regression coverage walks every
year boundary and round-trips each final valid day; in particular,
`1635/12/30` and `1636/01/01` now have consecutive, distinct ordinals.

Field-specific chronology predicates are:

| Predicate | Basis |
|---|---|
| occurrence ≤ awareness | `Q-S0-03` and `PS_AWARENESS_DATE` define this as the insured becoming aware of **this loss**, not another actor's timestamp |
| occurrence ≤ declaration | `PS_EVENT_DATE.validation` says occurrence is not after declaration; `Q-S0-07` defines declaration as this loss being declared to the insurer |
| awareness ≤ declaration | `Q-S0-04` asks whether declaration was within five working days **of awareness**, and `PS_DECLARATION_DATE` is the corresponding insured-to-insurer declaration fact |
| production Shamsi year ≤ Iranian event year | production cannot occur after the insured event |
| supplied `iranian_year` = Iranian year derived from occurrence | prevents a caller selecting a different annual/snapshot year |
| theft-clock start ≤ theft-clock as-of | elapsed missing days cannot be negative |
| theft-clock start = selected occurrence/awareness/declaration fact | existing selected-event binding remains authoritative; equality is by parsed calendar day, not raw spelling |

Review provenance time, evaluation cutoff, policy-effective intervals and legal
clocks are kept separate. This PR does not compute five-working-day notice,
choose the unresolved theft clock anchor, or infer policy inception/expiry.
The three ordered fields are the one canonical occurrence, insured-awareness,
and insured-to-insurer declaration sequence for this claim. The predicates do
not order police reports, assessors, reviewers, evidence receipt, complete-
documents timestamps, evaluation cutoffs, or any other actor/process.
Equivalent Shamsi slash/dash spellings and equivalent Gregorian/Shamsi values
bind the same selected theft event; genuinely different days still reject.

Snapshot selection now uses the actual validated event day. A supplied year can
no longer fabricate `YYYY/12/29`. Year-only synthetic fixtures retain the open
snapshot rather than pretending an event day. Gregorian event dates are
converted to Shamsi only for claim-year and effective-snapshot selection.

## Monetary normalization matrix

### True aliases

These representations name the same fact, scope and integer-IRR unit. When two
or more are supplied, every value must be equal.

| Canonical fact | Accepted representations |
|---|---|
| labour | `damage.labor`, `damage.labor_irr` |
| gross assessed damage | `damage.gross`, `gross_damage`, `gross_damage_irr` |
| aggregate repair/replacement | `damage.repair`, `repair_total`, `repair_total_irr`, `repair_and_replacement_irr` |
| assessed depreciation | `damage.depreciation`, `assessed_depreciation_irr` |
| depreciable-parts base | `damage.depreciable_parts`, `depreciable_parts_base_irr` |
| actual rescue/transport | `damage.rescue`, `actual_rescue`, `rescue_transport_actual_irr` |
| rescue admitted to total-loss numerator | `damage.rescue_for_threshold`, `rescue_for_total_loss_test_irr` |
| insured vehicle event value | `damage.market`, `market_value`, `vehicle.market_value_at_event_irr` |
| insured sum | `damage.insured`, `insured_sum`, `vehicle.insured_sum_irr` |
| salvage value | `damage.salvage`, `salvage_value`, `vehicle.salvage_value_irr` |
| actual third-party loss | `damage.actual_damage`, `actual_financial_loss_irr` |
| Article 8 corresponding damage | `damage.corresponding_damage`, `similar_part_corresponding_damage`, `article8_corresponding_damage_irr` |
| third-party financial limit | `damage.policy_financial_limit`, `tp_limit`, `policy.third_party_financial_limit_irr` |
| explicit victim valuation | `damage.vehicle_value`, `victim_vehicle_value` |
| explicit conventional threshold | `damage.conventional_threshold`, `threshold` |
| item assessed loss | claim/Review part `assessed_loss`, `assessed_loss_irr` |
| Review item new price | `new_price`, `new_price_irr` |
| shorthand replacement loss | `loss`, `assessed_loss` |

`vehicle.production_year_shamsi` and `damage.production_year` receive the same
conflict check, but are calendar-year facts rather than money.
Malformed list/object values are rejected as `invalid_type` before alias
equality is considered; alias comparison never hashes or normalizes them.

### Distinct operands

| Operands | Required treatment |
|---|---|
| `rescue_transport_actual_irr` vs `rescue_for_total_loss_test_irr` | Actual settlement expense and threshold numerator remain separate |
| actual rescue vs `rescue_payable` | No equality rule: the former is incurred expense; the latter is a separately supplied reimbursable amount that must remain within actual expense (when both exist) and the applicable ceiling |
| assessed part loss vs battery/tire `new_price` | Assessment and special-part cap base remain separate |
| gross/repair amounts vs assessed depreciation/depreciable base | Actual, aggregate, and deduction operands remain separate |
| victim valuation vs insured vehicle event market value | Different vehicles/scopes may legitimately differ |
| explicit conventional threshold vs annual snapshot/knowledge threshold | Case evidence and annual parameter retain separate provenance |

### Fallbacks

Fallback use is preserved and is not converted into alias equality:

- victim valuation may fall back to event market value only in the existing
  branch context where the damaged vehicle is the victim vehicle;
- the conventional threshold uses an explicit case value first, otherwise the
  annual parameter for the Iranian claim year;
- `rescue_payable` reaches settlement as its own normalized operand; it is not
  copied into actual expense and the engine refuses it above the verified cap;
  actual expense continues through the cap operator. Candidate ceilings floor
  non-positive bases at zero, so an explicit zero payable cannot create a
  spurious denominator uncertainty; and
- a year-only synthetic body case uses the open loaded rule snapshot, never a
  fabricated year-end event date.

### Structured contractual terms

`policy.franchise` (mode, amount/rate, minimum, base, sequence and source), the
legacy scalar franchise carriers, and `calculation_config.franchise_rate` are
not aliases. They retain their existing authority checks and precedence. PR-01
does not decide applicability, invent a source, or reconcile competing contract
documents. The same preservation applies to annual-parameter source records and
other structured policy terms.

## Parent reproduction and acceptance

Environment:

```text
Python 3.11.15
pip 24.0 (invoked as /tmp/body-model-pr01-venv311/bin/python -m pip)
parent f1a675f825bef484634c964d657d138c51ea40a3
tree   24d9659af753ec0dd78db32dad6ea7b9d690089e
```

Parent counterexample command:

```bash
/tmp/body-model-pr01-venv311/bin/python -m pytest \
  tests/test_stage0_counterexamples.py::test_ia07_invalid_chronology_cannot_pay \
  tests/test_stage0_counterexamples.py::test_ia15_conflicting_part_aliases_are_rejected \
  --runxfail -q
```

Observed parent exit: `1`, three failures. Named reasons: invalid date still
authorized and paid; production after event still authorized and paid; unequal
part aliases did not raise `InputSchemaError`. The parent full gate was observed
locally as 515 passed / 11 expected failures. These are local observations, not
substitutes for GitHub check status.

Acceptance matrix:

| Check | Required result |
|---|---|
| Three repaired IDs as ordinary tests | pass; no xfail markers |
| Invalid/ambiguous Gregorian and Shamsi dates | stable `invalid_date` rejection at Review and claim boundaries |
| Event/awareness/declaration and production chronology | stable field-specific rejection |
| Event/claim year disagreement | stable `conflicting_year` rejection |
| Equal true aliases | accepted and normalized by the existing canonical consumers |
| Unequal true aliases | stable `conflicting_alias` rejection |
| Distinct/fallback/contract operands | accepted without an equality rule or new authority interpretation |
| Snapshot correction | actual event-day anchor; no invalid/year-end substitution |
| Valid T1 control | payable unchanged at 1,657,000,000 IRR; snapshot changes from fabricated `1404/12/29` to actual `1404/08/20` |
| Full Python 3.11 gate | clean; remaining eight xfails stay mapped to their named defects |
| Release verdict | **BLOCKED** |

Fresh implementation result: the three repaired IDs pass with exit `0`; full
pytest reports **559 passed, 8 expected failures** with exit `0`; fixtures are
50/50; independent invariants are 51/51; and the curated mutation gate remains
24/24 killed. Compilation, knowledge validation (with the pre-existing 22 body-
authority and 48 source-metadata findings), generated-review/FAQ checks, issue-
manifest dry run, JSON parsing and `git diff --check` all exit `0` under the
interpreter recorded above.
