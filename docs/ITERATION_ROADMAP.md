# Iteration roadmap

## 2026-11-22 - Independent G0 evidence

Branch `codex/g0-independent-review-evidence`, based on main at
`37b1765af89121bf04ef590f729f1cd861e3c254`. The exact contribution HEAD
and PR verification are recorded in the dedicated evidence PR. No PR
existed when this entry was drafted.

The independent replay used Strategy B runtime
`1b41798f5725aa3d9bf8fce8cc8063a2baa45ea6` and tree
`d511963f90a18d695af2daf15e1f9014fe2759fe`. The contribution preserves
its 56 case records and commands. The historical replay passed 840 tests,
13 strict controls, 50 fixtures, and the mutation gate. Both frozen
comparisons exited 1. The published evidence removes workstation
identifiers and provides hashes for the original and published forms.
[Acceptance report](body-hardening/g0/G0_ACCEPTANCE_REPORT.md) |
[Evidence manifest](body-hardening/g0/G0_EVIDENCE_MANIFEST.json)

Engineering G0 remains NOT PASSED with 49 intentional refusals, one
unsupported scope disposition, and six pending. The next decisions
concern original C105 and synthetic C31 through C34 and C72. G1 remains
BLOCKED pending qualified authority and interface decisions. G2 remains
BLOCKED. Release readiness is NO. Publication of the release is HOLD.
