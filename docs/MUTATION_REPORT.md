# Body Calculation Mutation Report

This is a reproducible, curated high-risk mutation set for the deterministic
body calculation boundary. It is not a claim of exhaustive mutation coverage.

- Target modules: `plans.py`, `operators.py`, and the guard-plan gate in `engine.py`
- Required score: **90%**
- Result: **11/11 killed (100.0%)**
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

A surviving mutant or a score below the threshold fails the gate. The checked-in
report must exactly match a fresh run.
