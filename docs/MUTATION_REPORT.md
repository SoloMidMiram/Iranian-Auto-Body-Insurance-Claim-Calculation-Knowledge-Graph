# Body Calculation Mutation Report

This is a reproducible, curated high-risk mutation set for the deterministic
body calculation boundary. It is not a claim of exhaustive mutation coverage.

- Target modules: `plans.py`, `operators.py`, the guard-plan gate in `engine.py`, Review operand construction in `review.py`, canonical calendar validation in `dates.py`, and the authorization boundary in `admission.py`
- Required score: **90%**
- Result: **33/33 killed (100.0%)**
- Command: `python scripts/run_mutation_gate.py --check-report`

| Mutant | Result | Safety property |
|---|---|---|
| M01 | KILLED | ratio changes from multiplication to addition |
| M02 | KILLED | franchise is added instead of deducted |
| M03 | KILLED | rescue is deducted instead of added |
| M04 | KILLED | salvage is added instead of deducted |
| M05 | KILLED | insured-sum cap becomes a floor |
| M06 | KILLED | non-negative floor is inverted |
| M07 | KILLED | missing active operator is accepted |
| M08 | KILLED | rescue cap becomes a floor |
| M09 | KILLED | strict total-loss boundary becomes inclusive |
| M10 | KILLED | fully insured claim receives a zero ratio |
| M11 | KILLED | a bypassed required guard is accepted |
| M12 | KILLED | the immutable claim snapshot no longer has to match its issued hash |
| M13 | KILLED | a REFUSE or INSUFFICIENT_INFORMATION decision reaches the calculator |
| M14 | KILLED | risk intensification is settled at full amount instead of blocked on U15 |
| M15 | KILLED | an internal or metadata-mismatched capability can masquerade as review-issued |
| M16 | KILLED | dataclasses.replace can transplant a modified private grant onto another claim |
| M17 | KILLED | Article 8 explicit zero is replaced by the corresponding-damage cap |
| M18 | KILLED | one exclusion clause can replace the required causal conjunction |
| M19 | KILLED | depreciate-then-cap deducts scheduled depreciation a second time |
| M20 | KILLED | percentage franchise ignores its named calculation base |
| M21 | KILLED | a review-live uncertainty disappears from the deterministic result |
| M22 | KILLED | total-loss settlement base is silently aliased to the post-salvage base |
| M23 | KILLED | a non-leap Shamsi year accepts Esfand 30 |
| M24 | KILLED | the theft clock can use a date that disagrees with its selected event |
| M25 | KILLED | repair-only work receives replacement-part depreciation |
| M26 | KILLED | Review drops evidenced rescue from the total-loss classification numerator |
| M27 | KILLED | omitted material rescue is treated as zero and allowed to authorize payment |
| M28 | KILLED | a classification override bypasses the unresolved-rescue payment gate |
| M30 | KILLED | a classification override bypasses final-selected-branch evidence completeness |
| M31 | KILLED | an incomplete title transfer can use the insurer-title no-salvage route |
| M32 | KILLED | missing or not-applicable physical salvage disposition bypasses containment |
| M33 | KILLED | missing retained salvage valuation bypasses its explicit guard |
| M34 | KILLED | a positive monetary franchise bypasses source identity/version validation |

## Triaged mutation survivors

- **M27 was missing coverage, not equivalent.** The probe now includes an ordinary
  evidence-derived threshold route without an override. Mutating its omitted-rescue
  gate produces a payable and is killed.
- **M29 was equivalent under the corrected final-branch contract and is retired.**
  Its candidate-branch disjunct duplicated `_final_selected_branch_evidence_gap`;
  removing that disjunct leaves the focused and complete probes unchanged. M30
  directly mutates the controlling final-selected-branch condition and is killed.

A surviving mutant or a score below the threshold fails the gate. The checked-in
report must exactly match a fresh run.
