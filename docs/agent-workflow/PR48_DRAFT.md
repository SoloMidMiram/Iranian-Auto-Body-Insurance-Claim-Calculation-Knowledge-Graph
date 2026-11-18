# PR #48 agent-workflow addition — commit and description draft

Proposed commit: `chore(agents): add reusable context and regression helpers`

Repeated repository reconstruction and full-log reading cost context and can hide stale evidence. Add a versioned maintenance skill, tool recipes, review perspectives, compact context/map/roadmap, and read-only change/JUnit helpers. Helpers return bounded evidence summaries without changing runtime decisions, staging files, modifying tests or calling models.

Upload scope: AGENTS.md; .agents/skills/body-model-maintenance/; scripts/project_context.py; scripts/agent_workflow.py; tests/test_agent_workflow.py; docs/PROJECT_CONTEXT.md; docs/REPO_MAP.md; docs/ITERATION_ROADMAP.md; this description draft. No claim-calculation source, fixtures, Persian tutorial, pre-existing README/gitignore edits, browser captures or local audit dossiers are included.

Local workspace inspection found three distinct groups: prior BODY hardening runtime/tests and synthetic inputs; agent-context/tooling additions; pre-existing user inspection/tutorial/replay materials. Full path inventory is retained locally in docs/agent-workflow/local-change-inventory.json (not uploaded). Nothing from the other groups is implicitly authorized for this upload.

PR verified 2026-11-19: #48, head fix/body-runtime-blockers at cd7fb39a0b7859f2cec91b94770e240ab62e0b75. Local HEAD 2c2bc24a269384056ce7a6f275c77ca38bb38cf7 differs. Publish only additive agent files on the verified remote parent, preserving its runtime tree. Do not reset/rebase the dirty local checkout. Git CLI DNS failed; GitHub connector publication uses an expected-head lease, no force.

Validation: skill validator; context brief/find/check; JUnit parser tests (failed/error/skipped, missing tests, duplicate IDs); existing R2 regression XML summarized without executing or relabelling it as a fresh gate. Full financial validation is not rerun for this additive tooling slice. Historical R2 522-test/50-fixture results apply to the local R2 candidate only, not the remote PR head.

Engineering: tooling verified locally; remote integration CI not claimed. Domain/release: unchanged and blocked. This draft supplements PR #48's runtime narrative; it does not overwrite its body, imply independent review or authorize merge.
