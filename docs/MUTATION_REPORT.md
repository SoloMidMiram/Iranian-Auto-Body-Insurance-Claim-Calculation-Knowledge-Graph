# Body Calculation Mutation Report

This is a reproducible, curated high-risk mutation set for the deterministic
body calculation boundary. It is not a claim of exhaustive mutation coverage.

- Target modules: `plans.py`, `operators.py`, the guard-plan gate in `engine.py`, and the authorization boundary in `admission.py`
- Required score: **90%**
- Result: **16/16 killed (100.0%)**
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

A surviving mutant or a score below the threshold fails the gate. The checked-in
report must exactly match a fresh run.
