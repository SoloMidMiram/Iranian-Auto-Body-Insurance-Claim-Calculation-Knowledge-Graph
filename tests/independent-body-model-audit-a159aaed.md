# Independent frozen body-model audit

Original target: `SoloMidMiram/Iranian-Auto-Body-Insurance-Claim-Calculation-Knowledge-Graph`, revision `a159aaedaae8a0f8142f3c45675e8b11a9cd0fd8`. Original audit date: 9 October 2026. The detailed locations and frozen-export integrity statements below refer to that supplied export. Monetary examples use IRR.

Current-branch revalidation: revision `2c2bc24a269384056ce7a6f275c77ca38bb38cf7`, branch `fix/body-runtime-blockers`, also on 9 October 2026. This revision adds a current disposition, reprioritization, PR plan, gated roadmap, and research-decision register. It does not rewrite the evidence captured for the frozen export.

## Revalidation outcome and release decision

**Release assessment remains BLOCK. Graph/runtime parity remains PARTIAL.** All 16 frozen findings remain valid in substance on the current branch. IA-06 and IA-13 are now **partially remediated**, but neither is closed. No finding is considered closed merely because an adjacent test or guard was added.

Current validation evidence:

- The audit reproduction script completed and still reproduced the amount/eligibility counterexamples for IA-01 through IA-15. The most direct supported-path outputs remain: prior full compensation -> **1,657,000,000** payable; `ASSERTED_ONLY` causation -> **1,657,000,000** payable; repair-only work -> **120,000,000** depreciation; rescue-driven 76% damage -> `PARTIAL_DAMAGE`; physical insurer-title settlement with `title_transferred=false` -> **7,300,000,000** payable; and contradictory part aliases -> **1,657,000,000** payable.
- The separate 51-assertion invariant script passed **51/51**. This confirms the bounded positive invariants listed later, not the disputed legal choices.
- `python3 claim.py fixtures` passed **50/50** and `python3 scripts/run_mutation_gate.py --check-report` reported the mutation report current.
- `python3 claim.py validate` exited successfully but reported **22 body-authority findings** and **48 source-metadata findings**. Structural validity is therefore not authority completeness.
- The frozen-export audit recorded **507 tests passed at revision `a159aaed`**. The updated local branch at `2c2bc24` did **not** rerun that suite: the checked-in `.venv` has no pytest, the system Python has no pytest, and the host Windows Python shim is not executable under this WSL session. These are separate evidence records; the earlier count must not be presented as a current-branch result.
- The accessible Regulation 53 text corroborates the strict total-loss threshold including rescue, replacement-part-only depreciation, distinct theft classification/payment language, total-loss title mechanics, notice and subrogation consequences, and multiple-insurance allocation. An accessible official original with complete effective/amendment history was not established during this revalidation, so those legal readings still require primary-source and human-domain acceptance.

## Revised priority model

This register supersedes the old P0/P1/P2/P3 grouping used in the frozen finding detail.

| Priority | Meaning | Release treatment |
|---|---|---|
| P0 | A supported Review can issue a deterministic eligibility or money result from contradictory, missing, unsourced, or incorrectly transformed facts; no new legal interpretation is needed to fail closed | Must be fixed and covered by full-path regression before any body-model release candidate |
| P1 | A money/eligibility decision depends on a legal, contractual, or adjudicative choice, or a supported resolution cannot reach runtime correctly | Scope must remain blocked until a signed decision artifact exists and the selected rule is implemented/tested |
| P2 | Architecture, provenance, internal-boundary, or test-integrity debt weakens assurance without currently creating a demonstrated supported-Review payment by itself | Must close before an audit-ready release; may follow P0 containment if its boundary remains inaccessible |

## Current P0-P2 action register

| ID | Revised priority | Current state at `2c2bc24` | Current-branch evidence | Required release action |
|---|---|---|---|---|
| IA-01 | **P0** | OPEN | `prior_compensation=1,850,000,000` is emitted but ignored; payable remains `1,657,000,000` | Block any positive/contradictory prior-compensation state now; add allocation only after RQ-01 is answered |
| IA-02 | **P0** | OPEN | `ASSERTED_ONLY` still yields `COMPUTE`, payable `1,657,000,000`, confidence `0.95` | Require the positive causation predicate at Review and engine boundaries; map asserted/unknown to insufficient information |
| IA-03 | **P0** | OPEN | `REPAIR_ONLY` and `requires_replacement=false` still receive `120,000,000` depreciation | Make replacement status a validated predicate of depreciation; reject inconsistent category/status pairs |
| IA-04 | **P0** | OPEN | Repair `7,400` plus rescue `200` over market `10,000` still classifies partial and pays `6,860` | Bind the authority-selected threshold rescue operand; test both classification and settlement rescue operands separately |
| IA-05 | **P0** | OPEN | Physical total loss with `INSURER_TAKES_TITLE` and `title_transferred=false` still pays `7,300,000,000` | Require completed transfer for the no-salvage route and a sourced salvage value for retained salvage |
| IA-07 | **P0** (raised from P1) | OPEN | `1404-99-99` and production year `1500` are accepted; the latter raises payable to `1,765,000,000` | Canonical calendar validation, chronology, claim-year reconciliation, and effective-version refusal |
| IA-08 | **P0** (raised from P1) | OPEN | A non-zero `INSURER_MANUAL` franchise with no reference/version still yields `1,657,000,000` | Require insurer, product, instrument reference/version, effective interval, and accepted term for every monetary franchise |
| IA-15 | **P0** (raised from P2) | OPEN | Conflicting `assessed_loss` and `assessed_loss_irr` are admitted and one wins silently | Use one canonical field or equality-check every supplied alias before normalization |
| IA-06 | **P1** | PARTIAL | Clock fields now reach the engine and selected start date must equal its canonical event; occurrence-day 60/declaration-day 59 still pays | Preserve the fixes and model both clocks independently now; keep payment blocked until RQ-02 authorizes the substantive switch |
| IA-09 | **P1** | OPEN | `AFTER_SALVAGE` and `SETTLEMENT_BASE` are now distinct, but both remain admissible: example payables `1,530` vs `1,500` | Bind the allowed base/order to the applicable circular/policy version; refuse a conflicting configured base |
| IA-10 | **P1** | OPEN | Late notice and released recourse still add labels while paying `1,657,000,000` | Add explicit adjudication states and evidence; do not infer automatic denial or automatic permission |
| IA-13 | **P1** (raised from P2) | PARTIAL | Category-aware predicates and separate battery/tyre new-price handoff are fixed; a supplied `CAP_ONLY` resolution remains live and is reconciled to a generic authorization uncertainty | Add typed resolution-artifact plumbing now without activating an unresolved choice; applicable artifacts may then control liveness without erasing the primary error |
| IA-11 | **P2** | OPEN | Mutating graph annual depreciation from 5% to 20% still leaves payable/depreciation unchanged | Execute graph payloads or enforce a versioned code/graph implementation contract that rejects drift |
| IA-12 | **P2** | OPEN | Authorization is not bound to knowledge/source content; source hashes remain null and dependencies are incomplete | Hash and bind graph, sources, policy terms, evidence-to-operand derivations, and confidence semantics |
| IA-14 | **P2** | OPEN; EARLY CONTAINMENT REQUIRED | Internal total loss with absent/retained-but-unvalued salvage still pays `1,900` | Land missing-operand rejection before PR-06; complete internal-issuer isolation and glass parity in Stage 3 |
| IA-16 | **P2** (raised from P3) | OPEN | Duplicate top-level tests still shadow each other; `tests/BODY_CASE_REVIEW_MODEL.md` remains stale relative to `docs/` | Remove duplicates, add AST duplicate-name CI, and put every shipped generated copy under consistency checks |

## Implementation stages and exit gates

The roadmap separates immediate containment from final settlement logic. Engineering may represent uncertainty, derive facts independently, strengthen schemas, and prevent payment while a substantive interpretation is pending. It must not activate one unresolved interpretation merely because the supporting structure now exists.

| Stage | Work | Exit condition |
|---|---|---|
| 0 — Reproducible baseline | Commit the revised audit; record the exact code target, committed audit reference, audit Git blob ID in an external manifest/PR record, environment and commands; restore a usable pytest environment; detect duplicate tests | Clean-checkout results are reproducible, with skipped or unavailable checks explicitly recorded |
| 1 — Immediate containment | Block unsafe states implicated by IA-01/02/05/08; reject conflicting aliases and invalid chronology; add IA-14 missing-operand defenses; quarantine unresolved affected branches | Every adversarial input yields a specific nonpayable result through supported Review and, where applicable, the engine boundary |
| 2 — Deterministic corrections | Canonical inputs -> replacement-only depreciation -> correctly bound threshold operands -> disposition predicates -> contractual authority validation | Named regressions fail on each fix's parent revision and pass afterward |
| 3 — Engine and graph enforcement | Complete IA-14 boundary parity; strengthen internal operand validation, graph contracts, authorization binding and provenance | Review and internal execution enforce the same applicable invariants; same authorization/different graph is rejected |
| 4 — Authority-dependent activation | Implement approved decisions for allocation, theft clocks, franchise ordering, notice/subrogation and resolution artifacts | Every activated interpretation references its approved, applicable decision artifact; pending alternatives remain blocked or scenario-only |
| 5 — Release evidence | Re-audit all findings, run clean-checkout validation and produce the release dossier | No release-blocking finding remains; authority limitations exactly match the enabled scope |

Research and truth-table preparation run alongside Stages 0-3. Individual PRs are gated by their actual code and decision-artifact dependencies, not by completion of an entire phase. Graph/provenance groundwork may proceed before unrelated legal decisions; formula activation may not.

The existing 13 October `v0.1-body-model` target remains conditional. Calendar pressure is not grounds to waive an exit gate.

## Pull-request plan

Each PR must cite the committed audit finding and describe the final implementation and remaining limitations. It must not make a verbatim copy of the original `Smallest safe fix` its acceptance criterion: later authority research may legitimately refine that advice. Counterexamples belong in a separate runner or as narrowly scoped strict expected failures while the defect remains open; PR-00 must not merge an ordinarily failing default suite. For each fix, preserve evidence that its named regression failed on the parent revision, then remove/convert the expected failure so the fixed suite passes normally.

Recommended merge order is `PR-00 -> PR-01 -> PR-02/03/04/05 -> PR-05A -> PR-06`. PR-07 through PR-13 then advance according to the dependencies in their rows, not as one serial chain. PR-02 through PR-05 all touch some combination of `review.py`, `engine.py`, schemas and shared tests; prepare them in parallel only with explicit file ownership and planned rebases.

| PR | Finding(s) | Implementation slice | Principal files | Acceptance evidence | Depends on |
|---|---|---|---|---|---|
| PR-00 — Reproducible audit baseline | IA-16 | Commit this audit; record exact target/commit/audit-blob/environment/commands outside the self-hashed audit file; restore pytest; remove shadowed definitions; add AST duplicate-name and generated-copy checks; register counterexamples as strict expected failures or in a separate runner | Audit manifest/PR record, `tests/test_provenance.py`, test configuration, generated-doc checks, counterexample runner | Clean checkout reproduces every available gate; unavailable checks are explicit; the ordinary suite is green; strict expected failures are named by IA ID | None |
| PR-01 — Canonical dates and values | IA-07, IA-15 | Parse/validate Shamsi and Gregorian values once; enforce event/awareness/declaration/as-of and production chronology; reject unequal aliases | `schema_input.py`, `case.py`, schemas, Review input tests | Invalid dates, future production, conflicting year, unequal aliases refuse with stable paths; equal aliases normalize once | PR-00 |
| PR-02 — Eligibility admission gates | IA-01, IA-02 | Add explicit prior-compensation and positive-causation guards at Review and engine; initially block unimplemented contribution | `review.py`, `engine.py`, `guards.py`, knowledge guards/slots | Matrix for zero/partial/full prior compensation and established/asserted/unknown/contradicted causation across both issuers | PR-01 |
| PR-03 — Component and threshold operands | IA-03, IA-04 | Validate replacement predicate; separate repair/replacement/labour; bind threshold rescue independently from payable/capped rescue | `operators.py`, `review.py`, `case.py`, `classify.py` | Same part toggled repair/replacement changes only depreciation; 74.99/75/75.01% and rescue-crossing cases classify correctly | PR-01 |
| PR-04 — Total-loss disposition contract | IA-05 | Make disposition a closed state machine; require transfer completion or retained-salvage valuation | `review.py`, `engine.py`, `case.py`, schema/guards | Transfer false/in-progress/missing cannot pay under insurer-title; retained salvage missing cannot pay | PR-01 |
| PR-05 — Minimum franchise authority | IA-08 | Require reference, version, insurer, product/coverage applicability, effective interval, and accepted term for non-zero as well as zero franchise | `review.py`, `engine.py`, schema, policy snapshot provenance | Allowed enum alone fails; wrong insurer/product/date fails; applicable versioned term passes | PR-01 |
| PR-05A — Early engine containment | IA-14 | Add engine-level rejection for missing/ambiguous material salvage and other operands exercised by P0 paths; do not wait for complete issuer/provenance redesign | `case.py`, `engine.py`, focused direct-authorization tests | Every Review P0 adversary has an equivalent engine-boundary missing-input rejection where applicable | PR-04; coordinate with PR-05 |
| PR-06 — Immediate-safety gate | IA-01/02/03/04/05/07/08/14/15 | No new settlement interpretation; run clean supported-Review, direct-engine, fixture, property, mutation, parity and packaging gates | CI/release scripts and audit dossier | Stages 0-2 containment/correction criteria pass from clean checkout; independent reviewer signs results | PR-02 through PR-05A |
| PR-07 — Dual theft-clock structure | IA-06 | Preserve current clock-binding fixes; represent classification and payment clocks independently; derive, cross-check and trace both; keep authorization blocked until a substantive rule is approved | `review.py`, `engine.py`, event schema, rules/uncertainties | Both clocks are independently reproducible and impossible chronology fails; no unresolved choice authorizes payment | PR-00 for structure; RQ-02 decision artifact only for activation |
| PR-08 — Franchise/salvage/order authority | IA-09 | Map an applicable circular/policy term to one typed base/order; allow any demonstrably supported named base; block missing, conflicting or insufficient authority | `engine.py`, plans/rules/operators, adapter data | Applicable term selects and traces its base; unsupported selection is nonpayable; approved worked examples replay exactly | RQ-03/RQ-04/RQ-07 artifact for each activated scope; containment may land earlier |
| PR-09 — Notice and recourse adjudication | IA-10 | Add `PENDING/PROCEED/REFUSE/REDUCE` decision objects with actor, reason, evidence, time and authority; pending is immediately nonpayable; no guessed coefficient | Review procedure, schema, `review.py`, `engine.py` | State machine and pending containment pass without choosing a consequence; activated outcomes reproduce approved matrices | RQ-05/RQ-06 artifacts only for activated `PROCEED/REFUSE/REDUCE` outcomes |
| PR-10 — Resolution-artifact structure | IA-13 | Preserve category/new-price fixes; replace config-only resolution with a typed authority-artifact reference and correct uncertainty/error reconciliation; keep unsupported choices blocked | slots/uncertainties, schema, `review.py`, `engine.py` | Missing/wrong artifact stays blocked; primary errors survive; an applicable artifact closes only its uncertainty | PR-00 for structure; RQ-08/RQ-09 artifact for activating a particular interpretation |
| PR-11 — Complete engine-boundary parity | IA-14 | Finish glass-term completeness, issuer isolation, CLI separation and other internal/supported parity not covered by PR-05A | `admission.py`, `engine.py`, CLI, fixture adapter | No production path can mint/use `INTERNAL_TEST_DIRECT`; direct incomplete glass/settlement cases cannot pay | PR-05A; PR-05 where contractual terms are involved |
| PR-12 — Graph implementation contract | IA-11 | Choose interpreter or compiled/validated contract; bind numeric payload, exemptions, scopes, plans and guard sets without selecting unresolved legal values | `knowledge.py`, `plans.py`, `operators.py`, `engine.py` | Graph payload mutation changes behavior or causes a fail-closed consistency error | PR-00; coordinate shared engine edits, but no unrelated authority artifact required |
| PR-13 — Dependency provenance | IA-12 | Content-address knowledge, source bytes, policy terms, evidence-to-operand lineage and result dependencies; split early hash groundwork from final execution binding if useful | `admission.py`, `knowledge.py`, `engine.py`, source register | Same authorization/different content rejected; replay reconstructs every operand and confidence component | PR-00 for hash groundwork; PR-12 for final graph-execution binding |
| PR-14 — Release dossier | All | Update scope, customer docs, limitation register and frozen export; independently rerun every gate and finding | docs, exports, CI evidence | Stage 5 passes; release remains decision-support only unless separately certified | All enabled-scope PRs and their required decision artifacts |

### Acceptance contract for every fix PR

Every fix PR must record:

- the exact parent/target revision and committed audit reference;
- the named counterexample and its before/after output;
- a full supported Review-path regression where that path is applicable;
- engine-level missing-input rejection where the invariant also belongs at the calculation boundary;
- the rule and authority basis, including alternatives that remain unresolved;
- reproducible commands/results and explicit remaining limitations.

## Rule, calculation, and case-switch decision register

These are the questions to research or take to a lawyer, insurer product owner, senior adjuster, regulator, or actuarial reviewer. Until a question is answered with an applicable artifact, the listed safe runtime behavior is part of the model contract.

| RQ | Dilemma or contradiction | Exact question to answer | Evidence/data to gather | Safe behavior meanwhile |
|---|---|---|---|---|
| RQ-01 | Multiple insurance/prior recovery | After a partial prior payment, is this insurer's amount the unrecovered loss, its proportional share of the whole loss, the lesser of both, or another formula? Who pursues contribution? | Exact Article 21 Persian text and amendments; applicable policies and sums; prior settlement receipts; insurer contribution examples | Block positive prior compensation and inconsistent `NO` + positive amount; permit documented zero only |
| RQ-02 | Theft uses two legal functions but one switch | What event starts the Article 19 60-day total-loss classification period, and what event/document completion starts the Article 20 payment period? Are these calendar days? | Official Articles 19/20; policy wording; claim declaration timestamp; occurrence/awareness/police dates; complete-document timestamp; insurer worked files | Track all clocks; do not let caller selection make one substitute for another |
| RQ-03 | Total-loss franchise base | Does circular `1400/401/146850` require percentage franchise on `base - salvage`, and for which products/dates? Can policy wording lawfully override it? | Official signed circular and repeal history; applicable policy schedule/endorsement; insurer legal interpretation; worked example | Admit only the base supported by the applicable hierarchy; otherwise block |
| RQ-04 | Underinsurance/franchise/rescue order | In partial loss, is Article 10 applied before or after franchise? Is rescue inside the proportional reduction or added afterward? | Exact Article 10/Regulation 53 wording; policy clauses; official or insurer-approved numerical examples with underinsurance and rescue | Return scenario set when order changes the result; never choose by smaller/larger outcome |
| RQ-05 | Late notice consequence | Is late notice an optional refusal, mandatory refusal, reduction tied to prejudice, or excusable on unavoidable-cause proof? Who can waive it? | Article 10 Persian text; policy procedure; unavoidable-cause criteria; delegated authority matrix; adjudicated examples | Block final payment until an evidenced `PROCEED/REFUSE/REDUCE` decision exists |
| RQ-06 | Impaired subrogation | Does release/compromise permit full non-payment, recovery after payment, or only the proven value of impaired recourse? Who decides and how is prejudice valued? | Article 14 text; court/arbitration decisions; insurer recovery procedure; waiver/consent record; expected recovery valuation | Block deterministic settlement; do not invent a reduction coefficient |
| RQ-07 | Total-loss rescue and salvage semantics | Is the 75% numerator actual reasonable rescue, accepted rescue, or capped payable rescue? When exactly does title acquisition replace salvage deduction? Is `NOT_APPLICABLE` ever valid for physical total loss? | Article 19 text/interpretation; salvage valuation method; title-transfer checklist; circular; sample total-loss files | Keep threshold rescue and payable rescue separate; require one exclusive, evidenced salvage route |
| RQ-08 | Replacement depreciation | Does depreciation apply only to actually replaced parts? How are mixed repair/replace operations and production-year index counted? | Persian Article 19 partial-loss text; assessor invoices separating repair/replacement/labour; official age examples | Never depreciate repair-only/labour/glass; block inconsistent status/category records |
| RQ-09 | Battery/tyre 50% cap plus depreciation | Are old batteries/tyres both capped and depreciated? If yes, in which order; if not, which rule prevails? | Article 3/19 wording, insurer manual, assessment worksheet examples, approved product terms | Return named scenarios unless a sourced resolution artifact selects one |
| RQ-10 | Franchise schedules | Which rate/minimum applies by insurer, product, coverage, claim sequence, fault status and policy year? Can an insurer manual alter the contract? | Declarations, schedule, endorsements, claim history, insurer/product/version tables, effective dates and approval status | No global rate; no bare `INSURER_MANUAL` enum; block mismatched applicability |
| RQ-11 | Standalone glass terms | Does the endorsement include installation/labour, impose a limit or special franchise, and exempt or retain underinsurance? | Actual endorsement wording by insurer/product/version and worked paid claims | Keep standalone glass blocked until complete terms are installed |
| RQ-12 | Risk intensification ratio | Which premium is the numerator/denominator, what period applies, and how are zero/additional premiums handled? | Article 9; charged premium; appropriate-risk tariff; endorsement/change date; insurer calculation examples | Preserve U15 block; never reuse the Article 10 capital ratio |
| RQ-13 | Effective-date hierarchy | Which date selects regulation/circular/policy versions: event, policy inception, declaration, amendment endorsement, or another transition rule? | Promulgation/effective/repeal dates; policy inception/renewal/end endorsements; transitional clauses | Refuse historical scope with no resolvable version; do not label `BODY@open` as proof |
| RQ-14 | Evidence semantics | What proves causation, salvage value, market value, title transfer and authority decisions? Is document presence enough, or must a field be tied to a page/issuer/hash? | Evidence standard, document samples, issuer signatures, page locators, hashes, reviewer role/authority | Treat presence as an attestation only; `ASSERTED_ONLY` and unbound values cannot authorize money |
| RQ-15 | Money/rounding rules | At which step is IRR rounded, and are policy percentages/minima applied before or after rounding? How are negative/intermediate fractions handled? | Policy calculation instructions and paid worksheets with fractional percentage results | Keep Decimal and round once at the documented terminal step; reject unspecified intermediate rounding |
| RQ-16 | Graph versus code authority | Is the graph executable configuration, documentation, or a contract checked against code? Which artifact wins on divergence? | Architecture decision record, versioning/signing plan, change-control ownership | A divergence must fail closed; neither silently overrides the other |
| RQ-17 | Confidence meaning | Is `0.95` a rule-authority score, data completeness score, calibrated correctness probability, or only an internal ranking? May it ever authorize payment? | Metric definitions, calibration dataset, validation protocol and operating threshold owner | Keep classification/formula/evidence scores separate and non-authorizing |

### Case-switch truth tables that must be signed before implementation

1. **Causation:** `ESTABLISHED -> eligible to continue`; `ASSERTED_ONLY/UNKNOWN/missing -> insufficient information`; `CONTRADICTED -> refuse or conflict`, subject to a signed legal/product review of the last state.
2. **Physical total-loss disposition:** `INSURER_TAKES_TITLE` requires completed transfer and no salvage deduction; `INSURED_RETAINS` requires a sourced salvage value and deduction; `IN_PROGRESS/UNRESOLVED/missing` blocks; the valid meaning of `NOT_APPLICABLE` requires RQ-07.
3. **Prior compensation:** documented zero may continue; positive or internally contradictory facts block until RQ-01 is encoded; a missing amount never means zero.
4. **Component work:** repair-only is non-depreciable; replacement is age-tested; labour is separate; glass/lamp glass is exempt; inconsistent category/replacement flags are input errors.
5. **Franchise authority:** a source type is not an instrument. The switch may activate only after insurer/product/coverage/version/date applicability and the named base are established.
6. **Uncertainty resolution:** a choice string such as `CAP_ONLY` or `SETTLEMENT_BASE` is not self-authorizing. It must reference the artifact, reviewer/actor, effective scope and decision time that made the choice applicable.

## Frozen finding detail

The descriptions below retain the original frozen-export severity grouping for traceability. Use the revised current action register above for implementation order.

### Original P0 grouping

### IA-01 — Prior compensation never reduces or blocks the payable

- **Files/lines:** `model/knowledge/review_procedure.json:80,93`; `model/src/iran_auto_claim/review.py:503-504,620-638`; `model/schema/claim-case.schema.json:815-834`; `model/src/iran_auto_claim/engine.py:517-652,654-745`. The engine has no read of `policy.multiple_insurance` or `prior_compensation`.
- **Knowledge:** `REG53_ART21_MULTIPLE_INSURANCE_CONTRIBUTION`, `PS_MULTIPLE_POLICIES`, `Q-S6-05`, `Q-S9-03`.
- **Observed:** Change the supplied T1 review's Q-S6-05 to `YES_OTHER_POLICIES` and Q-S9-03 to `1850000000`, and confirm `EVT_OTHER_POLICIES` and `EVT_ARBITRATION_OR_COURT_AWARD`. Review remains `COMPUTE`, and payable remains **1,657,000,000**. Its gross assessed loss is 1,850,000,000 and is already fully compensated.
- **Expected invariant/importance:** A fully indemnified loss cannot support additional indemnity. Unimplemented contribution arithmetic must block affected files. Recording an input is not implementing Article 21.
- **Existing test:** `tests/test_review.py:152-172` checks emission of the zero-prior-compensation object and an unchanged payment. It never varies prior compensation. Fixture coverage of another recovery domain does not cover this body path.
- **Smallest safe fix:** Block authorization and engine settlement whenever prior compensation is positive or contribution facts are incomplete, until an authority-reviewed contribution/remainder operator is implemented. Do not guess allocation from total policy sums.
- **Regression:** Full compensation, partial compensation, multiple policies with no prior payment, and inconsistent `NO` plus positive prior compensation; assert both Review and internal engine outcomes and rule trace.

### IA-02 — Asserted-only causation is treated as sufficient

- **Files/lines:** `model/knowledge/review_procedure.json:36` (Q-S2-02); `model/src/iran_auto_claim/review.py:154-161,883-918`; `model/src/iran_auto_claim/engine.py:425-477`; `model/knowledge/guards.json:139-150`.
- **Knowledge:** `Q-S2-02`, `PS_CAUSATION_ESTABLISHED`, `G_NO_ASSUMED_CAUSATION`. The question explicitly says ASSERTED_ONLY must stop the pipeline.
- **Observed/counterexample:** In the T1 review change only Q-S2-02 from `ESTABLISHED` to `ASSERTED_ONLY`. Result remains `COMPUTE`, **1,657,000,000**, formula confidence **0.95**. No established-causation slot is bound. A present assessment document is accepted without establishing that it supports the asserted causal link.
- **Expected invariant/importance:** Answered is not equivalent to established. Unknown causation must not authorize a covered-payment result. The guard named in the question currently checks exclusion causation, not this positive coverage predicate.
- **Existing test:** `test_emission_preserves_sourced_dates_causation_mode_ratio_and_year` verifies the positive case; `test_causation_token_excludes_and_narrative_text_does_not` checks exclusion matching. Neither falsifies asserted-only eligibility.
- **Smallest safe fix:** Require an established causation predicate for affected body coverage, at Review and engine boundaries; emit a blocking reason for ASSERTED_ONLY. Keep contradiction/refusal distinct from insufficient information.
- **Regression:** ESTABLISHED/ASSERTED_ONLY/CONTRADICTED/UNKNOWN/missing, with evidence present and absent, through `Review.authorize()` followed by `compute()`.

### IA-03 — Repair-only work is depreciated

- **Files/lines:** `model/src/iran_auto_claim/operators.py:89-97,123-147`; `model/src/iran_auto_claim/case.py:384-405`; `model/src/iran_auto_claim/engine.py:529-542`; `model/schema/claim-case.schema.json:430-459`; `model/knowledge/review_procedure.json:61`.
- **Knowledge:** `REG53_ART19_REPLACEMENT_PART_DEPRECIATION`, `REG53_ART19B_PARTIAL_LOSS_BASE`, `OP_DEPRECIATION_REPLACEMENT_PART`, `Q-S4-03`.
- **Observed/counterexample:** Replace T1's component list with one `REPAIR_ONLY` component of 1,200,000,000, `requires_replacement: false`. Leave labour 400,000,000, rescue 100,000,000 and the sourced 10% AFTER_DEPRECIATION franchise. Production year 1399/event year 1404 yields **120,000,000 depreciation** and **1,432,000,000 payable**. With no replacement depreciation the same chain yields **1,540,000,000**. Merely setting `requires_replacement: false` on the original bumper also leaves its depreciation unchanged.
- **Expected invariant/importance:** Ageing applies to replacement parts, not repair work. The schema and normalization preserve replacement status, but the operator ignores it.
- **Existing test:** Age/category tests in `tests/test_operators.py:35-78` cover exemptions and rates but not repair-only status. No executable test varies `requires_replacement`.
- **Smallest safe fix:** Exclude REPAIR_ONLY and explicitly non-replacement work from ageing depreciation; reject inconsistent category/replacement combinations. Preserve any separately applicable battery/tyre damage cap according to reviewed authority, rather than blindly disabling all component rules.
- **Regression:** Same price, age and franchise, toggling replacement status; mixed repair/replacement/labour/glass; assert both intermediate depreciation and payable.

### IA-04 — Review omits rescue from total-loss classification

- **Files/lines:** `model/src/iran_auto_claim/review.py:571-579`; `model/src/iran_auto_claim/case.py:205-207`; `model/src/iran_auto_claim/classify.py:70-80`; `model/knowledge/rules.json:7-27`; `model/knowledge/review_procedure.json:65`.
- **Knowledge:** `REG53_ART19_TOTAL_LOSS_THRESHOLD`, `PS_RESCUE_ACTUAL`, `PS_REPAIR_TOTAL`, `Q-S4-07`.
- **Observed/counterexample:** From T1 set market=insured=10,000, production=1404, labour=0, one replacement component=7,400 and rescue=200. Review emits `rescue_transport_actual_irr` but never `rescue_for_total_loss_test_irr`. Case defaults the latter to zero. Review classifies **PARTIAL_DAMAGE** and pays **6,860**. The stated model numerator is 7,400+200=7,600, or **76%**, which selects total loss and requires that branch's settlement evidence.
- **Expected invariant/importance:** The same accepted rescue fact must reach the threshold numerator. Operator correctness on a supplied threshold operand does not establish the correctness of Review's operand construction.
- **Existing test:** `tests/test_operators.py:147-164` and M09 discriminate `>` versus `>=`; they do not test a rescue-driven crossing through Review.
- **Smallest safe fix:** Bind the applicable sourced rescue amount into the threshold input, with explicit treatment of admissibility/capping. Stop classification when the relevant rescue fact is unresolved.
- **Regression:** Repair=74.99%,75%,75.01%; repair below 75% plus rescue crossing it; rescue supplied only through Q-S4-07; rejected rescue evidence must not become a positive or zero threshold fact silently.

### IA-05 — Physical total loss can waive salvage without acquiring title

- **Files/lines:** `model/src/iran_auto_claim/engine.py:674-697`; `model/src/iran_auto_claim/review.py:561-564,883-918`; `model/knowledge/review_procedure.json:64,67`; `model/knowledge/guards.json:18-29`.
- **Knowledge:** `REG53_ART19_INSURER_TAKES_TITLE`, `G_SALVAGE_XOR_TITLE_TRANSFER`, `PS_TITLE_TRANSFERRED`, `PS_SALVAGE_DISPOSITION`.
- **Observed/counterexample:** In T1 set the bumper assessment to 6,500,000,000 so total-loss classification is unambiguous; provide salvage 1,000,000,000, `INSURER_TAKES_TITLE`, Q-S4-06=`NOT_TRANSFERRED`, and both salvage/title evidence IDs. Change the percentage franchise base in Q-S6-02/03 to SETTLEMENT_BASE so it is valid for total loss. Review remains `COMPUTE`; engine emits **7,300,000,000**, deducts no salvage, and labels the XOR guard executed despite `title_transferred: false`.
- **Expected invariant/importance:** A declaration of intended disposition cannot substitute for completed transfer. This creates the exact overpayment case the XOR design is intended to prevent.
- **Existing test:** Total-loss tests and `test_total_loss_guards_fire_and_also_run_when_they_do_not_breach` vary disposition/salvage but not contradictory transfer status. Whole-theft transfer tests correctly cover a separate branch.
- **Smallest safe fix:** In shared total-loss settlement require established transfer before the insurer-title/no-salvage route. At Review block NOT_TRANSFERRED, IN_PROGRESS and inappropriate NOT_APPLICABLE answers for that route.
- **Regression:** True/false/missing/in-progress transfer for insurer-title physical total loss and whole theft; check no payable and no false completed-transfer label.

### Original P1 grouping

### IA-06 — The single theft clock conflates different legal functions

- **Files/lines:** `model/src/iran_auto_claim/review.py:447-480`; `model/src/iran_auto_claim/engine.py:989-1021,1030-1078`; `model/knowledge/uncertainties.json:253-273`; `model/knowledge/rules.json:31-52`; `model/knowledge/review_procedure.json:43-47`.
- **Knowledge:** `U13_THEFT_CLOCK_ANCHOR`, `REG53_ART19_THEFT_TOTAL_LOSS_60D`, five PS_THEFT_CLOCK slots; no separately enforced payment clock.
- **Observed/counterexample:** Use the supplied T2 review with occurrence 1404-04-20, declaration 1404-04-21, selected THEFT_OCCURRENCE, as-of 1404-06-18, SHAMSI, days=60, title transferred and the required evidence. The complete Review path pays **7,200,000,000** when occurrence elapsed=60 and declaration elapsed=59. Selecting AWARENESS or DECLARATION with matching dates is also sufficient to resolve U13.
- **Expected invariant/importance:** Regulation 53 distinguishes the Article 19 theft classification period from the Article 20 declaration-based payment period. A source string and matching date establish a factual binding, not authority to replace these distinct functions with whichever event a caller selects. The graph itself acknowledges separate clocks but the runtime enforces only one. Exact release/payment timing must receive legal acceptance review.
- **Existing test:** `tests/test_review.py:312-347` explicitly expects the 60-occurrence/59-declaration example to pay; it embeds the defect's assumption. M24 only proves that the selected date matches its named event.
- **Smallest safe fix:** Maintain separate occurrence and payment-eligibility clocks, including the applicable evidence/document-completeness rules. Require controlling authority for any departure; do not resolve legal applicability by a free-form source label.
- **Regression:** occurrence60/declaration59; occurrence61/declaration60; awareness later than occurrence; nonexistent or chronologically impossible selected event; policy/circular override supported by an applicable versioned instrument.

### IA-07 — Date/year validation and snapshot selection admit contradictory timelines

- **Files/lines:** `model/src/iran_auto_claim/schema_input.py:363-371`; `model/src/iran_auto_claim/review.py:327-333`; `model/src/iran_auto_claim/knowledge.py:288-293,417-451`; `model/src/iran_auto_claim/operators.py:91-97`; `model/src/iran_auto_claim/engine.py:1448-1460`; `model/schema/claim-case.schema.json:180-188,1279-1350`.
- **Knowledge:** `REG53_ART19_YEAR_INDEX_INTERPRETATION`, `PS_EVENT_DATE`, `PS_CLAIM_YEAR`, `PS_PRODUCTION_YEAR`, regulatory snapshot.
- **Observed/counterexamples:** T1 with Q-S0-02=`1404-99-99` still computes 1,657,000,000. T1 with Q-S5-03=1500 still computes and increases payment to **1,765,000,000** because a future production year produces a negative year index and zero depreciation. Review emits hyphenated dates, but `_jalali_date` accepts only slash dates; snapshot selection falls back to the Iranian year's 12/29. A Gregorian event date without a supplied Iranian year can select `BODY@open`.
- **Expected invariant/importance:** Impossible dates and a vehicle produced after the event cannot become valid monetary facts. A snapshot's anchor must match the actual event. Selected rule IDs must restrict executable rules; the current handlers can cite/apply a rule outside the date-selected subset. No complete policy-effective-date selector exists.
- **Existing test:** Missing-year tests are discriminating for absence, not future years. Theft-calendar tests validate theft clock dates, not all event/review dates. Snapshot tests use slash dates or only verify that a label exists.
- **Smallest safe fix:** Normalize explicit calendars once, validate every date, enforce chronology, derive/check claim year, and refuse unavailable effective versions. Make runtime use the selected rule/version set. Until full dating is implemented, restrict/reject affected historical scopes explicitly.
- **Regression:** invalid months/days; leap/common Esfand; future production year; conflicting event/claim year; equivalent date spellings; pre-circular and post-circular dates; unsupported Gregorian-to-Shamsi snapshot mapping.

### IA-08 — Contractual authority is accepted from an enum label

- **Files/lines:** `model/src/iran_auto_claim/review.py:416-445,1034-1055`; `model/src/iran_auto_claim/engine.py:268-275,293-344,355-380`; `model/src/iran_auto_claim/guards.py:21,81-97`; `model/schema/claim-case.schema.json:835-931`; `model/knowledge/rules.json:340-368`.
- **Knowledge:** `REG53_POLICY_DEFINED_FRANCHISE`, `U02_FRANCHISE_BASE_SCHEDULES`, `G_NO_HARDCODED_FRANCHISE_RATE`.
- **Observed/counterexample:** In T1 replace franchise sources in Q-S6-02/04 with INSURER_MANUAL and remove `source_reference`/`source_version`; the supported path still pays 1,657,000,000 at confidence 0.95. Even the original authorization's policy snapshot has `insurer: null`, `policy_version: null`: Q-S0-01's insurer/product text is not normalized into those fields. Only a zero computed franchise demands a reference/version.
- **Expected invariant/importance:** A rate must belong to the applicable contractual schedule. An insurer procedure is not universal law and cannot establish the insured's contractual share merely by its label. Sequence/coverage-specific strings are stored metadata, not an implemented rate-selection schedule.
- **Existing test:** Tests distinguish a missing/wrong source enum and explicit zero authority, but do not test an allowed source enum with no applicable instrument. `test_percentage_franchise_uses_the_named_base` tests arithmetic, not policy matching.
- **Smallest safe fix:** Require instrument reference, version, insurer/product applicability and an auditable accepted term for every monetary mode. Permit an insurer-manual derivation only when linked to the controlling contract/authority. Block unimplemented claim-sequence/coverage schedules rather than treating their descriptions as execution.
- **Regression:** allowed enum/no reference; wrong product/version; manual conflicting with policy; zero/nonzero authority equivalence; first/second/subsequent-claim schedules with distinct expected amounts.

### IA-09 — Operator order does not enforce the circular's franchise calculation base

- **Files/lines:** `model/src/iran_auto_claim/engine.py:303-317,709-719`; `model/knowledge/rules.json:440-458`; `model/tests/test_engine.py:603-645`.
- **Knowledge:** `CIC_CIRC_1400_401_146850_SALVAGE_BEFORE_FRANCHISE`, `OP_SALVAGE_DEDUCTION`, `OP_FRANCHISE`.
- **Observed/counterexample:** Market=insured=2000, retained salvage=300, sourced 10% franchise. AFTER_SALVAGE produces franchise 170/payable **1530**. SETTLEMENT_BASE produces franchise 200/payable **1500**. Both are admitted, even though the circular trace says salvage precedes calculation and application of the franchise.
- **Expected invariant/importance:** The two named operands should remain distinct as arithmetic concepts. However, contractual base selection must be checked against applicable higher authority. Execution order alone does not prevent deducting franchise on the salvage value. Any legally permissible departure needs explicit adjudication rather than silent acceptance.
- **Existing test:** `test_total_loss_percentage_franchise_distinguishes_settlement_base_from_after_salvage` correctly distinguishes the amounts but expects both to settle; it does not assess authority compatibility.
- **Smallest safe fix:** Reject or authority-block a pre-salvage percentage base for retained salvage under the applicable circular, preserving the typed base model for scopes where lawful. Do not globally alias SETTLEMENT_BASE to AFTER_SALVAGE.
- **Regression:** Same operands with both named bases before/after the circular, retained/transferred salvage, and an explicit reviewed legal exception if one is supported.

### IA-10 — Notice and recourse problems are labels, not authorization decisions

- **Files/lines:** `model/src/iran_auto_claim/engine.py:468-476`; `model/src/iran_auto_claim/review.py:602-605,883-918,966-990`; `model/knowledge/review_procedure.json:26,91`; `model/knowledge/rules.json:274-311,371-395`.
- **Knowledge:** `REG53_NOTICE_AND_DUTIES`, `REG53_ART14_SUBROGATION`, `PS_NOTICE_TIMELINESS`, `PS_SUBROGATION_IMPAIRED`.
- **Observed/counterexamples:** T1 Q-S0-04=`LATE` still pays 1,657,000,000. T1 Q-S9-01=`RELEASED_PARTY`, with requested judicial/arbitration evidence present, also still pays that amount. Engine only appends LATE_NOTICE_REVIEW/SUBROGATION_IMPAIRMENT_REVIEW labels and a rule trace.
- **Expected invariant/importance:** These facts are not necessarily automatic statutory denials: an excuse, waiver or discretionary insurer decision may matter. But unresolved exercise of that authority must not silently coexist with a final deterministic payment. Documentary presence does not record an adjudication.
- **Existing test:** Review/recovery tests check flags and a separate LEGAL_RECOVERY route. They do not establish an explicit body-claim adjudication allowing payment after these triggers.
- **Smallest safe fix:** Require an explicit, evidenced insurer decision/exception for affected files, or return a blocked review state. Do not invent a reduction coefficient or automatically deny all late files.
- **Regression:** late/no excuse, unavoidable cause, accepted waiver; impaired/unimpaired recourse; explicit authorized proceed/refuse decisions and their provenance.

### Original P2 grouping

### IA-11 — Full graph/runtime parity is not established

- **Files/lines:** `model/src/iran_auto_claim/plans.py:78-130,148-171,203-227`; `model/src/iran_auto_claim/operators.py:19-25,89-97`; `model/src/iran_auto_claim/engine.py:145-190,529-544,674-697`; `model/knowledge/rules.json:145-159`; `model/knowledge/operators.json:5-21`.
- **Knowledge:** Body operator/guard nodes, `REG53_ART19_REPLACEMENT_PART_DEPRECIATION` and the cap/threshold rules.
- **Observed/counterexample:** In a detached in-memory Knowledge copy, change the depreciation rule's `annual_rate` to 0.20 and compute the original authorization against that copy. Payable remains 1,657,000,000 and depreciation remains 120,000,000: Python's 0.05 constant wins. No archive/model file is changed by this experiment. The special-cap/depreciation graph steps are identity functions because both are pre-applied in Python. Allowed plan patterns are independently hard-coded. Several guards are marked executed by handler branches rather than independent invariant checks.
- **Expected invariant/importance:** Rule changes must either change execution or be rejected as unsupported/inconsistent. A valid sequence identity does not prove rule-payload semantics or complete guard enforcement.
- **Existing test:** `tests/test_plans.py:22-73` compares graph walking with legacy formulas built from the same operands; both share the assumptions. Mutation checks target selected operators, not graph numeric payloads or replacement predicates.
- **Smallest safe fix:** Either execute typed numeric rule payloads or validate them exhaustively against a versioned implementation contract. Make the advertised scope bounded and explicit. Use discriminating invariant guards for title/causation rather than labels alone.
- **Regression:** Mutate graph annual rate, maximum, special cap, threshold, exempt scope, implementation binding, operator order and required guard set; assert changed behavior or a fail-closed consistency error.

### IA-12 — Result provenance is not a complete dependency audit

- **Files/lines:** `model/src/iran_auto_claim/admission.py:100-113,162-207,236-264`; `model/src/iran_auto_claim/review.py:1026-1059`; `model/src/iran_auto_claim/engine.py:1327-1406,1462-1493`; `model/src/iran_auto_claim/knowledge.py:654-682`; `model/knowledge/sources.json:7-84`.
- **Knowledge:** Source/rule provenance envelopes, authorization, execution-plan identity, U nodes.
- **Observed/counterexamples:** The claim snapshot and provenance are immutable, but authorization contains a snapshot label rather than the content hash of the selected graph/source/policy versions. `compute(authorization, different_kb)` is accepted without checking that it is the graph approved at issuance. Source content hashes are null in the register. Evidence is a set of caller-attested document IDs/booleans, with no document-content-to-parameter binding. `_finalize` builds provenance from noted rules; it does not enumerate every operand and its evidence lineage. IA-01's ignored prior compensation therefore never reaches an effective output dependency.
- **Confidence observation:** The baseline classifier confidence is 0.85, formula confidence 0.95, evidence confidence 1.0. Those are different metrics; 0.95 is not an independently calibrated probability that the final settlement is correct. Rule-only confidence does not account for the unversioned manual, chronology or policy-applicability defects.
- **Expected invariant/importance:** Replaying an accepted result requires immutable versions of every amount-affecting dependency and clarity about what each confidence metric measures. Presence attestations must not be described as verified document authenticity.
- **Existing test:** `tests/test_provenance.py:28-48` checks nonempty source/rule/plan/result fields; admission tests check payload/provenance immutability and evidence caps. Neither tests graph retargeting or source-byte lineage.
- **Smallest safe fix:** Bind graph content/version, normalized policy identity, cited evidence/content references and operand derivations into authorization/result. Verify those bindings before execution. Keep formula/evidence/classification confidence separate and document their uncalibrated semantics; derive any settlement confidence from the complete dependency set.
- **Regression:** Same authorization/different graph; missing or changed source/policy version; absent assessor dependency; scenario-specific provenance; policy identity survives normalization; confidence degradation with a weak dependency.

### IA-13 — Component predicates and resolution handoffs strand supported inputs

- **Files/lines:** `model/src/iran_auto_claim/review.py:188-210,370-413,416-445`; `model/knowledge/review_procedure.json:62-63,85-86`; `model/src/iran_auto_claim/engine.py:1409-1433`.
- **Knowledge:** Q-S4-04/05, Q-S8-01/02, U01/U04, PS_PART_CATEGORY, PS_PART_NEW_PRICE, PS_ASSESSED_DEPRECIATION.
- **Observed/counterexample:** Q-S4-03 now supplies typed component objects, but `answer_is` compares their whole string representations with BATTERY/TIRE/etc. Consequently Q-S4-04/05 gates do not match. A battery record without inline new price plus Q-S4-04=200 does not reliably bind the price. A supplied CAP_ONLY or resolved Article10 order is not considered in U04/U01 liveness; engine calculation can then be cleared by authorization uncertainty reconciliation. Q-S4-05 is a choice-valued question attempting to supply a money slot, with no numeric assessed-depreciation question completing that advertised path.
- **Expected invariant/importance:** Typed records must be queried by category. Resolution requires a bound authority artifact; once actually resolved, a slot should not remain unconditionally live. Error reconciliation must not erase a more specific INPUT_ERROR into a generic uncertainty status.
- **Existing test:** Emission tests supply convenient inline fields; underinsurance tests generally expect scenarios. They do not establish category-driven next questions or an authority-complete resolved-configuration handoff.
- **Smallest safe fix:** Use category-aware slot predicates, add a numeric assessed-depreciation binding if that scope is supported, and make resolution-artifact validation drive uncertainty liveness. Preserve primary error reasons during reconciliation. Do not simply suppress U01/U04 on an unsupported adjuster choice.
- **Regression:** Typed old battery/tyre with/without inline new price; repair-only and glass records; assessed depreciation route; configured order with valid/missing authority; assert next questions, emitted operands and final status.

### IA-14 — Internal authorization is not an independent eligibility validator

- **Files/lines:** `model/src/iran_auto_claim/case.py:205-227`; `model/src/iran_auto_claim/engine.py:690-695,803-845`; `model/src/iran_auto_claim/admission.py:286-320`; `model/src/iran_auto_claim/fixtures.py:50-67`.
- **Knowledge:** U12, U03/U11/U14, salvage and glass rules.
- **Observed/counterexamples:** Internal authorized TOTAL_LOSS with market=insured=2000, repair=1600 and sourced absolute franchise=100, but no salvage value/disposition, pays **1900**. Explicit INSURED_RETAINS with no salvage value also pays 1900. A fully insured direct GLASS_ONLY claim can settle from an endorsement token plus franchise, without independently validating installation/valuation/limit terms. Normal Review correctly blocks standalone-glass scope through its live uncertainties.
- **Expected invariant/importance:** Missing salvage is not proof that salvage is inapplicable or worth zero. Internal testing bypasses Review evidence eligibility by design; it must remain strictly separated from supported production routes. Engine-level defenses should reject unsupported monetary facts where the model promises independent internal rejection.
- **Existing test:** `admission_shim` and fixture runner intentionally use INTERNAL_TEST_DIRECT. Evidence tests explicitly expect a payable with evidence confidence None. These tests establish arithmetic, not admissibility.
- **Smallest safe fix:** Refuse missing retained-salvage operands in the engine; assert glass term completeness or return the same supported-scope block. Keep internal issuer conspicuous, prevent production fallback, and avoid presenting those fixture settlements as acceptance examples.
- **Regression:** Missing/explicit-zero salvage, no disposition, retained/title dispositions; token-only glass endorsement versus complete terms; production CLI must never accept the internal factory's path implicitly.

### IA-15 — Contradictory aliases are admitted

- **Files/lines:** `model/src/iran_auto_claim/schema_input.py:404-454`; `model/src/iran_auto_claim/review.py:491-497`; `model/src/iran_auto_claim/case.py:134-140,387-393`; `model/schema/claim-case.schema.json:448-456`.
- **Knowledge:** PS_PART_CATEGORY and amount-bearing Case fields.
- **Observed/counterexample:** T1 bumper record can contain `assessed_loss: 1200000000` and `assessed_loss_irr: 1` simultaneously. Review computes 1,657,000,000, silently choosing the first. Claim normalization similarly uses source/alias precedence without equality checks.
- **Expected invariant/importance:** Ambiguous monetary evidence must not become a deterministic amount by dictionary precedence. A caller can choose which conflicting alias improves a result.
- **Existing test:** Schema tests reject unknown fields, wrong types and missing values; they do not reject inconsistent synonymous values.
- **Smallest safe fix:** Accept one canonical field or require all supplied synonyms to agree before normalization. Apply the same check across competing damage/vehicle/policy representations where synonyms are supported.
- **Regression:** Both alias orders; equal/unequal aliases; zero versus positive; conflicting market/insured anchors; assert structured rejection paths.

### Original P3 grouping

### IA-16 — Duplicate tests and a stale reference survive the green gates

- **Files/lines:** `model/tests/test_provenance.py:51-87,90-125`; `model/tests/BODY_CASE_REVIEW_MODEL.md:287,367`; `model/docs/BODY_CASE_REVIEW_MODEL.md:287,367`; `model/knowledge/review_procedure.json:56`; `model/knowledge/parameter_slots.json:357-376`.
- **Knowledge:** Q-S3-07, PS_RESCUE_CAP_BASE.
- **Observed/counterexample:** `_required_evidence` and `test_evidence_confidence_counts_boolean_values_not_key_presence` are each defined twice. Python overwrites the earlier definitions before pytest collection. The tests-folder reference says Q-S3-07 is `review` and rescue-cap missing behavior is DEFAULT_ONE; current graph/docs say `hard` and BLOCK_IF_MATERIAL.
- **Expected invariant/importance:** Green collection should not conceal overwritten tests or contradictory generated acceptance references.
- **Existing test:** The 507 collection count is real, but it excludes shadowed definitions. Generated-doc checks do not reject the stale tests-folder copy.
- **Smallest safe fix:** Remove duplicate definitions; eliminate the duplicate reference or include it in generation checks. Add a duplicate-top-level-test-name check.
- **Regression:** Static AST duplicate-name scan and generation consistency for every shipped procedural reference.

## Confirmed invariants

Independently read the implementation and ran **51 additional assertions**. These establish bounded technical behavior; they do not validate the full legal/policy applicability of every branch.

- Raw payloads, bare Case/domain authorizations and unissued CalculationAuthorization objects cannot call compute. `dataclasses.replace` does not copy the private grant. Detached claim/provenance views cannot change the issued snapshot. INTERNAL_TEST_DIRECT is distinguishable and cannot masquerade as REVIEW_GATE by changing metadata.
- REFUSE and INSUFFICIENT_INFORMATION do not issue through Review. Existing missing-document/missing-production-year gates work on the exercised supported path. Evidence-confidence caps are carried into direct `compute(review.authorize())`.
- Replacement age schedule is 0% in production-year indices 1–4, 5% at index5, +5 points/year, capped at 25%; GLASS/LAMP_GLASS return zero. Itemized labour is excluded from this component depreciation. IA-03 limits the replacement-only claim.
- The one-pass battery modes produce 75/90/100 for assessed=120,new=200,age rate=25%; effective depreciation is not deducted twice. An unresolved interaction blocks.
- Percentage franchise requires a typed supported base; missing/unsupported bases and missing terms do not produce a single amount. Minimum franchise works. No universal percentage is substituted. Explicit zero requires reference/version. SETTLEMENT_BASE and AFTER_SALVAGE are distinct; IA-08/09 limit authority acceptance.
- Underinsurance ratio requires both market/insured values and uses multiplication capped at1. The two partial scenarios differ as expected: for after-depreciation=1000,franchise=100,ratio=.5,rescue=20, amounts are 420 and470. Total-loss settlement uses min(market,insured), does not multiply that base by the ratio again, and caps payment at insured sum.
- Strict threshold primitive: 7499/10000 and7500/10000 are not total;7501/10000 is total. Ordinary monetary arithmetic uses Decimal rather than binary-float threshold arithmetic. IA-04 limits the complete Review path.
- Glass from a base body peril routes into partial damage. Standalone-glass missing endorsement does not create universal cover; sourced standalone-glass applicability remains blocked through Review. Glass has no scheduled ageing depreciation.
- Whole theft supported Review reaches the engine with all five clock fields. Occurrence/awareness/declaration bind to their matching canonical fields. Missing/mismatched canonical dates leave U13 live in Review. Independent internal missing selected date surfaces U13; an internal mismatched date returns INPUT_ERROR/no payable (not a U13 status). Stored elapsed days cannot override derived dates.
- Whole theft Review at59 days remains pending;60/61 days reach the modeled settlement, subject to IA-06. Theft title transfer is required before its settlement. Attempted vehicle-theft damage routes to partial damage; partial-parts theft remains terms-blocked.
- Shamsi leap/common Esfand30 validation, cross-year intervals and reverse-date rejection work in the bounded algorithm. The tested Gregorian/Shamsi cross-year interval gives equal elapsed days. This proves those represented intervals, not arbitrary cross-calendar conversion or a full astronomical calendar certification.
- Active plans reject missing/duplicate/unknown operators and unsupported orders. Required guard execution accounting can suppress output when a guard is omitted. Bound Review uncertainties cannot disappear into one payable, although IA-13 shows incomplete resolution handoff.

## Unsupported or authority-blocked claims

- Insurer/product/version schedules, claim-sequence selection and coverage-specific deductions are not implemented by storing their names. No observed implementation establishes that an insurer manual can universally set contractual rates.
- Standalone-glass endorsement installation inclusion, limits, valuation conditions and underinsurance exemption are not generally established. Review's blocking behavior here is appropriate.
- Partial theft endorsement limits/franchise, unresolved old battery/tyre interaction, unresolved Article10 order and risk-intensification premium ratios cannot support one universal payable. Risk-intensification correctly blocks rather than substituting the capital ratio.
- Regulation/policy effective-version selection is incomplete. `BODY@...` is an identity label, not proof that all executed rules were legally operative on that date.
- The technical total-loss no-double-ratio behavior is established. Its legal generality is an explicitly tagged implementation inference in the graph and needs authority acceptance; no green suite upgrades it to primary text.
- Evidence IDs/booleans attest presence, not authenticity or support for each fact. Reviewer text is carried as provenance, not authenticated identity/role authorization. Arbitrary hostile Python code in the same interpreter is outside the private-capability threat model; no such introspection exploit is asserted as a new finding.

## Authority layer and Regulation 53 source quality

External sources were checked independently, rather than treating the repository's source register as verification:

1. [Central Insurance motor-insurance compilation](https://centinsur.ir/_douranportal/documents/2277/carinsurance.pdf), viewed 9 October2026. The Regulation53 section corroborates the replacement-only depreciation schedule, strict threshold including rescue, valuation/transfer rules and distinct theft classification/payment provisions. Its later circular section supports calculating retained-salvage franchise after salvage. Its multiple-insurance clause forbids a second indemnity after full compensation.
2. [Central Insurance Regulation53 page](https://www.centinsur.ir/fa-IR/Portal/4927/news/view/15724/1802), located by search. Direct opening returned403, so the page is not claimed as fully read. [Insurance Research Center index](https://www.irc.ac.ir/fa-IR/Irc/5191) independently links Regulation53 to the older regulator URL; that direct opening failed too.
3. Iran Insurance's general-conditions page timed out. This audit does not falsely claim a complete official-insurer cross-check. An agent-hosted Saman document was not promoted to regulator authority.

The accessible regulator compilation improves clause corroboration; it does not repair the frozen export's missing source hashes/reviewers, certify absence of subsequent amendments, or populate applicable policy terms. The register accurately labels its principal mirror PRIMARY_MIRROR, but rule confidence near0.99 is not provenance completeness. Statute, regulation, circular, policy, insurer procedure and model inference must remain separately typed. The graph partly does this; IA-06/08/09/12 show where execution or confidence does not preserve the distinction.

## Export verification

**No missing or hash-mismatched target artifact was found.**

| Check | Independent result |
|---|---|
| ZIP SHA-256 | `df84ce780f6fbf9d841298a71a308ad639d7d83b8a1baf2df98ac6feb1c9a9c7`, exact match |
| MANIFEST | Frozen SHA/base/tree and scoped directories inspected |
| FILE_HASHES.sha256 | All125 listed files pass;126 archive entries, hash manifest self-excluded |
| Git revision | GitHub Git-commit endpoint confirms a159aaed and tree `0512a3e4c96ebd30f1ac271a3a3c883042d3ac5d` |
| Model-to-Git binding | All90 exported model files match their Git blob hashes at that exact tree |
| COMMITS.md | Seven commit SHAs/subjects match frozen base-to-head comparison |
| MAIN_TO_HEAD.diff |34 changed filenames and all addition/deletion lines match remote comparison; two files differ only in context/hunk grouping between endpoints |
| Executable artifacts | claim.py, src, three schemas, knowledge, ontology, fixtures, tests and scripts all present |
| Post-audit integrity | All125 hashes remain unchanged |

The export deliberately omits Git metadata and several non-model operational/user-owned files. Those disclosed omissions are not executable-validation blockers. The remotely reported comparison is diverged in Git ancestry, while listing the stated seven branch-side commits; that does not alter the frozen tree binding or the audited scope. No inference about current main/merge readiness was used as model authority.

## Executable path and rule-to-test map

Actual path: `schema_input.validate_review → Review.bind/derive → Review.classification/decision/evidence → Review.authorize → immutable admission snapshot → compute/validated_case → classification reconciliation → snapshot resolution → coverage/risk gates → branch handler → graph settlement sequence → uncertainty/guard enforcement → finalization/provenance/confidence`.

Critical qualification: component cap/depreciation, rescue/franchise operands, threshold classification and several eligibility predicates execute in Python before the graph settlement walk. A graph trace therefore cannot by itself establish those operations were correct.

| Rule/dependency | Input/slot | Executable location | Guard/limitation | Existing test evidence |
|---|---|---|---|---|
| Replacement ageing | production_year,iranian_year,parts; PS_PRODUCTION_YEAR | operators89-97,123-190; engine529-568 | Schema missing-year condition; replacement status ignored | test_operators age tests; test_engine itemized paths; no repair-status discrimination |
| Battery/tyre | category,new_price,interaction | operators108-190 | U04 | Engine one-pass regression/M19 discriminate double deduction; Review predicate/resolution gap remains |
| Franchise | policy.franchise; PS_FRANCHISE | engine257-382 | G_NO_HARDCODED_FRANCHISE_RATE,U02 | Named-base/minimum/zero tests; source applicability absent |
| Article10 | market/insured; PS_UNDERINSURANCE_RATIO | operators53-70; engine241-254,605-652 | U01; total no-double guard | Partial scenarios, ratio anchors and plan mutations; unresolved rescue scope not spanned |
| Physical total threshold | repair + rescue_for_threshold /market | classify70-80; engine747-785; operators threshold function | Classification reconciliation | Exact75%/M09; Review rescue emission gap |
| Total valuation/disposition | market,insured,salvage,transfer | engine654-745 | XOR/ceiling labels | Total arithmetic/guard-path tests; false physical title not covered |
| Standalone glass | endorsement,terms,parts,ratio | engine788-891; Review370-413 | U03/U11/U14,glass guards | Direct arithmetic fixtures plus blocked Review example; not validated insurer terms |
| Theft dates | event.theft_clock +canonical dates | Review447-480; engine924-1094 | U13,title requirement | Direct and supported Review event/date tests; payment-clock semantics missing |
| Coverage causation | Q-S2-02,PS_CAUSATION_ESTABLISHED | Review883-990; engine425-477 | Named G_NO_ASSUMED_CAUSATION only handles narrower exclusions | Conjunctive-exclusion tests/M18; positive asserted-only gap |
| Prior payment | Q-S9-03 →multiple_insurance | Review503-504,620-638 | No operative body contribution/remainder guard | Round-trip zero metadata only |
| Authorization | decision,claim hash,provenance | admission162-264; compute1462-1493 | Private issuance identity/hash checks | test_admission rejection/mutation suite; graph-content binding absent |
| Confidence/lineage | rule trace,required evidence,authorization cap | engine1327-1406 | Min noted-rule/U confidence; evidence cap | test_provenance envelope checks; no dependency-completeness proof |

## Test adequacy assessment (frozen export)

Independent reruns in Python3.12 with pytest9.1.1 produced **507 passed**, **50/50 fixtures passed**, and the checked-in mutation report remained current with **24/24 killed**. The tests were not treated as the correctness oracle. Added independent assertions: **51 passed**. Separate adversarial probes reproduced the findings above; their incorrect outputs are counterexamples, not additional successful correctness tests.

What these gates prove:

- Many elementary arithmetic operations, explicit operator-order changes, missing source/base checks, selected authorization mutations, date binding and several guard omissions are discriminating.
- The fixture expectation resolver refuses unknown expectation keys instead of skipping them.
- M09 distinguishes strict threshold comparison; M19 distinguishes double depreciation; M20/M22 distinguish named franchise operands; M24 distinguishes the selected theft date binding.

What they do not prove:

- The50 fixtures cover seven domains, not50 full accepted body Review files. Their harness uses an explicit internal authorization and manufactures versioned policy references for scalar franchise inputs. They cannot prove normal evidence/Review admission.
- `_case` in test_engine supplies convenient market/insured anchors, zero aggregate depreciation and synthetic clock sources. Those hide absence and authority questions unless separately tested.
- The24 mutations are curated textual changes evaluated by `mutation_probe.py`, not exhaustive mutation analysis or all507 tests on every mutant. An abnormal mutant exit also counts as killed; a kill is not necessarily a precise financial assertion.
- There is no mutation coverage of repair-only scope, Review rescue emission, positive causation, prior indemnity, physical transfer preconditions, contractual instrument applicability, graph numeric payloads or separate legal theft clocks.
- Parity against legacy formulas shares operand/order assumptions. It cannot adjudicate legal interpretation. Test definitions can be overwritten (IA-16).

The two Article10 partial scenarios span exactly the graph's represented swap of ratio versus franchise **after depreciation and before rescue**. They do not span broader interpretations such as applying a ratio to rescue, an endorsement removing it, a varying franchise operand tied to after-ratio loss, or different authority scopes. Those broader possibilities require separately modeled authority; no numeric scenario interval currently certifies them. Blocking rather than collapsing identical rounded scenarios is appropriately conservative.

## Graph/runtime parity assessment (frozen export, reconfirmed on current branch)

**PARTIAL.**

PASS within the bounded settlement walk: the graph supplies branch operator lists and scenario sequences; the executor validates membership/order, rejects duplicate or unsupported operators, records plan identity and checks required guard accounting. Ratio/franchise/rescue/salvage/ceiling settlement steps have observable order effects.

Not a full PASS: cap/depreciation are already calculated before identity graph steps; numeric constants and permitted plan patterns are independently encoded; graph implementation metadata is not the sole dispatcher for actual arithmetic; Review predicates/uncertainty liveness are partially duplicated; effective rule subsets and knowledge-content identities do not constrain the whole execution. IA-11's rate-payload counterexample directly demonstrates undetected semantic divergence.

## Release assessment (current)

**BLOCK**

This is not ENGINEERING-READY / AUTHORITY-BLOCKED because current P0 findings IA-01/02/03/04/05/07/08/15 reproduce incorrect or unjustified supported-path behavior without first needing a new legal interpretation in order to fail closed. Close those P0s first. Then resolve or explicitly block the P1 theft-clock, retained-salvage franchise, late-notice, recourse and resolution-artifact scopes. Finally complete the P2 graph/provenance/internal-boundary assurance work. Restrict any remaining unsupported scope explicitly and consistently across Review, engine, fixtures and customer documentation.

Once executable admission/calculation defects are closed and unresolved authority is genuinely isolated, the next permissible assessment is ENGINEERING-READY / AUTHORITY-BLOCKED. A release-review-ready state additionally requires applicable, versioned primary/contractual authority and a complete supported-case acceptance corpus. A green suite alone cannot make either transition.

## Reproduction

Extract the original ZIP without editing it. Run:

```bash
cd /path/to/export/model
python -m pytest -p no:cacheprovider
python claim.py fixtures
python scripts/run_mutation_gate.py --check-report
```

The script below takes `/path/to/export/model` as its first argument. It uses the project-provided T1/T2 files as input baselines, changes only detached input dictionaries, and prints independent counterexamples. The graph-rate experiment alters only a deep-copied in-memory Knowledge object. It never writes model files. INTERNAL_TEST_DIRECT probes are visibly separated from supported Review probes.

```python
import json, copy, sys
from pathlib import Path
root = Path(sys.argv[1]).resolve()
sys.path.insert(0, str(root / 'src'))
from iran_auto_claim.review import Review
from iran_auto_claim.engine import compute
from iran_auto_claim.knowledge import Knowledge
from iran_auto_claim.admission import _internal_test_direct_authorize
kb = Knowledge.load(root)
base = json.load(open(root / 'cases/review_t1_fullcover_partial.json'))

def run(label, p):
    try:
        r = Review(p, kb)
        dec = r.decision()
        result = r.calculate()
        print(label, json.dumps({'decision': dec['decision'], 'open': dec['open_blocking_questions'], 'uncertainties': dec['live_uncertainties'], 'result': None if result is None else {'payable': str(result.payable), 'status': result.status, 'depreciation': str(result.fields.get('depreciation')), 'confidence': result.formula_confidence, 'branch': result.branch}}, ensure_ascii=False))
    except Exception as e:
        print(label, type(e).__name__, str(e))
run('baseline', base)
p = copy.deepcopy(base)
p['answers']['Q-S4-03'] = [{'category': 'REPAIR_ONLY', 'assessed_loss': 1200000000, 'requires_replacement': False}]
run('repair_only', p)
p = copy.deepcopy(base)
p['answers']['Q-S4-03'][0]['requires_replacement'] = False
run('replacement_false', p)
for q, val in [('Q-S2-02', 'ASSERTED_ONLY'), ('Q-S3-02', 'SUSPECTED_NO_REPORT'), ('Q-S5-03', 1500), ('Q-S0-02', '1404-99-99'), ('Q-S3-05', 'HELD')]:
    p = copy.deepcopy(base)
    p['answers'][q] = val
    run(q + ':' + str(val), p)
p = copy.deepcopy(base)
for q in ['Q-S6-02', 'Q-S6-04']:
    p['answers'][q]['source'] = 'INSURER_MANUAL'
    p['answers'][q].pop('source_reference', None)
    p['answers'][q].pop('source_version', None)
run('unversioned_manual', p)

def direct(label, p):
    try:
        r = compute(_internal_test_direct_authorize(p, purpose='INDEPENDENT_AUDIT'), kb)
        print(label, json.dumps({'payable': str(r.payable), 'status': r.status, 'reason': r.reason, 'branch': r.branch, 'fields': r.fields}, default=str))
    except Exception as e:
        print(label, type(e).__name__, str(e))
total = {'claim_id': 'independent-total', 'unit': 'IRR', 'classification': {'branch': 'TOTAL_LOSS'}, 'event': {'event_date': '1405-01-01'}, 'vehicle': {'market_value_at_event_irr': 2000, 'insured_sum_irr': 2000}, 'damage': {'repair_total_irr': 1600}, 'policy': {'franchise': {'mode': 'ABSOLUTE', 'absolute_irr': 100, 'source': 'POLICY'}}}
direct('total_absent_salvage', total)
p = copy.deepcopy(total)
p['vehicle']['salvage_disposition'] = 'INSURED_RETAINS'
direct('total_retains_absent_salvage', p)
p = copy.deepcopy(total)
p['vehicle']['salvage_disposition'] = 'INSURER_TAKES_TITLE'
p['vehicle']['title_transferred'] = False
direct('total_title_false', p)
p = copy.deepcopy(base)
p['answers']['Q-S5-01'] = 10000
p['answers']['Q-S5-02'] = 10000
p['answers']['Q-S5-03'] = 1404
p['answers']['Q-S4-02'] = 0
p['answers']['Q-S4-03'] = [{'category': 'OTHER_REPLACEMENT_PART', 'assessed_loss': 7400}]
p['answers']['Q-S4-07'] = 200
run('rescue_threshold_76pct', p)
p = copy.deepcopy(base)
p['answers']['Q-S4-03'][0]['assessed_loss'] = 6500000000
p['answers']['Q-S4-08'] = 1000000000
p['answers']['Q-S4-09'] = 'INSURER_TAKES_TITLE'
p['answers']['Q-S4-06'] = 'NOT_TRANSFERRED'
p['evidence_present'] += ['EVT_SALVAGE_VALUATION', 'EVT_TITLE_TRANSFER_PROOF']
run('review_total_title_not_transferred', p)
p = json.load(open(root / 'cases/review_t2_theft_pending.json'))
p['answers'].update({'Q-S2-08': 60, 'Q-S2-09': 'CONSISTENT', 'Q-S2-10': 'THEFT_OCCURRENCE', 'Q-S2-11': '1404-04-20', 'Q-S2-12': '1404-06-18', 'Q-S2-13': 'SHAMSI', 'Q-S2-14': 'independent police clock', 'Q-S4-06': 'TRANSFERRED'})
p['evidence_present'].append('EVT_TITLE_TRANSFER_PROOF')
run('theft_occurrence60_declaration59', p)
p = copy.deepcopy(base)
p['answers']['Q-S4-03'][0]['assessed_loss'] = 6500000000
p['answers']['Q-S4-08'] = 1000000000
p['answers']['Q-S4-09'] = 'INSURER_TAKES_TITLE'
p['answers']['Q-S4-06'] = 'NOT_TRANSFERRED'
p['evidence_present'] += ['EVT_SALVAGE_VALUATION', 'EVT_TITLE_TRANSFER_PROOF']
for q in ['Q-S6-02', 'Q-S6-03']:
    p['answers'][q]['calculation_base'] = 'SETTLEMENT_BASE'
run('review_total_title_false_valid_franchise', p)
p = copy.deepcopy(base)
p['answers']['Q-S4-03'][0]['assessed_loss'] = 6500000000
p['answers']['Q-S4-08'] = 1000000000
p['answers']['Q-S4-09'] = 'NOT_APPLICABLE'
p['evidence_present'] += ['EVT_SALVAGE_VALUATION']
for q in ['Q-S6-02', 'Q-S6-03']:
    p['answers'][q]['calculation_base'] = 'SETTLEMENT_BASE'
run('review_total_not_applicable_salvage', p)
p = copy.deepcopy(base)
p['answers']['Q-S9-03'] = 1850000000
p['answers']['Q-S6-05'] = 'YES_OTHER_POLICIES'
p['evidence_present'] += ['EVT_OTHER_POLICIES', 'EVT_ARBITRATION_OR_COURT_AWARD']
run('prior_full_compensation', p)
p = copy.deepcopy(base)
p['answers']['Q-S9-01'] = 'RELEASED_PARTY'
p['evidence_present'] += ['EVT_JUDICIAL_FINDING', 'EVT_ARBITRATION_OR_COURT_AWARD']
run('subrogation_release', p)
p = copy.deepcopy(base)
p['answers']['Q-S0-04'] = 'LATE_NO_REASON'
run('late_notice', p)
p = copy.deepcopy(base)
p['answers']['Q-S0-04'] = 'LATE'
p['evidence_present'] += ['EVT_JUDICIAL_FINDING', 'EVT_ARBITRATION_OR_COURT_AWARD']
run('late_without_excuse', p)
p = copy.deepcopy(base)
p['answers']['Q-S4-03'] = [{'category': 'BATTERY', 'assessed_loss': 90, 'new_price': 200}]
p['answers']['Q-S4-02'] = 0
p['answers']['Q-S4-07'] = 0
p['answers'].pop('Q-S8-02', None)
run('battery_question_gate', p)
p = copy.deepcopy(base)
p['answers']['Q-S4-03'] = [{'category': 'BATTERY', 'assessed_loss': 90}]
p['answers']['Q-S4-04'] = 200
p['answers']['Q-S4-02'] = 0
p['answers']['Q-S4-07'] = 0
p['answers']['Q-S8-02'] = 'CAP_ONLY'
run('battery_separate_new_price', p)
p = copy.deepcopy(base)
p['answers']['Q-S4-03'][0]['assessed_loss_irr'] = 1
run('contradictory_part_aliases', p)
changed = copy.deepcopy(kb)
changed.rules['REG53_ART19_REPLACEMENT_PART_DEPRECIATION']['rule_payload']['annual_rate'] = 0.2
z = compute(Review(base, kb).authorize(), changed)
print('detached_graph_rate20pct', json.dumps({'payable': str(z.payable), 'depreciation': str(z.fields['depreciation']), 'franchise_policy_snapshot': z.authorization['policy_snapshot']}))
```

### Independent invariant assertions

Run this separate script with the same model-directory argument. Expected result: 51 assertions passed.

```python
import sys, json, copy
from pathlib import Path
from decimal import Decimal as D
from dataclasses import replace
root = Path(sys.argv[1]).resolve()
sys.path.insert(0, str(root / 'src'))
from iran_auto_claim import operators as op
from iran_auto_claim.engine import compute, _dated_theft_clock_days
from iran_auto_claim.review import Review
from iran_auto_claim.admission import AuthorizationError, CalculationAuthorization, _internal_test_direct_authorize
from iran_auto_claim.knowledge import Knowledge
from iran_auto_claim.schema_input import InputSchemaError
kb = Knowledge.load(root)
checks = []

def check(name, condition):
    assert condition, name
    checks.append(name)

def rejects(name, func, errors=(Exception,)):
    try:
        func()
    except errors:
        checks.append(name)
    else:
        raise AssertionError(name)
for index, rate in [(1, '0'), (2, '0'), (3, '0'), (4, '0'), (5, '.05'), (6, '.10'), (8, '.20'), (9, '.25'), (15, '.25')]:
    check(f'depreciation year {index}', op.replacement_part_depreciation_rate(1400, 1399 + index, 'OTHER_REPLACEMENT_PART') == D(rate))
for category in ['GLASS', 'LAMP_GLASS']:
    check(category + ' exemption', op.replacement_part_depreciation_rate(1380, 1405, category) == 0)
for repair, wanted in [(7499, False), (7500, False), (7501, True)]:
    check('threshold ' + str(repair), op.is_total_loss(D(repair), D(0), D(10000))[0] is wanted)
for mode, wanted in [('CAP_THEN_DEPRECIATE', 75), ('DEPRECIATE_THEN_CAP', 90), ('CAP_ONLY', 100)]:
    result = op.eligible_part_loss({'category': 'BATTERY', 'assessed_loss': D(120), 'new_price': D(200)}, 1396, 1404, {'battery_tire_depreciation_interaction': mode})
    check(mode, result['loss_after_depreciation'] == wanted and result['capped_loss'] - result['depreciation_amount'] == wanted)
check('minimum franchise', op.franchise_amount('PERCENT_WITH_MINIMUM', D(100), D('.1'), minimum=D(20)) == 20)
rejects('ratio missing insured', lambda: op.underinsurance_ratio(None, D(100)), (op.OperatorError,))
rejects('ratio missing market', lambda: op.underinsurance_ratio(D(100), None), (op.OperatorError,))
for end, n in [('2026-03-01', 59), ('2026-03-02', 60), ('2026-03-03', 61)]:
    check('Gregorian clock ' + str(n), _dated_theft_clock_days({'start_date': '2026-01-01', 'as_of_date': end, 'calendar': 'GREGORIAN'}) == n)
check('Shamsi leap cross year', _dated_theft_clock_days({'start_date': '1403-12-29', 'as_of_date': '1404-01-02', 'calendar': 'SHAMSI'}) == 3)
check('Shamsi common cross year', _dated_theft_clock_days({'start_date': '1404-12-29', 'as_of_date': '1405-01-02', 'calendar': 'SHAMSI'}) == 2)
rejects('Shamsi common Esfand30', lambda: _dated_theft_clock_days({'start_date': '1404-12-30', 'as_of_date': '1405-01-02', 'calendar': 'SHAMSI'}), (op.OperatorError,))
rejects('reverse clock', lambda: _dated_theft_clock_days({'start_date': '2026-03-03', 'as_of_date': '2026-01-01', 'calendar': 'GREGORIAN'}), (op.OperatorError,))
base = json.load(open(root / 'cases/review_t1_fullcover_partial.json'))
r = Review(base, kb)
a = r.authorize()
v = compute(a, kb)
rejects('raw payload rejected', lambda: compute(r.case_payload(), kb), (AuthorizationError,))
rejects('bare authorization rejected', lambda: compute(CalculationAuthorization('COMPUTE', 'REVIEW_GATE'), kb), (AuthorizationError,))
rejects('replace rejected', lambda: compute(replace(a, decision='SCENARIO_SET'), kb), (AuthorizationError,))
p = a.claim_payload()
p['damage']['labor_irr'] = 0
check('detached claim cannot retarget', compute(a, kb).payable == v.payable)
p = copy.deepcopy(base)
p['answers'].pop('Q-S5-03')
check('missing production year blocks Review', Review(p, kb).calculate() is None)
p = copy.deepcopy(base)
p['answers']['Q-S3-07'] = 'YES'
check('risk intensification blocks Review', Review(p, kb).calculate() is None)
p = copy.deepcopy(base)
for q in ['Q-S6-02', 'Q-S6-03', 'Q-S6-04']:
    p['answers'][q].pop('calculation_base', None)
check('missing franchise base blocks Review', Review(p, kb).calculate() is None)
p = r.case_payload()
p['damage']['parts'][0]['assessed_loss_irr'] = True
rejects('boolean money rejected', lambda: _internal_test_direct_authorize(p, purpose='AUDIT'), (InputSchemaError,))
theft = json.load(open(root / 'cases/review_t2_theft_pending.json'))
theft['answers'].update({'Q-S2-09': 'CONSISTENT', 'Q-S2-10': 'THEFT_OCCURRENCE', 'Q-S2-11': '1404-04-20', 'Q-S2-12': '1404-06-18', 'Q-S2-13': 'SHAMSI', 'Q-S2-14': 'audit police clock', 'Q-S4-06': 'TRANSFERRED'})
theft['evidence_present'].append('EVT_TITLE_TRANSFER_PROOF')
for days, day in [(59, 17), (60, 18), (61, 19)]:
    p = copy.deepcopy(theft)
    p['answers']['Q-S2-08'] = days
    p['answers']['Q-S2-12'] = f'1404-06-{day}'
    z = Review(p, kb).calculate()
    check(f'Review theft {days}', z is not None and (z.payable is None if days == 59 else z.payable == 7200000000))
for event, q in [('THEFT_OCCURRENCE', 'Q-S0-02'), ('AWARENESS', 'Q-S0-03'), ('DECLARATION', 'Q-S0-07')]:
    p = copy.deepcopy(theft)
    p['answers']['Q-S2-10'] = event
    p['answers']['Q-S2-11'] = p['answers'][q]
    z = Review(p, kb)
    check(event + ' canonical binding', 'theft_clock' in z.case_payload()['event'])
    p['answers'].pop(q)
    z = Review(p, kb)
    check(event + ' missing canonical date', 'U13_THEFT_CLOCK_ANCHOR' in z.open_uncertainties() and z.calculate() is None)
    p = copy.deepcopy(theft)
    p['answers']['Q-S2-10'] = event
    p['answers']['Q-S2-11'] = '1404-04-19'
    z = Review(p, kb)
    check(event + ' mismatched date', 'U13_THEFT_CLOCK_ANCHOR' in z.open_uncertainties() and z.calculate() is None)
p = Review(theft, kb).case_payload()
p['event']['days_vehicle_missing'] = 99
z = compute(_internal_test_direct_authorize(p, purpose='AUDIT'), kb)
check('stored elapsed days cannot override dates', z.payable is None and z.status == 'INPUT_ERROR')
p = Review(theft, kb).case_payload()
p['event']['theft_clock']['start_date'] = '1404-04-19'
z = compute(_internal_test_direct_authorize(p, purpose='AUDIT'), kb)
check('internal mismatched event cannot pay', z.payable is None and z.status == 'INPUT_ERROR')
p = Review(theft, kb).case_payload()
p['event']['theft_clock']['start_event'] = 'DECLARATION'
p['event'].pop('declaration_date')
z = compute(_internal_test_direct_authorize(p, purpose='AUDIT'), kb)
check('internal missing selected event blocks U13', z.payable is None and 'U13_THEFT_CLOCK_ANCHOR' in z.blocking_uncertainties)
check('Gregorian Shamsi cross-year interval equivalence', _dated_theft_clock_days({'start_date': '2025-03-19', 'as_of_date': '2025-03-22', 'calendar': 'GREGORIAN'}) == _dated_theft_clock_days({'start_date': '1403-12-29', 'as_of_date': '1404-01-02', 'calendar': 'SHAMSI'}))
print(json.dumps({'passed': len(checks), 'checks': checks}, indent=2))
```
