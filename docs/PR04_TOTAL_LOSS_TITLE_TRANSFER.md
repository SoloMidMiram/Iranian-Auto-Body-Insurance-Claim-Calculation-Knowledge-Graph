# PR-04 physical total-loss title-transfer completion

This change closes the bounded IA-05 payment path. It does not change a
financial formula, choose a salvage valuation, resolve IA-08 or IA-14, upgrade
a source, approve PR #58, or authorize release. Release remains **BLOCKED**.

## Baseline and parent reproduction

- Integration parent: `cd7fb39a0b7859f2cec91b94770e240ab62e0b75`
- Parent tree: `4c594155cf9404def9bb32896c711985f3abccb8`
- Interpreter: Python 3.11.15
- Review path: supported `Review -> authorize -> compute`

The five already-merged Stage 0 regressions for IA-01, IA-02, IA-03, IA-04
and IA-15 passed on the parent. Running the IA-05 strict counterexample with
`--runxfail` failed as intended: a physical total loss with
`INSURER_TAKES_TITLE` and `title_transferred=false` received a Review-issued
`COMPUTE` authorization and settled **7,300,000,000 IRR** while recording zero
salvage deduction.

```bash
python -m pytest \
  tests/test_stage0_counterexamples.py::test_ia01_prior_compensation_blocks_a_single_payable \
  tests/test_stage0_counterexamples.py::test_ia02_asserted_only_causation_blocks_a_single_payable \
  tests/test_stage0_counterexamples.py::test_ia03_repair_only_component_has_no_replacement_depreciation \
  tests/test_stage0_counterexamples.py::test_ia04_rescue_crossing_the_strict_threshold_classifies_total_loss \
  tests/test_stage0_counterexamples.py::test_ia15_conflicting_part_aliases_are_rejected -vv
# 5 passed

python -m pytest \
  tests/test_stage0_counterexamples.py::test_ia05_incomplete_title_transfer_cannot_pay_total_loss \
  --runxfail -vv
# failed: payable 7,300,000,000 IRR
```

## Corrected contract

`INSURER_TAKES_TITLE` is an intended disposition, not evidence that ownership
has already transferred. The no-salvage-deduction route is available only when
the existing `vehicle.title_transferred` fact is positively true.

- Review returns `INSUFFICIENT_INFORMATION`, records
  `TITLE_TRANSFER_REQUIRED`, and refuses authorization for `NOT_TRANSFERRED`,
  `IN_PROGRESS`, `NOT_APPLICABLE`, missing or otherwise unresolved transfer.
- The engine independently returns `TITLE_TRANSFER_REQUIRED`, no payable and
  guard `G_SALVAGE_XOR_TITLE_TRANSFER` for a direct incomplete insurer-title
  case.
- Completed transfer still deducts zero salvage and preserves the established
  payable.
- Retained salvage, unresolved disposition and whole-theft behavior are not
  changed.

The Review trigger now reads the recorded `Q-S4-09` disposition answer rather
than waiting for its later-bound slot. This preserves both true and false title
answers in the emitted case for physical total loss.

## Validation

The corrected branch was checked with Python 3.11 using the repository gate.

| Check | Result |
|---|---|
| Focused Review/engine/guard matrix | 12 passed |
| Knowledge validation | passed; existing 22 authority and 48 source-metadata findings retained |
| Fixture corpus | 50/50 passed; T21 amount unchanged |
| Full pytest suite | 629 passed, 3 expected failures |
| Curated mutation gate | 30/30 killed (100%); M31 covers the transfer bypass |
| Generated review documentation and customer FAQ | current |
| Planning issue manifest | valid dry run |

The three expected failures remain IA-08 and the two IA-14 engine-boundary
salvage cases. Removing IA-05's strict marker does not close either IA-14 case.

## Risk, rollback and review

The intended behavior change is fail-closed: callers that previously declared
an insurer-title disposition without proving completed transfer no longer
receive a payable. No settlement amount changes for complete cases.

Rollback is a revert of this bounded commit. That rollback would reopen the
demonstrated overpayment path and must keep release blocked.

Independent engineering review must verify both Review admission and the
engine guard, the questionnaire dependency, mutation M31 and unchanged positive
controls. A qualified insurance-domain reviewer must confirm the bounded rule
that completed transfer is required before the insurer-title/no-salvage route.
