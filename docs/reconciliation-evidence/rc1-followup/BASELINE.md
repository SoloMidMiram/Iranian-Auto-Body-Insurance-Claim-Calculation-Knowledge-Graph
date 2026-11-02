# RC-1 follow-up baseline — 2026-11-02

Fresh GitHub connector inspection and git fetch agree with the supplied snapshot. Main: 37b1765af89121bf04ef590f729f1cd861e3c254. All five PRs remain OPEN and unmerged.

| PR | Head | Base |
|---|---|---|
| 48 | cd7fb39a0b7859f2cec91b94770e240ab62e0b75 | main |
| 57 | cb7bce78e8704378539f915f5d4ffd9be943a597 | #48 |
| 58 | 49b2446f4ac2674f5bbbd81b5d3bc513e1e77133 | #48 |
| 59 | 1e41c67c7f892526f52aecd40267709592383444 | #48 |
| 60 | 81ee520851ade552ce85b49b60eb817f2c8ec8d3 | #48 |

PR #60 is draft. Repository-gate run 41476049390 succeeded. Historical baseline: 739 tests, 50 fixtures, 38 mutants; these are not results for a new correction. Its merge base is #48. Runtime, schema, knowledge, fixture, test and original-input paths equal executable candidate 5cee269. #57 has seven unresolved threads, six with prior author responses; the actual-byte/index-flag finding PRRT_kwDOUgc9bM6sIHGl has no correction. #58/#59/#60 have no inline threads. #48's older clock threads are resolved.

A clean worktree starts from actual #60. Following the user's directory constraint, active work moved into `.qwen/worktrees/rc1-followup` under the original workspace on `codex/rc1-independent-reconciliation`. The earlier managed worktree is preserved without further writes. Existing user changes remain untouched. Read README, ROADMAP, VALIDATION_GATES, RC1 audit, corpus README, existing identities, authority report/checklist, planning manifest, provenance and regression sources before code edits. Provenance initially trusts status, allowing flagged hidden edits. Parent reproduction precedes correction.

Frozen original comparison: 6 MATCH / 41 MISMATCH. Separate synthetic comparison: 36 MATCH / 6 KNOWN_DEVIATION / 5 MISMATCH. Both gates fail. Preserve original/synthetic inputs, manifests and historical observations. Source-token identity does not authenticate a contract.

Issue #49 remains open; two qualified human reviewers, independent acceptance, accessible artifacts, pinned identities and clean main CI remain required. No insurer selected. No merge, closure, tag or final acceptance review will be performed. Publication for review is authorized.

Documentation contradictions: this integration README still advertises historical Stage0 515 passed / 11 xfailed; supplied main count 467 is a separate historical state. ROADMAP presents Oct7–13 as current; VALIDATION_GATES repeats the source-metadata limitation paragraph. Reconcile after implementation, preserving history.
