# Phase 2 Graph Authority Review

This is a planning checkpoint. It is not a GitHub issue.

## Before

- The graph described operators, scenarios, and branch scope.
- Python owned the ratio-versus-franchise formulas inside the body calculators.
- During the transition, `graph_partial_payable()` selected a legacy formula
  instead of walking the recorded sequence itself.

## After

- Partial and glass scenario order is read from `knowledge/branches.json` sequences.
- `src/iran_auto_claim/plans.py` now walks the recorded sequence directly. The
  legacy formulas remain callable only as independent parity oracles in tests.
- A swapped ratio and franchise sequence changes the scenario amount.
- Total-loss settlement walks salvage, franchise, rescue, and the insured-sum
  cap in graph order. Theft walks its smaller recorded plan.
- Each active body result records the exact sequence and a content-derived plan
  identity of the branch plus that sequence.
- A missing, duplicate, or unknown operator refuses the active body plan.
- Python still executes the approved arithmetic. It does not invent a second order.

## Verification

- Existing fixtures stay on the same payables. The repository test suite, including fixtures, was run on this checkpoint and passed.
- Hidden partial-order formulas no longer choose a scenario unless that scenario's sequence is in the graph.
- Third-party, Article 8, and legal-recovery calculators were not given a new execution plan. Issue #4 stays outside this checkpoint.
- P1-03 stays deferred. Provenance completion (#10) starts only after this checkpoint.

## Not claimed

- Every Python statement in the body calculators is a generic operator interpreter.
- Guard invocation on every path is proved here. That is #14.
- Overdue source metadata blocks release. That enforcement is later than #11.
