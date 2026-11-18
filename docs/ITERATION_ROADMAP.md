# Iteration roadmap — latest first

This is the dated narrative log; [ROADMAP.md](ROADMAP.md) retains strategic delivery phases. Prepend each pre-merge iteration. Dates reflect the client Asia/Tehran calendar, not inferred deadlines. Evidence reports remain historical.

## 2026-11-19 — Publish reusable agent tooling for PR #48

Branch: `fix/body-runtime-blockers`
HEAD: local validation base `2c2bc24a269384056ce7a6f275c77ca38bb38cf7`; remote publication parent `cd7fb39a0b7859f2cec91b94770e240ab62e0b75`.
PR: [#48](https://github.com/SoloMidMiram/Iranian-Auto-Body-Insurance-Claim-Calculation-Knowledge-Graph/pull/48), metadata verified 2026-11-19. Publication commit is recorded by Git; this entry pins its input parent to avoid a self-referential hash.

Add canonical repository skill/recipes/review perspectives and function-style read-only inventory/JUnit summaries. Upload only agent tooling; local financial hardening and user materials remain separate. Full descriptions and scope are in [commit draft](agent-workflow/PR48_DRAFT.md).

Validation: context commands, skill validation and helper tests run locally. Historical financial gates are not reused as remote-head proof.

Next plan: inspect remote integration CI and reconcile the separate runtime candidate before any merge review. Keep source-bound U03/U11/U04 blockers visible.

Engineering: tooling locally verified. Domain: unchanged, unapproved. Release: BLOCKED.

## 2026-11-18 — Context and workflow reuse

Branch: `fix/body-runtime-blockers`
HEAD: `2c2bc24a269384056ce7a6f275c77ca38bb38cf7`
PR: not created for this context slice. Related historical PR references: #48, #58, #59, #60; current remote state not verified in this iteration.

Implemented a small context entrypoint, keyword repository map, reusable maintenance skill and local context helper. This reduces repeated prompt reconstruction: start with a bounded brief, retrieve exact symbols, then open only necessary evidence. No quantitative token-savings claim is made. Existing financial behavior and user materials are unchanged by this slice.

Validation: `python scripts/project_context.py brief`, `find PS_RESCUE_THRESHOLD --limit 3`, `check`, and skill-creator `quick_validate.py` all exited 0 on 2026-11-18. Previous R2 financial results below are not relabelled as fresh tests of this documentation/tooling change.

Next plan: before merge review, verify actual PR identity/head/checks through GitHub, reconcile with the proposed runtime stack, refresh this entry and retain the separate domain gate. No push/merge authorization is implied.

Engineering: context tooling verified locally. Domain: unchanged, pending. Release: BLOCKED.

## 2026-11-18 — BODY-HARDENING-R2 recovery

Branch: `fix/body-runtime-blockers`
HEAD: `2c2bc24a269384056ce7a6f275c77ca38bb38cf7`
PR: not created for the local R2 candidate; existing related PRs require fresh reconciliation.

Recovered all 58 failures by distinguishing immaterial rescue evidence from mandatory unresolved inputs, repairing Review bindings and explicitly migrating synthetic contracts. T21 keeps its incomplete input and now expects a blocked settlement. All nine examples traverse public Review; successful synthetic results do not authenticate policy terms.

Evidence: `docs/body-hardening/r2/REPORT.md` (local-only report), `docs/body-hardening/r2/validation.json` (local-only validation), `docs/body-hardening/r2/candidate-manifest.json` (local-only candidate manifest). Recorded results: 522 tests, 50/50 fixtures, 24/24 mutations; graph, generated documentation and CLI gates passed for that candidate.

Next plan: source-bound glass endorsement U03/U11 and special-component U04 resolution contracts. First define applicable source, policy/version and invalid-authority behavior; only then enable currently hypothetical payable paths. No target delivery date is asserted without domain input.

Engineering: PASS for recorded candidate. Domain: NOT APPROVED. Release: BLOCKED.
