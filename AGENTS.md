# BODY project working rules

## Purpose and boundaries
Use English for communication and technical reports. Preserve Persian tutorial content unless its revision is requested. Scope is BODY: PARTIAL_DAMAGE, TOTAL_LOSS, GLASS_ONLY, THEFT; do not expand third-party recovery incidentally. Preserve unrelated working-tree changes. No push, merge, deployment or external messages without authorization.

Correctness and evidence outrank token savings. Missing evidence is not zero; test materiality for the final branch, including overrides. Classification rescue is independent of settlement rescue. Never invent transfer, valuation, policy terms or legal authority to green tests. Keep engineering, domain and release verdicts separate.

## Cheap context retrieval
1. Run `python scripts/project_context.py brief`. Read `docs/PROJECT_CONTEXT.md`, then the newest entry of `docs/ITERATION_ROADMAP.md`.
2. Route the task using `docs/REPO_MAP.md`. Search exact rule IDs, slot IDs, statuses or function names with `python scripts/project_context.py find KEYWORD` or `rg -n -F -- KEYWORD scoped/path`. Use grep equivalents if rg is unavailable. Read matching snippets before whole files.
3. Open detailed reports/tracebacks only for a concrete unresolved question. Do not preload all audit reports, JSON corpora, generated docs, logs, history or unrelated skills. Repository evidence outranks recalled status.
4. Reuse `scripts/replay_body_tutorial.py`, fixture runner, graph validator, mutation gate and existing public test builders. Do not repeatedly generate one-off scripts or introduce hidden evidence defaults in helpers.
5. Record evidence once, link it from summaries. Run focused checks during edits; run the full required gate before the final pre-merge handoff. Repeat passing checks only after relevant input changes or when freshness is unresolved. Never reuse historical results as current-head proof.

For calculation/review/context-maintenance work, read `.agents/skills/body-model-maintenance/SKILL.md` as the canonical skill; personal installations are optional copies. Keep planning proportional: goal, affected paths, regression, validation, blockers. Delegate only when explicitly authorized, not as a default token-saving measure.

## Every pre-merge iteration
Before requesting merge review, prepend a dated narrative entry to `docs/ITERATION_ROADMAP.md`, newest first (Asia/Tehran date). Include branch, exact HEAD, PR URL/number or `not created`, PR verification date or `not verified`, scope, why the changes matter, evidence links and command outcomes, unresolved domain decisions, next slice, and separate engineering/domain/release verdicts. Distinguish completed work from proposed plans. Multiple same-day entries are newest-first; do not rewrite historical outcomes.

Refresh `docs/PROJECT_CONTEXT.md` only when current goals/blockers change. Refresh `docs/REPO_MAP.md` when paths, responsibilities or commands change. Update the existing strategic `docs/ROADMAP.md` only for strategic scope/milestone changes; the iteration log does not replace `planning/issues.json`. Run `python scripts/project_context.py check` and review its limits: it checks context bookkeeping, not legal truth or merge permission. Never infer merge approval from green checks.

## Tools and routing
Prefer connected GitHub APIs for issue/PR metadata; retrieve only relevant IDs and fields. Save compact revision evidence. Live webpage/browser inspection must use playwright-global first, stop if unavailable, and list exact Playwright tools used. Local files and API metadata do not require a browser. Do not silently substitute HTTP commands for browser inspection.
