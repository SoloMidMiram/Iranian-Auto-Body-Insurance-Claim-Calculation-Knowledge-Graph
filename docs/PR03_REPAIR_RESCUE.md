# PR-03: repair status and total-loss rescue

Status: **implementation baseline reproduced after the accepted PR #55 merge**

Scope: IA-03 and IA-04 only

Release status: **BLOCKED**

The preparation contract was first written against a pinned, unmerged PR #55
head. PR #55 has since received the required review and merged. This revision
records a fresh reproduction of the resulting integration parent before any
PR-03 runtime change. It supersedes the provisional baseline record without
rewriting the historical PR-01 or PR-02 evidence.

## Baseline and prerequisite

Fresh GitHub and Git inspection on 12 October 2026 established:

| Item | Verified state |
|---|---|
| PR #55 | Merged into `fix/body-runtime-blockers` on 11 October 2026 |
| PR #55 base | `fix/body-runtime-blockers` at `9859b9c736df98f6a27c69953083b64bbdb1165a` |
| Final accepted PR #55 head | `fix/pr02-eligibility-admission` at `aad981f15857f44d464778cff8c8f041265b42cb` |
| Accepted PR-03 parent | `origin/fix/body-runtime-blockers` at merge commit `a8a20472172fbb5700adcf7c52df639830fbd9f2` |
| Parent tree | `150091f01bbff30495abc29094a3e5a5e79070f3` |
| Merge parents | First: `9859b9c736df98f6a27c69953083b64bbdb1165a`; second: `aad981f15857f44d464778cff8c8f041265b42cb` |
| PR #48 | Still open from `fix/body-runtime-blockers` to `main`; not merged or retargeted |
| PR-03 target | `fix/body-runtime-blockers` |
| Newer integration commits | None after `a8a20472172fbb5700adcf7c52df639830fbd9f2` at reproduction time |

The final PR #55 history between its original base and accepted head is:

1. `775c311102adcb2fb018d66afd96dd0f153d995f`, parent `9859b9c...`, implements
   IA-01/IA-02 containment.
2. `8f10b9290a5dd82ccff86b50c957d328f4ad83cb`, parent `775c311...`, corrects
   the PR-02 integration-parent evidence record; and
3. `aad981f15857f44d464778cff8c8f041265b42cb`, parent `8f10b929...`, aligns
   graph recovery-guard outputs.

The integration merge is `a8a20472172fbb5700adcf7c52df639830fbd9f2`.
Its first parent is the preceding PR #54 integration head `9859b9c...`; its
second parent is the final accepted PR #55 head `aad981f...`. The additional
`aad981f...` graph-alignment commit was inspected and does not alter the IA-03
part calculation or IA-04 rescue/classification paths.

Implementation preparation uses the isolated worktree `/tmp/body-model-pr03`,
branch `fix/pr03-repair-rescue`, created at the exact accepted parent. It was
clean before this document was copied from the provisional preparation
worktree. The primary worktree and all pre-existing user changes remain outside
this worktree.

The preparation document is a separate, untracked worktree artifact:

| Artifact | Worktree record |
|---|---|
| `docs/PR03_REPAIR_RESCUE.md` | `?? docs/PR03_REPAIR_RESCUE.md` in `/tmp/body-model-pr03` before implementation |

It is not contained in parent tree `150091f01bbff30495abc29094a3e5a5e79070f3`.
That tree identifies file contents, not ancestry, and predates this document.
The former pre-merge prerequisites have now been satisfied: PR #55 merged
through the normal process, the resulting remote integration head and parent
order were fetched and verified, the intervening commit was inspected, an
isolated branch was created, and the complete parent reproduction below ran
before runtime implementation.

PR #48 must remain open against `main`. PR-03 must not merge or retarget PR #48,
merge PR #55 itself, or rewrite shared history.

## Controlling material read

No `AGENTS.md` exists in the pinned tree. The following controlling material
was read before preparing this specification:

- `CONTRIBUTING.md`;
- `docs/VALIDATION_GATES.md`;
- `docs/STAGE0_REMEDIATION_BASELINE.md`;
- `docs/PR01_CANONICAL_DATES_VALUES.md`;
- `docs/PR02_ELIGIBILITY_GATES.md`; and
- `tests/independent-body-model-audit-a159aaed.md` in full.

`CONTRIBUTING.md` requires both engineering and domain review for these
eligibility/calculation changes. The pinned audit supplies the two strict
counterexamples and the signed component-work truth table: repair-only work is
non-depreciable, replacement work is age-tested, labor is separate, glass and
lamp glass are exempt, and inconsistent category/status records are input
errors. The audit also preserves RQ-07 through RQ-09: PR-03 must not invent a
new rescue admissibility rule or battery/tyre interaction while applying the
documented replacement-only boundary.

## Accepted-parent reproduction

The isolated environment was created and addressed exclusively through its
Python interpreter:

```bash
/usr/bin/python3.11 -m venv /tmp/body-model-pr03-venv311
/tmp/body-model-pr03-venv311/bin/python -m pip install -e '.[test]'
```

Environment:

- Python `3.11.15`;
- pip `24.0`;
- pytest `9.1.1`;
- editable `iran-auto-claim==1.0.0`; and
- revision `a8a20472172fbb5700adcf7c52df639830fbd9f2`, tree
  `150091f01bbff30495abc29094a3e5a5e79070f3`.

The shell printed the unrelated pre-existing warning
`/tmp/pr75-audit-tools/env: No such file or directory` before commands. It did
not change any recorded exit code. The complete gate was:

```bash
/tmp/body-model-pr03-venv311/bin/python -m compileall -q claim.py src scripts
/tmp/body-model-pr03-venv311/bin/python claim.py validate
/tmp/body-model-pr03-venv311/bin/python claim.py fixtures
/tmp/body-model-pr03-venv311/bin/python -m pytest
/tmp/body-model-pr03-venv311/bin/python scripts/run_mutation_gate.py --check-report
/tmp/body-model-pr03-venv311/bin/python scripts/sync_review_docs.py
/tmp/body-model-pr03-venv311/bin/python scripts/sync_customer_faq.py
/tmp/body-model-pr03-venv311/bin/python scripts/sync_github_issues.py \
  --repo SoloMidMiram/Iranian-Auto-Body-Insurance-Claim-Calculation-Knowledge-Graph
git diff --check
```

Every command exited `0`. Compilation passed; structural knowledge validation
retained the known 22 body-authority and 48 source-metadata findings; fixtures
passed 50/50; pytest reported **587 passed and 6 expected failures**; the
checked 24/24 mutation report, generated Review documentation, bilingual FAQ
and issue manifest were current; the issue command remained a dry run; and the
worktree contained only this untracked specification. These are locally
observed results at the accepted merged parent, distinct from remote CI
evidence.

### Parent failures

The exact strict-counterexample command was:

```bash
/tmp/body-model-pr03-venv311/bin/python -m pytest \
  tests/test_stage0_counterexamples.py::test_ia03_repair_only_component_has_no_replacement_depreciation \
  tests/test_stage0_counterexamples.py::test_ia04_rescue_crossing_the_strict_threshold_classifies_total_loss \
  --runxfail -q
```

It exited `1` with exactly two failures:

| Test | Named failure, not setup/admission failure |
|---|---|
| `test_ia03_repair_only_component_has_no_replacement_depreciation` | The supported Review reached `COMPUTE`; `requires_replacement=false` survived normalization, but result depreciation was `120,000,000.00` IRR instead of zero. |
| `test_ia04_rescue_crossing_the_strict_threshold_classifies_total_loss` | The supported Review reached `COMPUTE`; repair `7,400` plus actual rescue `200` was classified from `7,400` alone as `PARTIAL_DAMAGE`, not `TOTAL_LOSS`. |

The parent diagnostics were:

| Observation | IA-03 | IA-04 |
|---|---:|---:|
| Review decision | `COMPUTE` | `COMPUTE` |
| Bound repair/replacement total | `1,600,000,000` | `7,400` |
| Bound actual rescue | `100,000,000` | `200` |
| Emitted threshold rescue | absent, read as zero | absent, read as zero |
| Market value | `8,000,000,000` | `10,000` |
| Derived threshold numerator | `1,600,000,000` | `7,400` |
| Strict threshold | `6,000,000,000` | `7,500` |
| Classification | `PARTIAL_DAMAGE` | `PARTIAL_DAMAGE` |
| Depreciation | `120,000,000.00` | zero because production year equals event year |
| Allowable settlement rescue | `100,000,000` | `200` |
| Payable | `1,432,000,000` | `6,860` |

For IA-03, both the Review-bound part and emitted `damage.parts` record retained
category `REPAIR_ONLY` and `requires_replacement=false`. The active execution
plan still ran `OP_SPECIAL_PART_CAP`, `OP_DEPRECIATION_REPLACEMENT_PART`,
`OP_UNDERINSURANCE_RATIO`, `OP_FRANCHISE` and `OP_RESCUE_CAP`; the replacement
operator reported the erroneous amount as `other_depreciation`.

For IA-04, Review bound `PS_REPAIR_TOTAL=7400`, `PS_RESCUE_ACTUAL=200` and
`PS_RESCUE_CAP_BASE=ASSESSED_GROSS`. It emitted
`rescue_transport_actual_irr=200` but no
`rescue_for_total_loss_test_irr`. The classifier trace therefore stated
`repair+rescue 7400 against 75% threshold 7500.00 -> total=False`. The partial
settlement path independently consumed and paid the uncapped `200` rescue,
proving that the defect is operand construction for classification, not failure
to normalize rescue generally.

The following unchanged controls passed with exit `0`:

```bash
/tmp/body-model-pr03-venv311/bin/python -m pytest \
  tests/test_engine.py::test_actual_and_payable_rescue_operands_remain_distinct_through_calculation \
  tests/test_engine.py::test_supplied_rescue_payable_above_actual_or_ceiling_is_refused \
  tests/test_operators.py::test_threshold_is_strictly_greater_than -q
```

Direct classifier probes also confirmed the current primitive: with repair
`7,400` and market value `10,000`, explicit threshold rescue `99` gives `7,499`
and partial damage, `100` gives exact equality and partial damage, and `101`
gives `7,501` and total loss. Actual rescue alone currently defaults the
threshold operand to zero. `rescue_payable=200` with no actual or explicit
threshold rescue also leaves the threshold operand at zero, which is the
required separation control.

## IA-03 contract: repair status and depreciation

### Field-to-consumer matrix

| Input or representation | Current normalization | Current consumers | Required PR-03 contract |
|---|---|---|---|
| Review Q-S4-03 list | Binds raw component objects to `PS_PART_CATEGORY`; omission of `requires_replacement` becomes `true` when Review emits `damage.parts` | Review derives `PS_REPAIR_TOTAL`/`PS_GROSS_DAMAGE`, gates component questions and U04, then issues the immutable payload | Preserve each explicit Boolean. `REPAIR_ONLY` supplies a documented `false` when the flag is omitted; explicit `REPAIR_ONLY + true` is a stable input error. Other itemized categories retain the legacy omission default `true`. |
| `damage.parts[].requires_replacement` | Optional Boolean; `Case.parts` applies `bool(value)` and defaults omission to `true` | `calculate_partial_damage` passes the record to `eligible_part_loss`, but that operator ignores the field | Make it a predicate of replacement depreciation. Explicit `false` must leave the assessed component in eligible repair cost while making scheduled/effective replacement depreciation zero. |
| `damage.parts[].category` | Closed set: `GLASS`, `LAMP_GLASS`, `BATTERY`, `TIRE`, `OTHER_REPLACEMENT_PART`, `REPAIR_ONLY` | Cap selection, depreciation exemption/rate, U04 liveness, Review question gates and total repair derivation | Category and work status remain separate. Glass/lamp glass remain exempt; battery/tyre caps remain applicable; `REPAIR_ONLY` can never be treated as replaced. |
| `damage.replacement_parts[]` | Legacy shorthand always normalized with `requires_replacement=true` | Same per-part engine loop | Preserve replacement-by-construction compatibility. Reject `type/category=REPAIR_ONLY` in this explicitly replacement-only carrier instead of silently choosing one meaning. |
| `battery_loss`, `tire_loss`/`tires_loss`, `lamp_glass`, `other_replacement_part` | Legacy scalar shorthands normalize as replacement records | Same per-part cap/depreciation loop | Preserve their current replacement-by-construction meaning. No new repair inference is introduced. |
| `damage.labor[_irr]` / `PS_LABOR` | Kept outside `Case.parts` and added to assessed and eligible cost | Repair total, partial-loss base and total-loss numerator | Remain fully included and never enter replacement depreciation. |
| Aggregate assessed depreciation or base/rate | Used only when no itemized parts exist | Aggregate partial-damage fallback | Unchanged. PR-03 does not infer item status inside an undifferentiated aggregate. |

The existing default is therefore retained only where the carrier itself or the
legacy category contract means replacement. PR-03 must not globally change all
missing flags to `false`, and it must not silently coerce strings or other truthy
values; the current Boolean type validation remains controlling.

### Operator and ordering contract

For an itemized component:

1. keep its assessed loss in assessed gross;
2. establish the normalized replacement predicate before determining whether
   replacement depreciation is applicable;
3. for non-replacement work, set scheduled and effective replacement
   depreciation to zero while preserving any independently applicable
   battery/tyre damage cap;
4. for replacement work, delegate the cap/depreciation interaction to the
   existing configured mode without imposing an order; and
5. include the resulting eligible component cost in the repair base before the
   existing ratio, franchise and rescue sequence.

The supported replacement-work modes remain exactly:

- `CAP_THEN_DEPRECIATE`;
- `DEPRECIATE_THEN_CAP`; and
- `CAP_ONLY`.

PR-03 must not select one of those modes, change their arithmetic, or make the
numbered component flow imply that the cap always precedes depreciation. When
the interaction is material and unresolved for replacement work, U04 must
continue to block.

Thus `requires_replacement=false` changes depreciation and deductions derived
from the after-depreciation base; it does not erase the repair cost. The current
5%-per-year schedule, fifth-year start, 25% ceiling, production-year logic,
glass exemptions, special-part cap and plan order remain unchanged.

U04 remains live for an old battery/tyre only when that component is actually a
replacement and both the cap and age schedule could apply. A repair-only
battery/tyre can still be capped under the existing component rule, but must not
be forced into the cap-versus-depreciation uncertainty after depreciation has
become inapplicable. This narrows liveness to the existing rule collision; it
does not choose a battery/tyre interaction.

## IA-04 contract: classification rescue

### Operand-to-consumer matrix

| Operand | Accepted carriers | Scope and current consumer | Required PR-03 handling |
|---|---|---|---|
| Repair/replacement assessment | `repair[_total][_irr]`, `repair_and_replacement_irr`, itemized parts plus labor, or Q-S4-11 aggregate | `Case.repair_total`; classifier numerator and branch handlers | This field excludes rescue. Q-S4-11 asks for repair and replacement, Q-S4-07 separately asks for rescue, and the rule defines the numerator as their sum. Clarify the ambiguous slot prose; never add rescue into this field. |
| Actual rescue expense | True aliases `damage.rescue`, `damage.actual_rescue`, `damage.rescue_transport_actual_irr`; Review Q-S4-07 / `PS_RESCUE_ACTUAL` emits the canonical field | `Case.rescue_actual`; settlement `_rescue` applies the configured 20% cap | When no explicit threshold operand exists, the evidenced Q-S4-07 actual amount is the documented classification fallback as well as the settlement actual input. Record that derivation; do not copy a capped amount back into actual. |
| Explicit threshold rescue | True aliases `damage.rescue_for_threshold` and `damage.rescue_for_total_loss_test_irr` | `Case.rescue_for_threshold`; `classify` and `calculate_total_loss` | Preserve as a distinct classification operand. Explicit presence, including explicit zero, takes precedence over the actual-expense fallback. It is never a settlement amount. |
| Reimbursable rescue | `damage.rescue_payable` | `Case.rescue_payable`; settlement `_rescue`, subject to actual and ceiling checks | Never use it for classification and never copy it into actual expense. The existing normalization and calculation tests remain controls. |
| Allowable/capped settlement rescue | Result of `_rescue` from actual or supplied payable and `calculation_config.rescue_cap_base` | Added by branch settlement plans | Never feed it back to classification. Classification happens before dispatch and before this cap is calculated. |
| Rescue-cap base | `ASSESSED_GROSS`, `ELIGIBLE_GROSS` or `SETTLEMENT_BASE` | Settlement ceiling and U05 only | Unchanged; it does not select the total-loss threshold operand. |

The precedence contract is:

1. if an explicit threshold operand is present, preserve and use it, including
   explicit zero;
2. otherwise, if actual rescue is present, derive the threshold operand from
   that amount and record `DERIVED_FROM_ACTUAL_RESCUE` provenance;
3. otherwise retain the legacy arithmetic-zero compatibility representation
   while recording `OMITTED_DEFAULT_ZERO`, not an invented fact that no rescue
   occurred; and
4. never fall back from `rescue_payable` or the capped settlement result.

Actual and explicit-threshold amounts are not aliases and need not be numerically
equal. If both are supplied with unequal values, PR-03 must not choose the
smaller, larger or settlement-favorable value and must not report an alias
conflict. It must keep both operands and require all of the following before an
explicit unequal threshold operand can control:

1. an assessment or equivalent case record that explains the different scopes
   and decomposes the actual, classification-eligible and settlement-payable
   amounts;
2. an applicable authority or contractual/decision artifact, bound to the
   claim's product, event date and relevant scope, that permits the selected
   threshold treatment; and
3. an explicit accepted interpretation recording the responsible reviewer or
   decision-maker, acceptance time, selected interpretation and artifact
   reference.

A source enum, free-form label, document name or bare provenance string is not
sufficient. Until all three elements can be represented and validated, the
case remains nonpayable with a stable unresolved-threshold reason. Equal values
may proceed while retaining their separate roles. This containment preserves
RQ-07 instead of deciding whether the legally applicable threshold cost is
actual, accepted or capped rescue.

`OMITTED_DEFAULT_ZERO` is limited to legacy compatibility; it is not evidence
that rescue did not occur. An unanswered Q-S4-07 or missing required assessment
evidence remains blocking in Review. With an unknown classification rescue
operand, a branch is safe only when one of these conditions is established:

- repair/replacement cost alone is already strictly above 75%, so any
  non-negative rescue leaves the result total loss;
- evidence establishes an explicit zero eligible classification rescue; or
- evidence establishes an applicable upper bound and repair/replacement plus
  that bound cannot cross the strict threshold.

Otherwise the unknown operand is material to classification and the result must
be `CLASSIFICATION_EVIDENCE_REQUIRED` or an equivalent stable non-authorizing
state. A legacy parser may retain zero for arithmetic compatibility, but the
admission/classification gate must not treat that representation as a factual
zero when it could change the branch.

If an aggregate repair assessment already contains rescue, it cannot be used
unchanged alongside a separate rescue operand. Evidence must decompose it into
repair/replacement excluding rescue and the applicable rescue operand. Where
that decomposition is unavailable and the overlap can change classification,
the case must block; it must not subtract, duplicate or estimate rescue.

The supported Review route has a narrower existing contract: Q-S4-07 asks for
actual incurred cost with invoices and states that the same cost participates
in the total-loss numerator. Its fallback is therefore documented rather than
guessed. Missing `EVT_ASSESSMENT_REPORT` remains `BLOCK_PARAMETER`; deriving a
classification operand must not satisfy the evidence gate or authorize a
payment.

The strict predicate remains:

```text
repair_and_replacement + eligible_classification_rescue
    > 0.75 * loss_date_market_value
```

Equality is partial damage. Decimal arithmetic and the existing M09 strictness
control remain unchanged.

### Classification is not authorization

Correcting IA-04 intentionally changes the `7,400 + 200` Review from
`PARTIAL_DAMAGE` to `TOTAL_LOSS`. That valid-input result change does not permit
a total-loss settlement. It makes the existing total-loss
salvage/disposition questions and evidence applicable; in the exact IA-04
fixture, the newly applicable missing salvage facts must prevent the former
partial dispatch/payable. PR-03 does not strengthen or certify those existing
requirements. IA-05 can still take the unsafe insurer-title path with
incomplete transfer, and IA-14 can still take unsafe internal missing-salvage
paths; their strict counterexamples must remain unchanged and expected to fail.
With a direct authorization, a declared partial branch that derives as total
must produce `CLASSIFICATION_CONFLICT`.

The same canonical threshold resolver must be used by `classify` and
`calculate_total_loss`, preventing a Review/engine mismatch.

## Bounded future patch

After the post-merge parent is verified and reproduced, the smallest reviewable
implementation is expected to touch:

- `src/iran_auto_claim/schema_input.py` and
  `schema/claim-case.schema.json` for the documented part-status combinations
  and threshold-operand descriptions;
- `src/iran_auto_claim/review.py` for canonical Review emission, U04 liveness
  and threshold provenance;
- `src/iran_auto_claim/case.py` for one normalized replacement predicate and
  one classification-rescue resolver that preserves omission and explicit zero;
- `src/iran_auto_claim/operators.py` for the replacement-only depreciation
  predicate;
- `src/iran_auto_claim/classify.py` and, only as needed for trace/containment,
  `src/iran_auto_claim/engine.py` for shared threshold resolution and a stable
  unresolved dual-operand outcome;
- `knowledge/parameter_slots.json`, `knowledge/operators.json` and
  `knowledge/review_procedure.json` to make replacement status and the
  repair-plus-separate-rescue contract explicit without changing rates or
  authority;
- focused operator, schema, Review, engine, property and Stage-0 tests; and
- mutation probes/report entries that kill an ignored replacement predicate and
  a dropped Review rescue-to-threshold handoff.

The patch must keep the current execution-plan order. No new insurance rule,
cap, rate, franchise, salvage treatment, title rule, endorsement behavior or
payment authority belongs in PR-03.

## Implementation sequence

1. Reverify and reproduce the accepted merged integration parent; preserve the
   fresh failure output above as the immutable parent evidence. **Completed at
   `a8a20472172fbb5700adcf7c52df639830fbd9f2`.**
2. Add ordinary tests for the matrices below while retaining the two strict
   xfail markers until the implementation makes them pass.
3. Centralize part work-status normalization and reject only the documented
   contradictions.
4. Gate replacement depreciation on normalized replacement status; update U04
   liveness without changing cap/depreciation ordering for replacements.
5. Centralize classification-rescue resolution with explicit-presence checks,
   source tracing and no payable-rescue fallback.
6. Route both Review classification and engine reconciliation/total-loss
   verification through that resolver.
7. Remove only the IA-03 and IA-04 xfail markers after their repaired tests pass
   ordinarily. Four expected failures should remain: IA-05, IA-08 and the two
   IA-14 parameter cases.
8. Update the knowledge descriptions, generated Review copies, bilingual FAQ,
   mutation probe/report and PR-03 evidence, then run the full clean gate.

## Acceptance matrix

### IA-03

| Case | Required result |
|---|---|
| Exact IA-03 Review counterexample | Primary invariant: replacement depreciation is `0` and repair-only `1,200,000,000` plus labor `400,000,000` remain eligible. `1,540,000,000` IRR is the expected downstream regression result under the otherwise unchanged franchise/rescue chain, but must be independently reproduced after the fix. |
| Same ordinary part, `requires_replacement=true` vs `false` | Assessed/eligible component and classification inputs unchanged; only replacement depreciation and downstream base-dependent amounts change |
| `REPAIR_ONLY` with omitted flag | Normalize to non-replacement under the documented category compatibility contract |
| `REPAIR_ONLY` with explicit `true` | Stable structured input error at Review and claim boundaries |
| `replacement_parts` containing `REPAIR_ONLY` | Stable structured input error; do not reinterpret the replacement-only carrier |
| Mixed repair-only, replacement, labor and glass | Repair/labor remain included; only replaced non-exempt parts depreciate; glass/lamp glass stay at zero depreciation |
| Old battery/tyre marked non-replacement | Existing cap preserved, depreciation zero, U04 not live; no interaction mode is selected |
| Old battery/tyre replacement | Existing U04 behavior and all three configured interaction outcomes remain unchanged |
| Aggregate explicit depreciation path | Unchanged; no inferred component status |
| Missing/invalid Boolean type | Existing structured validation remains fail-closed |

### IA-04

| Case, market `10,000` unless noted | Required result |
|---|---|
| Repair `7,499`, rescue `0` | `PARTIAL_DAMAGE` |
| Repair `7,500`, rescue `0` | `PARTIAL_DAMAGE`; equality trace explicit |
| Repair `7,501`, rescue `0` | `TOTAL_LOSS` |
| Repair `7,400`, Q-S4-07 actual rescue `99` | Numerator `7,499`; `PARTIAL_DAMAGE` |
| Repair `7,400`, Q-S4-07 actual rescue `100` | Numerator `7,500`; `PARTIAL_DAMAGE` |
| Exact IA-04 case: repair `7,400`, Q-S4-07 actual rescue `200` | Numerator `7,600`; `TOTAL_LOSS`; existing total-loss requirements are reevaluated and the fixture's missing salvage facts block the former partial dispatch. This does not close IA-05 or IA-14. |
| Actual rescue only | Threshold derives from actual with named provenance; settlement still caps actual independently |
| Explicit threshold only | Classification uses the explicit operand; settlement actual remains absent |
| Actual plus equal explicit threshold | Both roles and sources retained; one classification addition, no double counting |
| Actual plus unequal explicit threshold without qualified selection record | No min/max/equality guess and no payable. Proceed only with scope-decomposing assessment evidence, applicable authority and an explicitly accepted interpretation; a source label alone does not resolve it. |
| `rescue_payable` only | Never enters actual or classification; remains settlement-only and ceiling-checked |
| Actual plus `rescue_payable` | Existing above-actual and above-ceiling checks unchanged; threshold never reads payable |
| Omitted rescue vs explicit zero | Legacy arithmetic compatibility may match, but omission is not evidence of zero. Review remains blocking unless classification is invariant to the unknown non-negative operand or an evidence-backed zero/upper bound makes the branch safe. |
| Repair assessment excludes rescue plus a separate rescue operand | Rescue added exactly once; repair total remains rescue-exclusive |
| Repair assessment already containing rescue | Decompose repair/replacement and rescue using assessment evidence; if material decomposition is unavailable, block rather than count rescue twice or infer a subtraction. |
| Positive rescue with missing assessment evidence | Review remains non-authorizing regardless of the derived branch |
| Declared partial but rescue-derived total | `CLASSIFICATION_CONFLICT`, no dispatch/payable |

### Unchanged controls and gate

- Replacement rates, year-index boundaries and 25% cap remain unchanged.
- Glass/lamp-glass exemptions and battery/tyre configured modes remain
  unchanged.
- Actual, reimbursable and threshold rescue remain distinct.
- The settlement-rescue ceiling and U05 denominator behavior remain unchanged.
- Exact 75% remains partial; Decimal arithmetic remains controlling.
- IA-01/IA-02 admission gates and IA-07/IA-15 canonical input behavior remain
  unchanged.
- Both repaired tests pass with `--runxfail`; the full suite has four remaining
  expected failures; fixtures, validation, generated documents and mutation
  report are current from a clean checkout.

## Implementation evidence

The bounded implementation preserves repair-only assessed cost in the eligible
base while setting its replacement depreciation to zero. `REPAIR_ONLY` omission
normalizes to non-replacement; contradictory `REPAIR_ONLY + true` records and
`REPAIR_ONLY` entries in the replacement-only shorthand return structured
`contradictory_input` errors. Non-replacement battery/tyre work retains the
special cap without activating U04, while replacement work still exercises
`CAP_THEN_DEPRECIATE`, `DEPRECIATE_THEN_CAP`, and `CAP_ONLY` unchanged.

Review now emits actual rescue and a separate classification operand with
`DERIVED_FROM_ACTUAL_RESCUE` provenance. The classifier and total-loss handler
share the same resolver: explicit zero is preserved, actual is the documented
fallback, settlement `rescue_payable` is never a source, and omitted legacy
input is traced as `OMITTED_DEFAULT_ZERO`. Unequal actual/threshold operands
remain nonpayable until the repository can validate the required assessment,
authority and accepted interpretation. An assessment flagged as already
including positive rescue likewise blocks until it is decomposed.

Fresh post-change Python 3.11 evidence in the isolated worktree:

```bash
/tmp/body-model-pr03-venv311/bin/python -m pytest \
  tests/test_stage0_counterexamples.py::test_ia03_repair_only_component_has_no_replacement_depreciation \
  tests/test_stage0_counterexamples.py::test_ia04_rescue_crossing_the_strict_threshold_classifies_total_loss \
  --runxfail -vv
# exit 0: 2 passed

/tmp/body-model-pr03-venv311/bin/python -m pytest
# exit 0: 605 passed, 4 xfailed
```

The IA-03 regression now produces zero depreciation and the expected
`1,540,000,000` IRR payable. The IA-04 Review classifies `7,400 + 200` as total
loss; classification does not issue payment, and the newly applicable existing
total-loss evidence gates remain in force. The four preserved strict failures
are IA-05, IA-08, and both IA-14 variants.

## Documentation and generated evidence

The implementation updates source knowledge and regenerates
`docs/BODY_CASE_REVIEW_MODEL.md`; its generated blocks are mirrored into
`tests/BODY_CASE_REVIEW_MODEL.md`. The bilingual customer FAQ distinguishes
repair from replacement depreciation and classification rescue from
capped/reimbursable settlement rescue; `docs/CUSTOMER_FAQ.md` is regenerated
from `knowledge/customer_faq.json`.

M25 kills an ignored replacement predicate and M26 kills a dropped
Review-to-threshold rescue handoff. The regenerated current mutation report is
**26/26 killed**; historical 24/24 and Stage-0 records remain unchanged.
Validation confirms that `OP_DEPRECIATION_REPLACEMENT_PART` names the
replacement predicate and the total-loss rule still names separate
repair/replacement and rescue operands.

## Remaining blockers and exclusions

Even after IA-03 and IA-04 pass, release remains **BLOCKED**. The strict Stage-0
inventory still contains IA-05 (title/salvage disposition), IA-08 (franchise
authority) and two IA-14 engine-boundary salvage cases. Authority-dependent
IA-06, IA-09, IA-10 and IA-13, and graph/provenance work including IA-11 and
IA-12, also remain outside this PR.

In particular, reclassification can expose but does not repair the remaining
unsafe total-loss paths: IA-05 demonstrates payment through the
`INSURER_TAKES_TITLE` route without completed title transfer, while IA-14
demonstrates direct-engine payment with missing disposition/salvage or retained
salvage lacking a value. PR-03 must preserve those strict expected failures and
must not describe application of the current total-loss requirements as proof
that disposition containment is complete.

PR-03 does not implement title transfer, salvage containment, franchise
authority, endorsements, contribution formulas, theft clocks, notice/recourse
decisions, graph authority or production payment authority. It must not turn an
unresolved RQ-07 or RQ-09 alternative into executable law. Opening PR-03 does
not merge any PR or approve PR #48 for release.
