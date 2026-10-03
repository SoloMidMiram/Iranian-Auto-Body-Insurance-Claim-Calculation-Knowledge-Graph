# Iranian Auto Insurance Claim Calculation — Knowledge Graph and Rule Engine

A machine-readable knowledge model for Iranian motor claim calculation, with an
engine that executes it. It replaces the naive template

```
خسارت − استهلاک − فرانشیز − ماده ۱۰ = پرداخت
```

with a **classification-first, provenance-backed, uncertainty-aware** pipeline:

```
EVENT → LEGAL/POLICY SNAPSHOT → COVERAGE + CAUSATION + EXCLUSION GATE
     → CLAIM BRANCH CLASSIFICATION → BRANCH-SPECIFIC VALUATION
     → COMPONENT CLASSIFICATION → APPLICABLE OPERATORS
     → CONFIGURABLE OPERATOR ORDER → STATUTORY/CONTRACTUAL CAPS
     → DUAL-COVERAGE ALLOCATION → SUBROGATION/LEGAL RECOVERY
     → PAYABLE + RULE TRACE + PROVENANCE + CONFIDENCE + UNRESOLVED VARIABLES
```

Three commitments hold everywhere in the code:

1. **Every executable node carries provenance** — source class, authority,
   instrument, article, effective version/date, confidence, validation cycle.
2. **Uncertainty is data, not a missing value.** Where the primary text does not
   settle an operation, the engine returns a *scenario set* or refuses. It never
   invents a number.
3. **Confidence is computed, not asserted.** A result's confidence is the minimum
   of the confidences of the rules it actually cited, further capped by the
   single-interpretation confidence of any live blocking uncertainty.

## Quickstart

No dependencies beyond the standard library. Python 3.10+.

```bash
python claim.py validate              # integrity gate over the whole graph
python claim.py fixtures              # run the 50-case P01–L50 validation corpus
python claim.py review cases/review_t1_fullcover_partial.json --calc
python claim.py questionnaire --stage S4_DAMAGE_SCOPE
python claim.py parameters --branch PARTIAL_DAMAGE
python claim.py ladder                # the iterative completion rungs and their gates
python claim.py flowchart             # the review-and-calculation flowchart, as mermaid
python claim.py calc cases/example_partial_resolved.json
python claim.py calc cases/example_partial_unresolved.json
python claim.py unknowns              # every unresolved variable, with what resolves it
python claim.py contradictions        # the contradiction matrix as data
python claim.py queries               # the report's documented graph query patterns, answered
python claim.py branch PARTIAL_DAMAGE # operator order and status for a branch
python claim.py rule REG53_ART19_REPLACEMENT_PART_DEPRECIATION
python claim.py node OP_UNDERINSURANCE_RATIO
python claim.py params --year 1405
python claim.py ingest submissions/example_conflicting_educational.json
```

The persistence and engine boundary accepts monetary values only as non-negative
integer IRR. Toman and million-toman conversion is explicit presentation logic.

Tests: `python -m pytest` (363 tests). Install development/test
dependencies with `pip install -e ".[test]"`; `pip install -e .` installs only
the dependency-free runtime and the `iran-claim` console script.

The two worked examples are the same claim under two configurations. With the
operator order resolved you get one payable and confidence 0.95; with it
unresolved you get two scenarios and confidence 0.55, plus an escalation prompt.
That contrast is the whole point of the model.

## Case review: from a claim file to the right parameters

The engine computes an amount from a claim case, but only from one that has been
authorized. Before that may happen, someone has
to establish what happened, whether cover applies, and which parameters are sourced.
That review layer is a gate-ordered questionnaire over the same graph:

```
FILE → INVESTIGATION → CLASSIFICATION → PARAMETER LOCK → DECISION
                                            COMPUTE | SCENARIO_SET | REFUSE | INSUFFICIENT
```

* `knowledge/review_procedure.json` — 11 stages, 58 discriminating questions, each
  with a closed answer vocabulary, the condition under which it is asked, the
  parameter slots its answer binds, the evidence it demands and the rung it belongs to.
* `knowledge/parameter_slots.json` — every value a calculation consumes, with who is
  allowed to supply it, which operator reads it, and what happens when it is absent.
* `knowledge/evidence_items.json` — the documents a file must hold, each tagged with
  the kind of authority that demands it, so an insurer checklist never reads as law.
* `knowledge/case_tiers.json` — the iterative ladder, T0 (one number, nothing assumed)
  to T6 (anything not yet certified), each rung adding one source of complexity.

An answer may **select** knowledge but never create it: a questionnaire entry that
tried to bind a numeric rate fails `validate`. Absence is recorded as `UNKNOWN`,
`NOT_TRIGGERED` or `NOT_APPLICABLE` and stops the decision, rather than defaulting to
zero or to a full-cover ratio of one. See the compact
[`Body Claim Acceptance Model`](docs/BODY_CLAIM_ACCEPTANCE_MODEL.md) for the FAQ-facing
architecture and calculation contract, and
[`docs/BODY_CASE_REVIEW_MODEL.md`](docs/BODY_CASE_REVIEW_MODEL.md) for the generated
questionnaire, parameter-selection matrix and worked traces;
`python scripts/sync_review_docs.py --write` refreshes the generated tables inside it.

## The authorization boundary

The engine cannot be handed a claim. `compute()` accepts a
`CalculationAuthorization` and refuses a raw payload, a `Case`, or anything else,
so no script, feature or future caller can reach the arithmetic without an issuer
having admitted the file:

```
raw claim → review gate → CalculationAuthorization → compute() → result
```

`Review.authorize()` is the only producer for a claim file and raises on `REFUSE`
and `INSUFFICIENT_INFORMATION`, which makes those two outcomes structurally
incapable of reaching the calculator. The authorization binds the exact emitted
payload by SHA-256 hash, so a case edited after issuance is refused rather than
recalculated. Synthetic fixtures, the mutation probe and `claim.py calc` go through
the narrow named channel `engine_direct_authorize()`, which still enforces the
schema and records `ENGINE_DIRECT` as the issuer. Every result carries that
authorization provenance in `CalcResult.authorization`.

## Project delivery and safety status

The current repository is a **research and adjuster decision-support system**.
It is not approved for unattended production payment. The ordered completion
plan, phase gates, and import-ready GitHub backlog are maintained in:

* [`docs/ROADMAP.md`](docs/ROADMAP.md) — investigation, implementation, phase
  ordering, preparation for the next phase, and release discipline.
* [`docs/VALIDATION_GATES.md`](docs/VALIDATION_GATES.md) — universal invariants,
  branch-specific boundary cases, and phase acceptance evidence.
* [`planning/issues.json`](planning/issues.json) — stable roadmap issue IDs,
  milestones, labels, dependencies, acceptance criteria, and validation.
* [`CONTRIBUTING.md`](CONTRIBUTING.md) and [`SECURITY.md`](SECURITY.md) — source,
  review, privacy, and high-impact defect controls.

Preview the planned milestones and issues without changing GitHub:

```bash
python scripts/sync_github_issues.py \
  --repo SoloMidMiram/Iranian-Auto-Body-Insurance-Claim-Calculation-Knowledge-Graph
```

Creating missing milestones, labels, and issues requires an explicitly supplied
repo-scoped `GITHUB_TOKEN` and the additional `--apply` flag.

## Layout

```
schema/claim-case.schema.json     input contract for a claim
ontology/ontology.json            classes, edges, source-class hierarchy, branch aliases
knowledge/sources.json            source register: tier, URL, retrieval date, access notes
knowledge/rules.json              LegalRule nodes with full provenance envelopes
knowledge/operators.json          the eight operator families, with implementations
knowledge/branches.json           branch → ordered operator list + order status + scenarios
knowledge/annual_parameters.json  versioned annual nodes (1405), derived values marked DERIVED
knowledge/uncertainties.json      unresolved variables, blocking flags, resolution artefacts
knowledge/contradictions.json     the contradiction matrix, resolution + confidence
knowledge/exclusions.json         Article 5 endorsable vs Article 6 non-compensable
knowledge/guards.json             guardrails, each with an enforced_in and a triggered_label
knowledge/evidence_items.json     the documents a claim file must hold, and who demands them
knowledge/review_procedure.json   review stages and the questionnaire that drives them
knowledge/parameter_slots.json    every value a calculation consumes, and who may supply it
knowledge/case_tiers.json         the iterative completion ladder, T0 through T6
fixtures/cases.json               the P01–L50 corpus, with expected outcomes
submissions/                      sample ingestion submissions (rejected / superseding)
cases/                            schema-shaped worked examples, plus review answer files
src/iran_auto_claim/              money, case normalisation, knowledge, operators,
                                  guards, classify, engine, render, review, ingest,
                                  fixtures, cli
tests/                            fixtures, knowledge, operators, engine, guards,
                                  ingest, money, cli, review
```

`src/iran_auto_claim/knowledge.py` is the only module that reads the knowledge
files, and `Knowledge.validate()` is the schema-first ingestion gate. It is what
an added node must pass: provenance completeness, referential integrity across
declared edge fields, operator implementations that resolve to real callables,
guardrails whose `enforced_in` resolves, blocking uncertainties that a branch can
actually reach, and contradiction nodes whose controlling authority outranks the
candidate they reject.

## How the graph is expanded

Adding knowledge is a data operation, and the tooling enforces the rules:

| Change | How | What must also happen |
|---|---|---|
| New rule | `ingest` submission through the closed schema | contradiction check against the same topic; provenance envelope |
| New operator | add to `knowledge/operators.json` with an `implementation` | loader verifies the dotted path resolves |
| New branch | add to `knowledge/branches.json` | declare operator sequence, order status, scenarios if unresolved |
| New insurer | add `INSURER_PROCEDURE` nodes, attach to a policy version | may override configurable operators only |
| New annual parameter | add an `AnnualParameter` node for the year | no rule changes; derived values marked `DERIVED` |
| Resolve an uncertainty | update the branch's `order_status`, keep the old scenarios | validation re-checks scenario consistency |
| Contradiction found | `ingest` writes a `Contradiction` node | human review flag |

The ingestion gate has two brakes and one warning:

* **Brake — hierarchy.** A submission that contradicts a same-topic rule is
  refused outright if a *higher-ranked* source class controls it. An EDUCATIONAL
  blog claim cannot override a Regulation; `submissions/example_conflicting_educational.json`
  demonstrates exactly this, and the engine blocks it.
* **Brake — human decision.** A submission that wins or ties still needs
  `--accept-review`. Silently replacing a rule the engine executes is not a side
  effect a schema check should be able to authorise.
* **Warning — near misses.** Matching is on instrument+article identity (or an
  explicit `topic`). If nothing matches but existing rules share part of the
  identity, the plan says so, because "no contradiction found" and "you mistyped
  the instrument" must not look the same.

After a supersede, the ledger is honest rather than tidy: the old rule is marked
`SUPERSEDED`, nothing is silently rewired, and `validate` keeps failing with
explicit "still cites superseded rule" issues until the references are migrated.
`tests/test_ingest.py` performs that migration and asserts the graph validates
clean afterwards.

## The validation corpus

`fixtures/cases.json` holds all 50 synthetic cases from the report (P01–L50),
transcribed with their expected outcomes. `tests/test_fixtures.py` runs every one
of them, and the harness is deliberately strict: an expected key it cannot
resolve fails the test rather than being skipped, so a fixture can never pass by
having nothing checked.

Several fixtures expect `payable: null`, and that is a feature:

| Fixture | Why there is no single number |
|---|---|
| P10, P11 | The underinsurance ratio's position relative to the franchise is unstated. Two sourced scenarios are returned. |
| G27 | Standalone glass: endorsement terms and order both required. |
| P14, TH33 | The law identifies the coverage architecture; the *endorsement* supplies the missing economics. |
| TP37 | The vehicle is non-conventional; the engine refuses to manufacture an Article 8 correspondence assessment. |
| T22, TH29 | Whole-vehicle theft below 60 days: pending, not payable. |

## Corrections the model encodes

Each of these is a `Contradiction` node the engine resolves, not a comment:

| Topic | Internet template | Model |
|---|---|---|
| Article 10 | a deduction | `UNDERINSURANCE_RATIO = min(1, insured/market)` |
| Depreciation | consumables only | all replaced parts except glass/lamp glass; 5%/yr from the 5th production year, max 25% |
| Battery/tires | ordinary depreciation | separate 50%-of-new-price cap; interaction with aging **left unresolved** (U04) |
| Glass franchise | universal 20% | no universal statutory rate; policy-defined (guardrail refuses a hardcoded one) |
| Glass and Article 10 | automatically exempt | **unproven**; endorsement wording required (U11) |
| Total loss | 75% threshold | strictly `> 75%`; equality stays partial |
| Total loss + underinsurance | apply ratio after `min(market, insured)` | double application prohibited (guardrail) |
| Salvage vs franchise | franchise first | salvage first (Circular 1400/401/146850) |
| Article 8 | `damage × threshold / luxury_value` | component-wise correspondence (1398/06/13 amendment); whole-car ratio refused by guardrail |
| Article 8 excess vs at-fault | sue for all excess | capped against the at-fault party too; own body policy is the route |
| Exclusions | one `coverage = false` | `EXCLUDED_BUT_ENDORSABLE` vs `NON_COMPENSABLE` |
| عامل بلافصل حادثه | a multiplier | a causation predicate, never a multiplier |

## Confidence model

`CalcResult.formula_confidence` is computed in `engine._finalize`:

```
confidence = min( confidence of every cited rule,
                  confidence_of_single_interpretation of every live blocking uncertainty )
```

So a clean full-cover partial claim lands at 0.99, one that cites the rescue rule
(v0.95) lands at 0.95, and one with an unresolved operator order lands at 0.55 —
the same 0.55 the report assigns to that topic. Tests assert these values.

## Deliberate deviations from the report text

1. **`INSURER_MAY_PURSUUE_RESPONSIBLE_PARTY` → `INSURER_MAY_PURSUE_RESPONSIBLE_PARTY`.**
   A typo in the fixture text; the corrected token is used in both the engine and
   the fixture. Recorded in `fixtures/cases.json` under `corrections_applied`.
2. **Node id key.** All nodes use `node_id` uniformly; `ontology.json` declares
   `id_property: "node_id"` and `Branch` uses `branch`.
3. **Test-variant labels are not branches.** `TOTAL_LOSS_TEST`, `TOTAL_THEFT`,
   `ARTICLE_8_DUAL_COVERAGE`, `ORDINARY_FINANCIAL` and `THEFT_PARTIAL_DAMAGE` are
   documented aliases that select a sub-mode inside a canonical branch, so the
   branch vocabulary stays closed.
4. **Two extra uncertainty nodes.** `U11_GLASS_ARTICLE10_EXEMPTION` and
   `U12_SALVAGE_DISPOSITION` were added because the glass engine and the
   total-loss settlement each need an uncertainty record that the report's list of
   ten does not contain.
5. **`accepted_candidate_as_incomplete`.** Contradiction C03 resolves as
   `ACCEPT_CANDIDATE_AS_INCOMPLETE`: the battery/tire rule does not take *only*
   the regular schedule, and the cap interaction remains open.

## Status against the report's priority table

| # | Task | Status |
|---|---|---|
| 1 | Provenance envelope on every node | done, validated |
| 2 | Claim classifier decision tree | done (`classify.py`, `derive_branch` equivalent) |
| 3 | Operators registered with formulas | done, implementations verified resolvable |
| 4 | OperatorOrder as configurable data | done (`branches.json`, scenarios returned) |
| 5 | Contradiction matrix as queryable nodes | done (13 nodes, `claim.py contradictions`) |
| 6 | Guardrails (double application, caps) | done (13 guardrails, each executable) |
| 7 | GraphRAG retrieval over the ontology | **deterministic graph queries built** (`claim.py queries`, `node`, `branch`, `rule`); embedding/LLM retrieval **not built** |
| 8 | Scenario-set responses for uncertainties | done for every unresolved branch |
| 9 | Insurer adapter slots | registered but **deliberately empty**; nothing is invented |
| 10 | Annual parameter refresh pipeline | versioned nodes + `DERIVED` markers; 1406 pending |
| 11 | 50 test cases as a validation suite | done, all passing |
| 12 | Human-in-the-loop escalation UI | escalation prompts rendered; no UI |

## Known limits

* **The insurer adapter is empty.** No current authoritative manual for Asia,
  Pasargad or Parsian was obtained, so no franchise schedule, endorsement wording
  or Article 8 valuation table is populated. `U02`, `U03` and `U06` are the live
  consequences.
* **Annual parameters are secondary-sourced.** The 1405 diyah (2.8bn tomans) comes
  from secondary reporting. The 1.4bn threshold and 70m minimum are *derived*
  (50% and 2.5% of the bodily ceiling) and marked `DERIVED`, both carrying
  `requires_primary_revalidation: true` and confidence 0.86. Replace before
  certification; no rule changes are needed.
* **Article 8 correspondence is an input, not a computation.** The engine consumes
  an assessor's `corresponding_damage` and refuses when it is absent. That is
  correct — the amended instruction delegates the valuation map to experts.
* **`Rescue denominator` and `battery/tire interaction`** are carried as explicit
  configuration with `UNRESOLVED` defaults, so the engine asks rather than
  choosing.
* **An artificial-clock dependency:** ingested rules get `last_validated` from the
  ingestion date, overridable with `as_of` for deterministic runs.

## Where to calibrate next

The highest-value next input is not more general reading, it is a small set of
insurer documents. In priority order:

1. One underinsured partial-loss worksheet per insurer showing gross parts/labour,
   depreciation, franchise and final payment — this settles U01, the single
   biggest source of amount variance.
2. The franchise schedules by product and policy version (U02), including theft,
   partial theft, glass and natural-disaster rates.
3. Glass-only endorsement wording (U03, U11).
4. The Article 8 component valuation map (U06) and the annual conventional
   reference set (U07).
5. The primary Judiciary 1405 announcement (U08).

`claim.py ingest` is the supported path for all of them: schema-validated,
hierarchy-checked, contradiction-flagged, and human-authorised before it changes
what the engine does.
