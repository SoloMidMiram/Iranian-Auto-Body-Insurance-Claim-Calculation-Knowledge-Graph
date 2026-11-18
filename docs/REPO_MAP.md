# Repository map

Maintained 2026-11-18 using keyword/ripgrep references. Paths are stable routing hints; use `rg -n` to obtain current line numbers. This map is not a second rule registry.

| Responsibility | Canonical paths | Search keys | Verification |
|---|---|---|---|
| Raw input and aliases | src/iran_auto_claim/schema_input.py; schema/ | validated_case, InputSchemaError | tests/test_schema_input.py |
| Evidence binding and admission | src/iran_auto_claim/review.py; knowledge/parameter_slots.json; knowledge/review_procedure.json | authorize, PS_RESCUE_THRESHOLD, Q-S4-15 | tests/test_review.py; tests/test_admission.py |
| Immutable authorization | src/iran_auto_claim/admission.py | CalculationAuthorization, verify, ISSUER_REVIEW | tests/test_admission.py |
| Normalized case/classification | src/iran_auto_claim/case.py; src/iran_auto_claim/classify.py | rescue_for_threshold, classify | tests/test_engine.py; tests/test_hardening.py |
| Calculation and final branch guards | src/iran_auto_claim/engine.py; src/iran_auto_claim/guards.py | compute, reconcile_classification, TITLE_TRANSFER_SETTLEMENT_UNRESOLVED | tests/test_guard_paths.py; tests/test_guards.py |
| Arithmetic and graph plans | src/iran_auto_claim/operators.py; src/iran_auto_claim/plans.py; knowledge/branches.json; knowledge/operators.json | is_total_loss, execution_plan, OP_RESCUE_CAP | tests/test_operators.py; tests/test_plans.py; tests/test_properties.py |
| Authority and provenance | knowledge/rules.json; knowledge/sources.json; knowledge/guards.json; knowledge/uncertainties.json; src/iran_auto_claim/knowledge.py | U03_GLASS, U04_BATTERY, U11_GLASS, provenance | python claim.py validate; tests/test_provenance.py |
| Public tutorial replay | fixtures/body_tutorial_hardening.json; scripts/replay_body_tutorial.py | TUTORIAL-07, TUTORIAL-09, public_inputs | tests/test_tutorial_public.py |
| Internal arithmetic corpus | fixtures/cases.json; src/iran_auto_claim/fixtures.py | T21, INTERNAL_TEST_DIRECT | python claim.py fixtures; not public admission proof |
| CLI and quality gate | claim.py; src/iran_auto_claim/cli.py; .github/workflows/ci.yml; docs/VALIDATION_GATES.md | review, calc, fixtures | tests/test_cli.py; scripts/run_mutation_gate.py |
| Planning and issue register | planning/issues.json; docs/ROADMAP.md; docs/ITERATION_ROADMAP.md | release, body, latest date | scripts/sync_github_issues.py (inspect flags; no remote write without authorization) |
| Evidence dossiers | docs/body-hardening/r2/ | failure-inventory, validation, candidate-manifest | Read linked evidence for specific findings |

Dependency direction: schema -> Review/slots -> Case/classification -> admission -> engine -> graph plans/operators/guards -> trace. Knowledge selects rules/plans; Python executes them. Avoid a second engine or duplicated canonical inputs.

Generated artifacts: docs/BODY_CASE_REVIEW_MODEL.md via scripts/sync_review_docs.py; docs/CUSTOMER_FAQ.md via scripts/sync_customer_faq.py; docs/MUTATION_REPORT.md via scripts/run_mutation_gate.py. Update source and regenerate, never hand-edit generated blocks. The Persian tutorial is manual. R2 matrices are audit snapshots, not live authority registries.

Cheap retrieval examples:

```powershell
python scripts/project_context.py brief
python scripts/project_context.py find PS_RESCUE_THRESHOLD
rg -n -F -- U04_BATTERY_TIRE_CAP_VS_DEPRECIATION src knowledge tests
python scripts/project_context.py check
```

Routine full gate commands are maintained in docs/VALIDATION_GATES.md and CI. Reuse those definitions rather than copying their entire content into prompts.

Agent tooling: `.agents/skills/body-model-maintenance/SKILL.md` is canonical; `scripts/agent_workflow.py changes` inventories paths and `regress CURRENT.xml --baseline BASE.xml` summarizes recorded outcomes. Review roles and interpretation recipes live alongside the skill. R2 tutorial tools/reports may be local-only until their separate runtime slice is published.
