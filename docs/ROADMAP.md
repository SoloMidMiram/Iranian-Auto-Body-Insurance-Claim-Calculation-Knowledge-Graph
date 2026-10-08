# Delivery roadmap

## Purpose and release posture

This roadmap turns the current knowledge model into a defensible, fail-closed
Iranian motor-claim decision-support system. It deliberately separates four
questions that must not be conflated:

1. **What authority applies?** Legal and contractual source investigation.
2. **What happened?** Claim classification, evidence, and coverage decisions.
3. **What is the amount?** Deterministic operators, order, caps, and rounding.
4. **May the system issue one number?** Uncertainty, confidence, and human review.

Until Phase 6 is accepted, the project is **research and adjuster decision
support only**. It must not be represented as an unattended production payment
authority.

## One-week body-model completion sprint — 2026-10-07 to 2026-10-13

The achievable one-week target is `v0.1-body-model`: a reproducible,
fail-closed research and adjuster decision-support release for
`PARTIAL_DAMAGE`, `TOTAL_LOSS`, `GLASS_ONLY`, and `THEFT`. In this sprint,
"complete" means that the body-model logic, authority records, provenance,
graph execution, guards, and validation evidence are internally complete for
those four branches. It does **not** mean insurer calibration, unattended
payment authority, or production certification; those remain in Phases 3-6.

### Scope lock

In scope:

- issues `#7`, `#8`, `#10`-`#15` and the release checklist in `#6`;
- primary-source authority records and hashes for every executable body rule;
- effective-dated snapshots and sourced theft-clock dates;
- closed claim/evidence taxonomy for the four supported branches;
- graph-authoritative plans, guard coverage, property/mutation tests, and
  direct/graph parity;
- a tagged release dossier that pins code, graph, source, and parameter
  versions and states every unsupported scope.

Explicitly out of scope for the week:

- third-party liability and Article 8 expansion (`#4`, `#9`);
- insurer/product calibration and assessor procedure packs (Phase 3);
- independent field validation, APIs, monitoring, GraphRAG, and production
  certification (Phases 4-6);
- new claim branches, convenience features, or classifier broadening that are
  not required by a listed release gate.

### Dated execution plan

Preparation may overlap, but merges preserve the dependency order. Keep no
more than two workstreams active and designate one integrator for the release.

| Date | Lane | Issues | Deliverable and exit evidence |
|---|---|---|---|
| Oct 7 | Authority | `#7`, `#11` | Freeze the body-rule source inventory; record source class, effective dates, clause locators, hashes, and revalidation state. Name two human reviewers. Merge `#7` before `#11`. |
| Oct 8 | Temporal | `#8` | Implement effective-dated snapshots and sourced occurrence, awareness, declaration, document, and as-of dates. Prove the 60-day derived clock. |
| Oct 9 | Provenance | `#10` | Complete dependency-derived provenance and confidence, including review-returned and graph-selected evidence. No single payable survives blocking uncertainty. |
| Oct 10 | Claim model | `#12` | Close the four-branch taxonomy and add 59/60/61-day theft boundary tests. Refuse contradictory or unmapped evidence. |
| Oct 11 | Execution | `#13`, `#14` | Make graph operator order/config authoritative, then prove every public path invokes admission, computation, and consistency guards. |
| Oct 12 | Validation | `#15` | Pass deterministic, property, mutation, and direct/graph parity suites; assemble the release manifest and evidence dossier. |
| Oct 13 | Release | `#6` checklist | Independent re-review, clean repository gate, zero unresolved P0/P1 body-model blockers, merge freeze, and tag `v0.1-body-model` only if every hard gate passes. |

### Operating rules and hard gates

- Use one pull request per dated deliverable; keep each PR reviewable in less
  than half a day and require its issue acceptance evidence in the PR body.
- Hold a 15-minute daily triage: blockers, changed assumptions, gate status,
  and the next 24-hour owner. Do not add scope during the sprint.
- A dependency may be prepared in parallel but may not merge before its
  predecessor. Failed gates reopen the owning issue; they are not waived by
  documentation alone.
- By the end of Oct 7, `#7` must have two named reviewers and accessible source
  artifacts. If either is missing, the week may end in an
  `engineering-complete/authority-blocked` release candidate, but it must not
  be tagged or described as complete.
- Freeze feature work at the end of Oct 11. Oct 12-13 are reserved for defects,
  evidence, reproducibility, and release review.
- Any unexplained direct/graph difference, mutation survivor in a required
  rule, missing source hash, or payable result with blocking uncertainty is a
  release stop.

### Definition of done for the week

The sprint is complete only when all of the following are true:

1. Issues `#7`, `#8`, and `#10`-`#15` meet their acceptance criteria and close
   with reproducible evidence; `#6`'s release checklist is fully checked.
2. All four supported branches have review-to-validated-case-to-engine
   coverage and explicit unsupported-state behavior.
3. Two human reviewers sign the authority pack; every executable body rule has
   a clause locator, effective-date interval, source hash, and revalidation
   status.
4. The full repository gate passes from a clean checkout, including fixtures,
   property tests, mutation assertions, and direct/graph parity.
5. The release manifest pins code, graph, schema, parameter, and source
   versions, and the tag states that the release is research/decision-support
   only.

### Research/model validation checkpoint — 2026-10-08

The cross-check in
[`RESEARCH_REPORT_MODEL_VALIDATION.md`](RESEARCH_REPORT_MODEL_VALIDATION.md)
found four amount/eligibility defects that precede the remaining sprint work:

- Article 8 does not yet cap by actual loss and treats explicit zero as absent;
- a causation-required exclusion can fire from a bare cause token;
- configured `DEPRECIATE_THEN_CAP` applies battery/tyre depreciation twice;
- percentage-franchise base semantics are collected but not executed.

It also found that review-authorized live uncertainties are not universally
reconciled with the result's blocking-uncertainty set. Treat RMV-001 through
RMV-006 in that audit as release stops. They refine the existing P0/P2/P3 issue
scope and must be repaired or explicitly removed from supported scope before the
Oct 11 feature freeze; passing the original 50 fixtures does not close them.

### Practical roadmap after `v0.1-body-model`

These ranges begin only after the one-week gate passes and are capacity
estimates, not certification promises.

| Horizon | Focus | Exit condition |
|---|---|---|
| Weeks 2-5 | Phase 3 insurer/product calibration | One signed adapter package, procedure/version maps, worked examples, and variance report. |
| Weeks 4-9 | Phase 4 independent validation | Blinded replay dossier, discrepancy log, threshold tuning with provenance, and independent legal/domain sign-off. |
| Weeks 8-13 | Phase 5 private pilot | Authenticated API, human escalation queue, monitoring, replayable decisions, rollback drill, and pilot acceptance. |
| Weeks 14-16 | Phase 6 controlled release | Final legal/actuarial/security review, immutable release artifacts, runbooks, and documented operating limits. |

Advancement remains evidence-gated. Calendar pressure never converts an unmet
phase exit criterion into an accepted risk.

## Priority and impact scale

| Score | Meaning |
|---:|---|
| 5 | Could change legal eligibility or payable amount across many claims |
| 4 | Major audit, provenance, historical-version, or operational risk |
| 3 | Important but branch-specific capability |
| 2 | Productivity or usability improvement |
| 1 | Cosmetic or low-risk maintenance |

Priorities are ordered `P0` through `P3`. A phase cannot pass while it has an
open P0 issue, an unmet exit criterion, or missing validation evidence.

## Workstreams

| Segment | Scope | Primary output |
|---|---|---|
| A — Authority | Statutes, regulations, circulars, policy terms, effective dates | Versioned authority register |
| B — Claim model | Cases, evidence, coverage, causation, exclusions, classification | Closed claim/evidence schema |
| C — Calculation | Operators, order, caps, money, rounding, invariants | Fail-closed calculation engine |
| D — Calibration | Insurer/product/version procedures and assessor mappings | Signed adapter packages |
| E — Validation | Synthetic boundaries, real worksheets, mutation/property tests | Reproducible validation dossier |
| F — Governance | Ingestion, contradiction review, audit history, releases | Controlled change process |
| G — Product | API, human escalation, monitoring, retrieval | Private pilot service |

## Phase sequence

### Phase 0 — Repository baseline and immediate safety containment

**Goal:** establish a reproducible private repository and eliminate known paths
that can silently overpay, underpay, or accept malformed claims.

Investigation:

- Inventory code, knowledge files, sources, fixtures, generated artifacts, and
  runtime entry points.
- Reproduce the known dangerous cases: missing franchise, negative money,
  Article 8 actual loss below correspondence, zero-vs-missing, and total-loss
  settlement without threshold evidence.
- Define the permitted use statement and fail-closed response contract.

Implementation:

- Enforce the claim schema before `classify`, `calc`, and `json` execution.
- Add branch-specific required-field checks and financial-domain invariants.
- Block on missing policy economics instead of substituting zero.
- Correct Article 8 to respect actual loss, correspondence, and policy caps.
- Return non-zero CLI exit status for invalid or guard-violating requests.
- Add CI, test dependencies, issue templates, and repository governance files.

Exit gate:

- Every Phase 0 regression in `docs/VALIDATION_GATES.md` passes.
- `validate`, all fixtures, and the full pytest suite pass in clean CI.
- No blocking uncertainty can coexist with a single payable.
- Invalid money, units, booleans, branches, or required evidence are refused.

Next-phase preparation:

- Freeze a baseline tag and export the validation output as a release artifact.
- Assign an owner and reviewer for every source family in Phase 1.

Issues: `P0-01` through `P0-06`.

### Phase 1 — Authority investigation and temporal provenance

**Goal:** prove which authority applies to a claim on a given event and policy
date, and ensure every executable dependency contributes to provenance and
confidence.

Investigation:

- Revalidate Regulation 53, the 1395 compulsory insurance law, the Article 8
  instruction and amendment, relevant Central Insurance circulars, and annual
  parameters against primary or authoritative official copies.
- Record promulgation, effective, superseded, and applicability dates.
- Identify policy-wording and insurer-procedure topics that law intentionally
  leaves configurable.
- Review all current `PRIMARY` classifications; a third-party host is a mirror,
  not a primary publishing authority.

Implementation:

- Introduce an effective-dated regulatory and policy snapshot selected by event
  date and policy version.
- Give every executable node a validated provenance envelope, or explicitly
  define it as a derived node with dependencies.
- Include annual parameters, classifier decisions, assessor inputs, policy
  terms, and live uncertainties in result provenance/confidence.
- Add content hashes and retrieval metadata to source records.

Exit gate:

- Every amount-affecting rule has an official source or is marked blocking.
- Historical test cases select the correct rule and annual parameter version.
- Revalidation deadlines fail CI when overdue for release-critical sources.
- The source audit has two-person approval.

Next-phase preparation:

- Publish the approved authority-to-operator matrix for Phase 2.
- Freeze the vocabulary for evidence, valuations, policy versions, and
  uncertainty resolution artifacts.

Issues: `P1-01` through `P1-05`.

### Phase 2 — Claim taxonomy and graph-driven calculation

**Goal:** make the declared ontology and operator order the authoritative
execution configuration, with code/data drift made impossible or observable.

Investigation:

- Map every canonical branch and alias to coverage gates, required evidence,
  operators, uncertainties, caps, and permitted terminal states.
- Identify predicates currently implemented through text keywords or trusted
  declared branches and replace them with controlled evidence fields.
- Decide whether the graph is interpreted at runtime or compiled into a signed
  executable plan.

Implementation:

- Create a branch execution-plan compiler/interpreter from graph nodes.
- Verify every configured operator and guard is invoked in the applicable path.
- Reject declared-branch/evidence contradictions or require a recorded adjuster
  override with reason and identity.
- Add graph/code parity, mutation, property, and boundary tests.

Exit gate:

- Changing operator order in an isolated test graph changes the scenario result.
- Removing a required guard or operator makes validation/CI fail.
- All seven branches and aliases pass the branch matrix.
- No branch relies on uncontrolled free-text classification.

Delivered toward this phase (2026-09-25):

- The **case-review layer** (`knowledge/review_procedure.json`,
  `knowledge/parameter_slots.json`, `knowledge/evidence_items.json`,
  `knowledge/case_tiers.json`, `src/iran_auto_claim/review.py`) supplies the
  controlled evidence fields that replace keyword-only predicates: 11 gate-ordered
  stages, 58 questions with closed answer vocabularies, 36 parameter slots declaring
  who may supply each value and what absence means, and 24 evidence items tagged with
  the class of authority that demands them.
- Branch `required_evidence` is now referential data validated against `EvidenceItem`
  nodes instead of a free-text hint, and the ladder in `knowledge/case_tiers.json`
  states the permitted terminal state per rung (`claim.py ladder`).
- Remaining for this phase: the branch execution-plan compiler, graph/code parity
  proofs that a mutated graph changes execution, and replacing the last keyword
  predicates in `classify.py` with the evidence fields this layer now produces.

Next-phase preparation:

- Publish the adapter interface and calibration worksheet template.
- Select the first insurer/product/version for Phase 3.

Issues: `P2-01` through `P2-04`.

### Phase 3 — Insurer and assessor calibration

**Goal:** replace missing contractual economics with versioned, reviewable
insurer adapters and assessor inputs without letting them override controlling
law.

Acquisition order:

1. Franchise schedules by insurer, product, coverage, claim sequence, and policy
   version (`U02`).
2. Underinsured partial-loss worksheets that resolve operator order (`U01`).
3. Standalone-glass endorsement wording (`U03`, `U11`).
4. Article 8 component correspondence catalogues/reference sets (`U06`, `U07`).
5. Battery/tire interaction and rescue denominator (`U04`, `U05`).

Implementation:

- Define signed `InsurerProcedure`, `PolicyVersion`, and `AssessorValuation`
  packages with source, effective dates, scope, and confidence.
- Prevent an adapter from overriding statute/regulation-controlled behavior.
- Require a documented fallback: scenario set, human assessment, or refusal.

Exit gate:

- Each adapter is reconciled against at least five representative worksheets,
  including one boundary and one missing-term case.
- Calculated amounts match approved worksheets to the documented IRR rounding
  rule; unexplained differences are zero.
- No adapter passes when its source version is absent or outside its effective
  interval.

Next-phase preparation:

- Assemble anonymized golden cases and independent expected decisions for
  Phase 4.

Issues: `P3-01` through `P3-06`.

### Phase 4 — Independent validation and governed knowledge expansion

**Goal:** move from self-consistency tests to independent evidence that the
model agrees with qualified human decisions and remains safe under change.

Implementation:

- Build an anonymized golden corpus reviewed independently by claims and legal
  specialists.
- Add exact audit snapshots, stable rounding, deterministic serialization, and
  reproducible calculation identifiers.
- Make ingestion atomic and locked; recursively detect semantic conflicts;
  validate duplicates, references, dates, and migrations before commit.
- Complete a privacy/security threat model and redaction policy.

Exit gate:

- Minimum branch-specific cases in `docs/VALIDATION_GATES.md` are satisfied.
- Deterministic cases match approved results exactly after documented rounding.
- Every uncertain case refuses or returns the approved scenario set.
- Knowledge migration failure leaves the previous graph fully intact.
- No raw personal data is present in the repository or CI artifacts.

Next-phase preparation:

- Approve the API contract, reviewer roles, pilot cohort, and rollback plan.

Issues: `P4-01` through `P4-04`.

### Phase 5 — Human-in-the-loop private pilot

**Goal:** operate the engine in shadow mode with mandatory review, observable
decisions, and no autonomous payment authority.

Implementation:

- Add an authenticated private API and adjuster review queue.
- Show inputs, classifications, formulas, sources, confidence components,
  uncertainties, overrides, and result versions.
- Add immutable audit events, monitoring, rate limits, backups, and rollback.
- Run a shadow pilot against real claims without controlling payment.

Exit gate:

- At least 100 representative shadow claims are dual-reviewed.
- Zero silent single-payable results occur with blocking uncertainty.
- All disagreements are categorized; no unexplained material amount variance
  remains open.
- Security, backup/restore, rollback, and incident-response exercises pass.

Next-phase preparation:

- Assemble the certification dossier and define the narrowly authorized release
  scope.

Issues: `P5-01`, `P5-02`.

### Phase 6 — Certification and controlled release

**Goal:** release only the branches, insurers, products, and policy versions
proven by the validation dossier.

Exit gate:

- Legal, claims, engineering, security, and product owners sign the release.
- Supported and unsupported scopes are machine-readable and user-visible.
- Every release pins source, graph, code, adapter, and annual-parameter versions.
- Rollback and emergency rule-disable procedures are tested.

GraphRAG or other generative retrieval begins only after this gate. It may
explain or retrieve approved nodes; it must never calculate outside the
deterministic engine.

Issues: `P6-01`, `P6-02`.

## Commit and release discipline

Use small, reviewable commits aligned to issue IDs:

```text
docs(P0-06): establish roadmap and validation gates
test(P0-03): reproduce missing-franchise false precision
fix(P0-03): block settlement when franchise terms are missing
test(P0-04): cover Article 8 actual-loss ceilings
fix(P0-04): apply actual, correspondence, and policy caps
```

For every phase:

1. Commit the failing validation case.
2. Commit the implementation or knowledge change.
3. Commit source/provenance migrations separately from formula changes.
4. Run the complete gate; record commands and results in the PR.
5. Merge only after required domain and engineering review.
6. Tag accepted phase baselines as `phase-N-accepted.YYYYMMDD`.

Do not combine unrelated legal-source changes and calculation changes in one
commit. A knowledge supersession must leave an explicit migration trail.

## Definition of done for an issue

An issue is complete only when:

- Its acceptance criteria and listed validation cases pass.
- Code, graph, schema, documentation, and examples agree.
- New or changed amount-affecting behavior has a source and a regression test.
- Uncertainty and failure behavior are tested, not only the happy path.
- The full repository gate is green.
- Review evidence and any residual risk are recorded in the PR.
