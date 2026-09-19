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
