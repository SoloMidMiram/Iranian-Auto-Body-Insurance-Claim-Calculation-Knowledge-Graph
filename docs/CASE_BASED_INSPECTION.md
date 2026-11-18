# Case-based body-model inspection — PR #56 against independent reference outcomes

Repository: `SoloMidMiram/Iranian-Auto-Body-Insurance-Claim-Calculation-Knowledge-Graph`
Inspection date: 12 October 2026. Monetary unit: IRR unless stated.
Purpose: compare the deterministic model against independently derived, source-supported
reference outcomes. **This is an inspection, not implementation, approval or release.**
No runtime rule, schema, knowledge node, test marker, remote issue, PR or review comment
was changed by this work. **Release remains BLOCKED.**

“Independent” here means independent of engine output and implementation arithmetic. The legal
predicate inputs were traced through the repository's source register and recorded clause text;
they were not independently authenticated against a complete official amendment history. That
authority limitation is explicit in §2 and prevents this inspection from serving as domain
approval.

---

## 1. Pinned model under inspection

### 1.1 Revisions, tree objects and PR status

| Role | Branch | Commit | Tree | Status |
|---|---|---|---|---|
| **Proposed head under review** (PR #56) | `fix/pr03-repair-rescue` | `6f655f178379c182947b28e29ff0fc7153d8e522` | `14b8e77c97abd4590f5eec4d72f852021fd1e9ae` | OPEN, `mergeable=MERGEABLE`, `mergeStateStatus=CLEAN`, **no review decision recorded**, CI `repository-gate` SUCCESS ×2 (completed 2026-10-12T01:45Z) |
| **Accepted integration baseline** (PR #56's base) | `fix/body-runtime-blockers` | `a8a20472172fbb5700adcf7c52df639830fbd9f2` | `150091f01bbff30495abc29094a3e5a5e79070f3` | PR #50 + #54 + #55 merged (Stage-0 baseline, PR-01, PR-02) |
| main (integration target of PR #48) | `main` | `37b1765af89121bf04ef590f729f1cd861e3c254` | `eb6e49e79b4906ae5bd00a49b187057f286624f3` | docs merge #47 only; **PR #48 is still OPEN and was not treated as accepted** |

`git merge-base --is-ancestor a8a2047 6f655f1` → yes; `git rev-list --count a8a2047..6f655f1` → **3**
(`1d535e5`, `99bdb4d`, `6f655f1`). The baseline commit and tree match the parent declared in the
PR record, so the proposed delta is exactly PR-03 and nothing else.

A **proposed head is not an accepted baseline.** Every row below labels which revision a behaviour
belongs to. Two things exist only at the proposed head: the IA-03/IA-04 corrections and the
unresolved-rescue payment gate (§7, §8).

### 1.2 Isolation and working-tree status

The interactive working copy was already dirty and its local integration branch had diverged from
the remote branch. It was not used as model evidence, and its unrelated modified and untracked
files were not staged, reverted or rewritten.

All model execution used two detached or dedicated isolated worktrees pinned to the full revisions
in §1.1: one at the proposed PR head and one at the accepted integration baseline. Both execution
worktrees were clean before and after the inspection. The case inputs were read from the same
canonical `cases/inspection-*.json` corpus, whose SHA-256 digests are recorded in Appendix A.
Running the full mutation probe did not modify `docs/MUTATION_REPORT.md`, confirming that the
checked-in report matched the fresh run.

### 1.3 Instructions and validation documentation read

`README.md`, `CONTRIBUTING.md`, `SECURITY.md`, `docs/VALIDATION_GATES.md`, `docs/ROADMAP.md`,
`docs/RESEARCH_REPORT_MODEL_VALIDATION.md`, `docs/MUTATION_REPORT.md`, `docs/PR03_REPAIR_RESCUE.md`,
`.github/PULL_REQUEST_TEMPLATE.md`, `.github/ISSUE_TEMPLATE/calculation-defect.yml`,
`tests/independent-body-model-audit-a159aaed.md` (the IA register, tracked since PR #50),
`schema/review-answers.schema.json`, `schema/claim-case.schema.json`, `knowledge/*.json`.

Applicable constraints taken as binding for this inspection: a green suite is not a legal
conclusion; an amount-affecting change needs engineering **and** domain review; no real names,
identifiers, policy numbers, plates or unredacted documents may be committed; mirrors must not be
presented as publishing authority.

### 1.4 Supported Python version

| Revision | `requires-python` | CI matrix |
|---|---|---|
| baseline `a8a2047` | `>=3.10` | 3.10 / 3.11 / 3.12 / 3.13 |
| **proposed `6f655f1`** | **`>=3.11,<3.12`** | **one 3.11 job + a new `sync_customer_faq.py` step** |

The narrowing is part of PR #56 and is **outside** its stated IA-03/IA-04 scope. It was verified
from the files at each revision, not from the PR prose.

### 1.5 Interpreter-bound environment and gate evidence

Fresh validation used CPython **3.11.15** and interpreter-bound pip **24.0** from an isolated
virtual environment. This satisfies the proposed `>=3.11,<3.12` contract. The supported CLI was
executed from each source checkout, and pytest used that same interpreter. A newly created empty
3.11 environment lacked pytest and was not counted as gate evidence; the complete runs below used
the established PR-03 validation environment with the declared test dependency installed.

Gate runs, at each pinned revision, from that revision's own venv:

| Gate | baseline `a8a2047` | proposed `6f655f1` |
|---|---|---|
| `python -m compileall -q claim.py src scripts` | exit 0 | exit 0 |
| `python claim.py validate` | exit 0 — `knowledge graph OK`; **22** body-authority findings; **48** source-metadata findings; 273 nodes; 10 blocking uncertainties; 13 contradictions | identical counts |
| `python claim.py fixtures` | `50/50 fixtures passed` | `50/50 fixtures passed` |
| `python -m pytest` | exit 0 — **587 passed, 6 xfailed** (593 tests) | exit 0 — **609 passed, 4 xfailed** (613 tests) |
| `python scripts/run_mutation_gate.py --check-report` | not run at baseline | exit 0 — "mutation report is current" |
| `python scripts/run_mutation_gate.py` (full) | not run | **28/28 killed (100.0%)**, required score 90% |
| `python scripts/sync_review_docs.py` | not run | exit 0 — "documentation blocks are current" |
| `python scripts/sync_customer_faq.py` | not present at baseline | exit 0 — "customer FAQ data and documentation are current" |
| `python scripts/sync_github_issues.py --repo …` | not run | exit 0 — valid dry run: 8 milestones, 11 labels, 29 issues |

Expected failures, identified by name (not by count):

```text
baseline  a8a2047 : IA-03, IA-04, IA-05, IA-08, IA-14[disposition-absent], IA-14[retained-value-absent]
proposed  6f655f1 : IA-05, IA-08, IA-14[disposition-absent], IA-14[retained-value-absent]
```

The PR's claimed gate numbers reproduce exactly (587/6 at the parent, 609/4 at head,
50/50 fixtures, 22/48 findings, 28/28 mutants). Nothing in this inspection contradicts them.

---

## 2. Reference sources, their authority class and their limits

Expectations in §4/§5 were derived from the instruments below, as recorded in
`knowledge/sources.json` and `knowledge/rules.json`, and from arithmetic done independently of the
engine (§3). Publisher, instrument, locator, version/effective date, applicability, retrieval
status and integrity evidence are stated per source. **All 16 sources carry `content_hash: null`,
incomplete effective intervals and no revalidation date** — which is exactly what
`claim.py validate` reports as 48 source-metadata findings. There is therefore **no integrity
evidence for any source in the register**, and structural validity is not authority completeness.

| Source id | Publisher / authority | Instrument | Locator / clause | Version & effective applicability | Register tier | Retrieval status | Integrity evidence |
|---|---|---|---|---|---|---|---|
| `SRC_CENTINSUR_CAR_INSURANCE_COMPILATION` | Central Insurance of Iran (Bimeh Markazi) | Motor-insurance compilation PDF (Regulation 53 + TPL law 1395 + circulars) | `centinsur.ir/_douranportal/documents/2277/carinsurance.pdf` — compilation-level, no page locator | not dated in register | PRIMARY (official compilation) | read 2026-09-18; re-read 2026-10-09 by the audit (corroborates strict threshold incl. rescue, replacement-only depreciation, distinct theft clauses, salvage-before-franchise, no second indemnity) | **none (hash null)** |
| `SRC_IRANINSURANCE_REG53` | High Insurance Council | Regulation 53 | `iraninsurance.ir/fa/w/آیین‌نامه-شماره-53-5` — full text | effective 1384-12-09; `effective_until` null | PRIMARY (official insurer copy) | register records "direct open timed out"; audit 2026-10-09 records the same | none |
| `SRC_REG53_MIRROR` | High Insurance Council text, mirrored | Regulation 53 | `gostareshins.com/…آیین‌نامه-شماره-53-بیمه-بدنه…` — Arts 3–6, 10–14, 19–21 | not dated; mirror of 1384 text | **PRIMARY_MIRROR** | read | none — and `validate` flags "remains PRIMARY_MIRROR; no reviewer" for 6 operators |
| `SRC_REG53_MIRROR_DAVOUDABADI` | HIC text, practitioner mirror | Regulation 53 Arts 1–24 | `davoudabadi.ir/page/91785462` | not dated | PRIMARY_MIRROR (corroboration only) | read 2026-09-25 | none |
| `SRC_IRANINSURANCE_BODY_GENERAL_CONDITIONS` | HIC via Iran Insurance Co. | Regulation 53 general conditions, Arts 1–24 | `iraninsurance.ir/fa/w/شرایط-عمومی-بیمه-بدنه-اتومبیل-2` | effective 1384-12-09 | PRIMARY_MIRROR | opened and read 2026-09-25 | none |
| `SRC_CIC_CIRCULAR_1400_401_146850` | Central Insurance | Circular 1400/401/146850 (salvage then franchise) | same compilation PDF, circular section | effective 1400-09-13 | PRIMARY | read (inside compilation) | none; **no reviewer** |
| `SRC_CIC_CIRCULAR_1404_06_10` | Central Insurance | Circular 1404/06/10 (non-conventional Art 8 excess) | `centinsur.ir/fa-IR/Portal/1/news/view/15628/5736/Staging` | effective 1404-06-10 | PRIMARY | read | none |
| `SRC_HIC_ARTICLE8_INSTRUCTION` | High Insurance Council | Art 8 implementation instruction | `davoudabadi.ir/page/90973652` | effective 1396-05-29, amended 1398-06-13 | PRIMARY (single article, hosted) | read | none |
| `SRC_TPL_LAW_1395` | Islamic Consultative Assembly | Compulsory TPL Law 1395, Art 8 | reproduction inside the compilation PDF | not dated | PRIMARY (statute as reproduced) | read | none |
| `SRC_IRANINSURANCE_BODY_ENDORSEMENT_TERMS` | Iran Insurance Co. | Private conditions / additional coverages (glass, parts theft, loss of use) | endorsement clauses page | **no version, no effective date** | POLICY_SPECIFIC (one company's wording) | read 2026-09-25 | none |
| `SRC_IRANINSURANCE_BODY_FRANCHISE_SCHEDULE` | Iran Insurance Co. | Premium and franchise page | `…حق-بیمه-و-فرانشیز-بیمه-بدنه…` | **no printed version; some amounts look legacy** | INSURER_PUBLISHED | read 2026-09-25; marked `requires_primary_revalidation` | none |
| `SRC_BIMEDAY_BODY_CLAIM_PROCEDURE` | Day (Bimeh Day) | Claims documents checklist; states a 60-day theft count | `bimeday.ir/…` | undated | INSURER_PUBLISHED | read 2026-09-25 | none |
| `SRC_IRANINSURANCE_CLAIMS_FAQ` | Iran Insurance Co. | Public FAQ "آنالیز خسارت پرداختی" | `iraninsurance.ir/fa/w/…` | undated | SECONDARY_CURRENT | register: page timed out, indexed content only | none |
| `SRC_1405_DIYAH_SECONDARY` | Bimeh.com | 1405 diyah reporting | `bimeh.com` (site root, no article) | 1405 annual | SECONDARY_CURRENT (EDUCATIONAL class) | read 2026-09-18; `requires_primary_revalidation` | none |
| `SRC_HIC_DIMINUTION_INSTRUCTION_1403` | HIC via ekhtebar.ir | Diminution-of-value instruction | `ekhtebar.ir/…کسر-قیمت…` | approved 1403-08-02, effective 1403-10-01 (unverified) | SECONDARY_CURRENT (single unofficial mirror) | read 2026-09-25 | none |
| `SRC_INSURER_MANUAL_PENDING` | **not obtained** | insurer manuals / franchise schedules (Asia, Pasargad, Parsian…) | `n/a` | `n/a` | **UNAVAILABLE / NOT_RETRIEVED** | never retrieved | none |

### 2.1 What this register cannot support

`SRC_INSURER_MANUAL_PENDING` is the declared `resolved_by` for **U01, U02, U03, U04, U05, U06, U07
and U11** — i.e. the Article 10 order, every franchise schedule, glass endorsement economics, the
battery/tyre interaction, the rescue denominator and the Article 8 catalogue. A source that is
`NOT_RETRIEVED` cannot resolve anything. Consequently:

- **No real insurer example could be authored for this dossier.** The repository holds no dated,
  versioned insurer worksheet, no franchise schedule with an effective date, and no endorsement
  wording tied to a policy version — and this inspection did not obtain one. The 2026-10-09 audit
  independently recorded `centinsur.ir` 403 and `iraninsurance.ir` timeouts. Per the brief,
  **nothing was invented**: no insurer worksheet, no
  policy clause, no official example and no expected final amount was fabricated. Readiness per
  document type is recorded in §11.
- Amount-affecting readings that rest on a mirror alone (replacement-only depreciation, the 20%
  rescue ceiling, the strict `> 75%` test, the 5-year/5%/25% schedule) are corroborated by the
  Central Insurance compilation but **not** by an official original with a complete amendment
  history. They are usable as reference inputs, not as certified law.
- Two rules are explicitly non-primary in their own envelopes:
  `REG53_ART19_TOTAL_LOSS_NO_DOUBLE_UNDERINSURANCE` (`derivation: IMPLEMENTATION_INFERENCE`,
  confidence 0.90) and `REG53_ART19_YEAR_INDEX_INTERPRETATION` (`IMPLEMENTATION_INTERPRETATION`,
  confidence 0.90, caveat "must be confirmed against claims-department practice"). Where a case
  depends on them, §7 says so rather than presenting the result as settled.

---

## 3. How the reference outcomes were derived

`docs/CASE_BASED_INSPECTION.md` §4/§5 expectations were computed **before** any case was executed.
The standalone Decimal arithmetic used only the clause formulas below and imported nothing from
`iran_auto_claim`:

```text
year index            i = claim_year − production_year + 1
replacement ageing    rate = 0 if i < 5 else min(0.25, 0.05 × (i − 4))        [Art 19]
depreciable scope     replaced parts except GLASS / LAMP_GLASS                [Art 19, Art 19 glass exemption]
special cap           min(assessed, 0.50 × new_price)                         [Art 3]
partial base          fair labour + current replacement-part prices,
                      then depreciation, then franchise, then add rescue      [Art 19(b)]
underinsurance        ratio = min(1, insured_sum / market_value_at_event)     [Art 20 note 2]
rescue ceiling        min(actual, 0.20 × total_damage)  — denominator unnamed [Art rescue clause]
total-loss test       (covered repair+replacement + rescue) > 0.75 × market   [Art 19, strict]
total-loss base       min(market, insured); never multiplied by the ratio
                      again; capped at insured                                [Art 19 + inference]
salvage order         franchise computed after probable salvage is deducted   [Circular 1400/401/146850]
title route           if title transfers, salvage value is not also deducted  [Art 19]
```

The clause *inputs* (10% franchise on a named base, first-claim sequence, market and insured sums,
component categories, production year, evidenced rescue) are synthetic controlled facts each case
declares. They are labelled `SYNTHETIC_INSURER` and `synthetic controlled policy term`; they are
not attributed to an actual insurer, product, worksheet or policy clause. Where the sources do not
choose between alternatives (Article 10 order, battery/tyre interaction, rescue denominator,
disposition semantics, theft clock anchor, premium-ratio mechanism), **the reference outcome is
"no single amount"**, not a guess. No expected value in §4/§5 was copied from engine output, from
`fixtures/cases.json`, or from a mutation probe.

This is an independent arithmetic oracle, not an independently authenticated legal oracle. Clause
selection inherits the incomplete integrity and effective-date evidence in §2; cases relying on an
interpretation or inference are labelled accordingly.

Case inputs follow the repository's conventions: flat `cases/*.json` review-answer files with
`claim_id` / `unit: IRR` / `note` / `evidence_present` / `answers`, question ids inside the closed
`Q-S\d+-\d\d` vocabulary, closed choice tokens, non-negative integer IRR money answers, and one
material fact varied per file. Digests are recorded in Appendix A, and the committed read-only
runner validates and executes the corpus without generating or rewriting it.

---

## 4. Reference case matrix — expectations recorded before execution

**F1 repair-only versus replacement depreciation** (market = insured = 8,000,000,000; production
1399; event 1404 ⇒ index 6 ⇒ 10%; labour 400,000,000; rescue 100,000,000; franchise 10%
`AFTER_DEPRECIATION`, sourced `POLICY` schedule 1404)

| Case | Varied fact | Reference outcome |
|---|---|---|
| C13D-REPLACEMENT-CONTROL | replaced panel 1,200,000,000 | PARTIAL_DAMAGE; COMPUTE; depreciation **120,000,000**; after-depreciation 1,480,000,000; franchise 148,000,000; payable **1,432,000,000** |
| C13A-REPAIR-ONLY | category `REPAIR_ONLY` | PARTIAL_DAMAGE; COMPUTE; depreciation **0**; after-dep 1,600,000,000; franchise 160,000,000; payable **1,540,000,000** |
| C13B-REPLACED-BUT-FLAG-FALSE | `OTHER_REPLACEMENT_PART` + `requires_replacement=false` | same as C13A: depreciation 0; payable **1,540,000,000** |
| C13C-REPAIR-ONLY-FLAG-TRUE | `REPAIR_ONLY` + flag true (contradiction) | **no authorization**; structured input refusal; no amount |
| C21MIX-FOUR-KINDS | replaced panel + `GLASS` 450m + `LAMP_GLASS` 250m + `REPAIR_ONLY` 300m + labour | assessed 2,600,000,000; depreciation **120,000,000** (panel only); after-dep 2,480,000,000; franchise 248,000,000; payable **2,332,000,000** |

**F2 battery/tyre interaction (U04)** — production 1395 ⇒ index 10 ⇒ 25%; battery assessed
120,000,000, new price 200,000,000 ⇒ cap 100,000,000. No universal order is asserted anywhere, so
candidates are 75,000,000 / 90,000,000 / 100,000,000 (kept amounts) and the reference for a bare
mode token is *no single amount*:

| Case | Q-S8-02 | Reference |
|---|---|---|
| C31U04-UNRESOLVED | `UNRESOLVED` | no single payable; three named candidates surfaced |
| C32/C33/C34 | `CAP_THEN_DEPRECIATE` / `DEPRECIATE_THEN_CAP` / `CAP_ONLY` | still no single payable — a questionnaire token is not an authority artifact (RQ-09 unresolved). An amount would be 67,500,000 / 81,000,000 / 90,000,000 (kept − 10% franchise) **only if** the adjuster choice were authority |
| C35Q404-BATTERY-NEW-PRICE | as C31 + dedicated `Q-S4-04` new-price answer | `PS_PART_NEW_PRICE` must bind so the cap and the mode become reachable |

**F3 strict 75% threshold** — market = insured = 10,000; production 1404 (index 1 ⇒ 0%); labour 0;
one replaced component 7,400; franchise 10% `AFTER_DEPRECIATION` ⇒ franchise 740:

| Case | rescue | numerator | Reference |
|---|---|---|---|
| C41-BELOW-7499 | 99 | 7,499 = 74.99% | PARTIAL_DAMAGE; payable **6,759** |
| C42-AT-7500 | 100 | 7,500 = exactly 75% | PARTIAL_DAMAGE (strict test); payable **6,760** |
| C43-ABOVE-7501 | 101 | 7,501 = 75.01% | **TOTAL_LOSS**; no settlement evidence in the file ⇒ no amount |
| C44-RESCUE-CROSSES-7600 | 200 | 7,600 = 76% | **TOTAL_LOSS**; no amount (the frozen IA-04 counterexample) |
| C45-RESCUE-OMITTED | omitted | unknown | **no amount** — absence is not zero; must never pay more than C44 |
| C46-RESCUE-EXPLICIT-ZERO | 0 | 7,400 = 74% | PARTIAL_DAMAGE; payable **6,660** |
| C47-AGGREGATE-ONLY-RESCUE | aggregate 7,400 + rescue 200 | 7,600 = 76% | TOTAL_LOSS with rescue counted **exactly once**; no amount without disposition/salvage evidence |
| C48-ASSESSED-DEPRECIATION-FIGURE | `Q-S4-05 = ASSESSED_FIGURE` | — | the assessor's own figure has no money channel (choice-valued question bound to a money slot); if the engine silently uses `COMPUTED_PER_PART`, the declared route is not honoured |

**F4 capital examples** — C71/C72 from the T3 shape (market 8,000,000,000 / insured 6,000,000,000 ⇒
ratio 0.75; door 1,500,000,000 replaced at index 7 ⇒ 15% ⇒ depreciation 225,000,000; exempt
windscreen 450,000,000; labour 300,000,000; rescue 80,000,000):

| Case | Reference |
|---|---|
| C71-UNDERINSURED-UNRESOLVED | after-dep 2,025,000,000; franchise 202,500,000; **two** scenarios: ratio-then-franchise **1,396,250,000**, franchise-then-ratio **1,446,875,000**; no single payable |
| C72-UNDERINSURED-ORDER-LOCKED | still no single payable — a bare `Q-S8-01` token is not the worksheet/circular that U01 declares as its resolver |
| C73-OVERINSURED | insured 12,000 > market 10,000 ⇒ ratio capped at 1 ⇒ identical to C42: **6,760** |
| C74-UNDERINSURED-TOTAL-LOSS | base `min(8,000m, 6,000m)` = 6,000,000,000; franchise 600,000,000; payable **5,400,000,000**; the ratio is **not** applied a second time (inference-based, §2.1) |

**F5 total-loss title and disposition completeness** — physical total loss: market = insured =
8,000,000,000, replaced component 6,500,000,000, rescue 0 ⇒ 81.25% > 75%; salvage 1,000,000,000 where
recorded; franchise 10%:

| Case | Facts | Reference |
|---|---|---|
| C61-TITLE-NOT-TRANSFERRED | `INSURER_TAKES_TITLE`, `Q-S4-06=NOT_TRANSFERRED`, salvage valued, transfer proof also in file | **no amount** — an intended disposition is not a completed transfer, and salvage must not be waived without title |
| C62-TITLE-TRANSFERRED | same but `TRANSFERRED` + proof | base 8,000,000,000; salvage deducted **0**; franchise 800,000,000; payable **7,200,000,000** |
| C63-RETAINS-AFTER-SALVAGE | `INSURED_RETAINS`, salvage 1,000,000,000, franchise base `AFTER_SALVAGE` | after-salvage 7,000,000,000; franchise 700,000,000; payable **6,300,000,000** (circular order) |
| C64-RETAINS-SETTLEMENT-BASE | as C63, pre-salvage base | **blocked pending authority** — a pre-salvage base would pay 6,200,000,000, i.e. 100,000,000 less than the circular-supported order; RQ-03 has no artifact |
| C65-RETAINS-SALVAGE-MISSING | `INSURED_RETAINS`, no salvage value, no valuation document | **no amount** — absent salvage is not zero |
| C66-DISPOSITION-UNRESOLVED | `UNRESOLVED` + valuation on file | **no amount** (U12 blocking; the two routes differ by 1,000,000,000) |
| C67-DISPOSITION-NOT-APPLICABLE | `NOT_APPLICABLE` on a physically total loss | **blocked** — whether `NOT_APPLICABLE` can ever be valid here is open (RQ-07) |

**F6 unresolved premium and policy facts**: C81 (`Q-S3-07=YES` + underwriting record) → no amount;
the premium-ratio operator does not exist and the capital ratio must not substitute. C82 (`UNKNOWN`)
→ no authorization. C83 (`Q-S0-06=INSTALMENT_OVERDUE`) → no amount until the consequence is sourced.
C84 (`UNKNOWN` policy state) → no authorization.

**F7 contractual authority for the rate (IA-08)**: C101 — the same 10% attributed to
`INSURER_MANUAL` with `source_reference` and `source_version` removed → **no amount**: a source-type
label is not an instrument.

**F8 containment accepted at the baseline** (must still hold at the head): C91 prior full
compensation 1,600,000,000 → no amount; C92 documented zero → 1,432,000,000; C93 `ASSERTED_ONLY`
causation → no authorization; C94 event date `1404-99-99` → structured refusal; C95 production year
1500 → structured refusal and specifically **no** amount above C13D; C96 conflicting aliases →
structured refusal; C97 late notice without excuse → no amount without an evidenced adjudication
(RQ-05); C98 released recourse → no amount without adjudication (RQ-06); C99 third-party split →
no body-only amount; C102 standalone glass on a held endorsement with no wording → no single amount
(glass franchise line, installation inclusion and valuation condition are all endorsement terms).

**F9 theft clock**: C104 (whole vehicle; occurrence 1404-04-20, declaration 1404-04-21, as-of
1404-06-18, SHAMSI, anchor selected as occurrence, title transferred; market = insured = 9,000,000,000;
franchise 20% `SETTLEMENT_BASE`) → arithmetic 9,000,000,000 − 1,800,000,000 = 7,200,000,000, **but no
payment may be authorized while the Article 19 classification clock and the Article 20
declaration-based payment clock remain a single caller-selected switch (RQ-02)**. C105 (as-of
1404-06-17 ⇒ 59 days) → pending, no amount. C106 (60 days stored, no anchor/date/calendar/source) →
no amount.

---

## 5. Engine-boundary reference expectations (internal test path)

These use the repository's own internal path (`tests/admission_shim.compute` →
`iran_auto_claim.fixtures._authorize_fixture_case` → `admission._internal_test_direct_authorize`,
`purpose` visible as `INTERNAL_TEST_DIRECT`). They exist to inspect **containment at the
calculation boundary**; a passing internal row never stands in for a supported Review result.

| Probe | Payload fact | Reference expectation |
|---|---|---|
| INT-01 | rescue operands absent entirely | no amount: the threshold numerator is unknown |
| INT-02 | as INT-01 + documented `classification.override` (authorized/actor/reason/source/timestamp) | an override selects a branch, it does not create a missing fact ⇒ no amount |
| INT-03 | actual 200 vs explicit threshold operand 0 | conflicting operands ⇒ no amount until an accepted interpretation exists |
| INT-04 | `repair_total_includes_rescue=true` with positive rescue | double counting prevented ⇒ no amount until decomposed |
| INT-05 | omitted rescue + `rescue_omission_legacy_compatibility=true` | permitted only as an explicitly traced legacy default, never emitted by Review |
| INT-06 | actual = threshold = 2,000, declared PARTIAL_DAMAGE | evidence-derived TOTAL_LOSS ⇒ conflict, no amount |
| INT-07 | TOTAL_LOSS, market = insured = 2,000, repair 1,600, absolute franchise 100, **no salvage value, no disposition** | no amount (IA-14a) |
| INT-08 | as INT-07 with `INSURED_RETAINS` and **no salvage value** | no amount (IA-14b) |
| INT-09 | as INT-08 with salvage **explicitly 0** | a documented zero may settle; must differ from INT-08 |
| INT-10 | replaced panel 1,200m, index 6, graph as checked out | depreciation 120,000,000 |
| INT-11 | identical authorization; in-memory graph `annual_rate` 0.05 → 0.20 | behaviour must change or fail closed (IA-11) |
| INT-12 | identical authorization; in-memory graph `maximum_rate` → 0.01 | behaviour must change or fail closed (IA-11) |
| INT-13 | declared TOTAL_LOSS vs derived PARTIAL + override + **complete** operands | the documented-override route stays available |
| INT-14 | as INT-13 but **rescue omitted** (the reported bypass) | no amount — the evidence gate must outrank the override |

---

## 6. Execution record

Commands were run from each pinned worktree with the same Python 3.11.15 environment. Exit codes
below are the process exit code of the documented command. The committed read-only runner records
the revision, tree, interpreter, input digest, decision, status, amounts and traces in JSON.

```bash
# one supported Review path plus engine, machine-readable
python claim.py review cases/inspection-<case>.json --json --calc
python claim.py calc cases/inspection-<case>.json

# complete corpus; --internal adds separately labelled INTERNAL_TEST_DIRECT probes
python scripts/run_case_based_inspection.py \
  --root <pinned-worktree> \
  --cases cases \
  --internal \
  --output <report.json>
```

Exit-code contract observed (from `iran_auto_claim/cli.py`): `review --json` prints and exits **0**
for a blocked review (`calculation: null`); `review … --emit-case` and `calc`/`json` exit **1** when
no authorization is issued; input-contract refusals exit **1** with machine-readable issues.
Refusal codes observed verbatim: `contradictory_input`, `invalid_date`, `invalid_chronology`,
`conflicting_alias`.

---

## 7. Comparison — reference against observed

Columns: `reference` (independently derived) | `observed @ baseline a8a2047` | `observed @ proposed
6f655f1`. "≡" marks an exact match with the reference; "DIVERGES" marks a discrepancy.

### 7.1 Cases where the proposed head changes behaviour (all six are IA-03/IA-04)

| Case | Reference | Baseline | Proposed head | Discrepancy at baseline | Boundary |
|---|---|---|---|---|---|
| C13A-REPAIR-ONLY | dep 0; payable 1,540,000,000 | dep 120,000,000; payable **1,432,000,000** | **1,540,000,000** ≡ | 108,000,000 underpayment; repair work aged as a replaced part | `operators.eligible_part_loss` / `case` normalisation |
| C13B-FLAG-FALSE | 1,540,000,000 | **1,432,000,000** | 1,540,000,000 ≡ | same, via the boolean rather than the category | `operators.py` (replacement predicate) |
| C13C-REPAIR-ONLY-FLAG-TRUE | refusal, no amount | **accepted; COMPUTE; 1,432,000,000** | exit 1 `contradictory_input` at `answers.Q-S4-03[0].requires_replacement` ≡ | contradictory work order silently resolved | `schema_input` review validation |
| C21MIX-FOUR-KINDS | 2,332,000,000 | **2,305,000,000** (dep 150,000,000: the 300,000,000 repair-only fender was aged at 10%, franchise 245,000,000) | **2,332,000,000** ≡ | 27,000,000 underpayment in a realistic mixed file | `operators` / component normalisation |
| C43-ABOVE-7501 | TOTAL_LOSS, no amount | **PARTIAL_DAMAGE; payable 6,761** | INSUFFICIENT_INFORMATION, branch TOTAL_LOSS, no amount ≡ | 0.01% crossing silently stayed partial and paid | `review` rescue emission → `classify`/`operators.is_total_loss` |
| C44-RESCUE-CROSSES-7600 | TOTAL_LOSS, no amount | **PARTIAL_DAMAGE; payable 6,860** (the frozen IA-04 figure) | INSUFFICIENT_INFORMATION, TOTAL_LOSS, no amount ≡ | rescue absent from the numerator; branch mis-set and paid | same |

### 7.2 Cases where both revisions already agree with the reference

| Case | Reference | Observed (both) | Boundary |
|---|---|---|---|
| C13D-REPLACEMENT-CONTROL | dep 120,000,000; payable 1,432,000,000 | 1,432,000,000 ≡ | operators/engine |
| C41 / C42 / C46 | 6,759 / 6,760 / 6,660 | 6,759 / 6,760 / 6,660 ≡ (C42 confirms equality is **not** total) | `operators.is_total_loss` strict compare |
| C45-RESCUE-OMITTED | no amount | INSUFFICIENT_INFORMATION, no amount ≡ | Review open-question gate |
| C47-AGGREGATE-ONLY | TOTAL_LOSS, rescue once, no amount | TOTAL_LOSS derived from 7,600; INSUFFICIENT_INFORMATION ≡ | `review` aggregate binding |
| C63-RETAINS-AFTER-SALVAGE | 6,300,000,000 | 6,300,000,000 ≡ (`SALVAGE_DEDUCTED_BEFORE_FRANCHISE`) | `_settle_total_loss` + circular order |
| C71-UNDERINSURED | two scenarios 1,396,250,000 / 1,446,875,000, no single payable | `ORDER_UNRESOLVED`, scenarios exactly those two ≡ | `branches.json` U01 scenarios |
| C72-ORDER-LOCKED | no single amount | `AUTHORIZED_UNCERTAINTY_UNRESOLVED`, payable `None`, `order_used=AFTER_DEPRECIATION_BEFORE_FRANCHISE` ≡ (see F-06) | admission/`_reconcile_authorization_uncertainties` |
| C73-OVERINSURED | 6,760 (ratio capped at 1) | 6,760 ≡ | `operators.underinsurance_ratio` |
| C74-UNDERINSURED-TOTAL-LOSS | 5,400,000,000, no second ratio application | 5,400,000,000 ≡ | `min(market,insured)` + `DO_NOT_APPLY_RATIO_TWICE` (inference-based) |
| C81/C82/C83/C84 | no amount / no authorization | all INSUFFICIENT_INFORMATION, no calculation ≡ | S0 hard gates, U15, `blocking_conditions` |
| C91–C96, C99, C102, C105, C106 | as §4 F8/F9 | match ≡ (C91 `PRIOR_COMPENSATION_SETTLEMENT_UNSUPPORTED`; C93 `COVERED_PERIL_CAUSATION_NOT_ESTABLISHED`; C94 `invalid_date` ×2; C95 `invalid_chronology`; C96 `conflicting_alias`; C99 routed THIRD_PARTY_FINANCIAL then blocked on Q-S8-05; C105 `PENDING_60_DAY_CRITERION`; C106 U13 live) | schema/review admission |
| C31–C35 (fail-closed half) | no single payable | `BATTERY_TIRE_INTERACTION_UNRESOLVED`, `candidate_scenarios=[CAP_THEN_DEPRECIATE, DEPRECIATE_THEN_CAP, CAP_ONLY]`, no universal order chosen ≡ | operators + U04 liveness |

### 7.3 Cases where the model diverges from the reference at **both** revisions

| Case | Reference | Observed (both revisions) | Discrepancy | Disposition |
|---|---|---|---|---|
| **C61 vs C62** | C61 no amount; C62 7,200,000,000 | **both pay 7,200,000,000**; identical `settlement_base 8,000,000,000`, `base_after_salvage 8,000,000,000`, `franchise 800,000,000`, label `DO_NOT_DEDUCT_SALVAGE_AND_TRANSFER_IT` | `vehicle.title_transferred` is not read on the physical insurer-title route; the same label is emitted for `NOT_TRANSFERRED` and `TRANSFERRED`. 900,000,000 above the salvage-supported retained route (C63): 1,000,000,000 of undeducted salvage less a 100,000,000 higher franchise | **confirmed model defect (IA-05)** |
| **C101 vs C13D** | C101 no amount | C101 pays 1,432,000,000 with `franchise_source=INSURER_MANUAL` and **no** `franchise_source_version` field emitted — the same amount as the dated policy term | an enum label is accepted as contractual authority | **confirmed model defect (IA-08)** |
| **C67** | blocked (semantics open) | pays **6,200,000,000**, field-for-field identical to C64, label `SALVAGE_DEDUCTED_BEFORE_FRANCHISE` | `NOT_APPLICABLE` behaves exactly as `INSURED_RETAINS` | unresolved interpretation (RQ-07) with a demonstrated silent equivalence |
| **C64** | blocked pending authority | pays 6,200,000,000 | a pre-salvage franchise base settles although the applicable circular orders it after salvage | unresolved authority (RQ-03 / IA-09) — not a proven defect without an applicable instrument |
| **C97 / C98** | no amount pending adjudication | pay 1,432,000,000 with only `LATE_NOTICE_REVIEW` / `SUBROGATION_IMPAIRMENT_REVIEW` labels | labels instead of decisions | unresolved (RQ-05 / RQ-06, IA-10) |
| **C104** | no authorization while the clocks are conflated | pays 7,200,000,000; trace `derived_days: 60` from `THEFT_OCCURRENCE`, label `EVIDENCE_CONFIDENCE_REDUCED` | arithmetic agrees with the reference; the **authority** for one caller-selected clock does not | unresolved legal interpretation (IA-06/RQ-02), amount not disputed |
| **C48** | declared assessor route must be honoured or refused | pays 1,432,000,000 with `depreciation_source=COMPUTED_PER_PART` | the answer that "locks" the route binds nothing (choice-valued question → money slot) and the alternative is applied silently | unsupported implementation scope (IA-13) |
| **C35** | `Q-S4-04` must bind `PS_PART_NEW_PRICE` | slot status `NOT_TRIGGERED`, value `None`; `PS_BATTERY_TIRE_INTERACTION` also `NOT_TRIGGERED` although `Q-S8-02` was answered in every battery file | the battery/tyre handoff is unreachable from a review file: no mode can ever be selected through the supported path | unsupported implementation scope (IA-13) |

### 7.4 Engine-boundary probes

| Probe | Reference | Baseline `a8a2047` | Proposed `6f655f1` | Reading |
|---|---|---|---|---|
| INT-01 | no amount | **SETTLED, payable 6,660** | `CLASSIFICATION_EVIDENCE_REQUIRED`, `classification_rescue_source=UNRESOLVED_MISSING_RESCUE`, no amount | containment is **proposed-only** |
| INT-02 | no amount (override cannot create a fact) | branch TOTAL_LOSS selected; blocked only by an unrelated franchise-base check | `CLASSIFICATION_EVIDENCE_REQUIRED`, no amount | fixed at head |
| INT-03 | no amount | **SETTLED, payable 6,860** | `CLASSIFICATION_EVIDENCE_REQUIRED` ("actual and explicit classification rescue differ…") | proposed-only |
| INT-04 | no amount until decomposed | `UNCAUGHT-InputSchemaError` (field unknown at baseline) | `CLASSIFICATION_EVIDENCE_REQUIRED` ("repair/replacement already includes rescue…") | proposed-only; see F-07 on the exception shape |
| INT-05 | explicit legacy zero only, traced | `UNCAUGHT-InputSchemaError` | SETTLED 6,660 with `classification_rescue_source=EXPLICIT_LEGACY_DEFAULT_ZERO` | the legacy channel exists **only** internally; Review never emits it (C45 blocks) |
| INT-06 | conflict, no amount | `CLASSIFICATION_CONFLICT` | `CLASSIFICATION_CONFLICT` | holds at both |
| INT-07 / 08 / 09 | no amount / no amount / zero may settle | **all three SETTLED 1,900** | **all three SETTLED 1,900** | **IA-14 preserved**: absent salvage operand, retained-with-no-value and explicit zero are indistinguishable at the engine boundary |
| INT-10 / 11 / 12 | payload change must change behaviour or fail closed | 1,432,000,000 / 1,432,000,000 / 1,432,000,000 | 1,432,000,000 / **1,432,000,000** / **1,432,000,000** | **IA-11 preserved** at the proposed head: `annual_rate 0.20` and `maximum_rate 0.01` leave `depreciation=120,000,000.00` and `depreciation_source=COMPUTED_PER_PART` |
| INT-13 | override available with complete operands | SETTLED 9,200 | SETTLED 9,200 | the legitimate override path is preserved |
| INT-14 | no amount | **SETTLED 9,000 with label `AUTHORIZED_CLASSIFICATION_OVERRIDE`** (`is_total=False` from a zero the file never supplied) | `CLASSIFICATION_EVIDENCE_REQUIRED`, no amount | reproduces and closes the bypass reported at `99bdb4d`, exactly as PR-03 claims |

---

## 8. Findings, prioritised

Priorities use the audit register's model (P0 = a supported path can issue a wrong money/eligibility
result without any new legal interpretation; P1 = depends on an unsourced authority choice; P2 =
assurance/architecture/test-integrity debt). IA ids refer to
`tests/independent-body-model-audit-a159aaed.md` as tracked at `6f655f1`.

**A. Confirmed model defects (reproduced on the supported path or the internal boundary)**

1. **F-01 / IA-05 — P0, both revisions.** Title state is inert on the physical total-loss
   insurer-title route. C61 and C62 differ only in `Q-S4-06` and pay the identical 7,200,000,000,
   while the salvage-supported retained route (C63) pays 6,300,000,000 — 900,000,000 less, of which
   1,000,000,000 is the un-deducted salvage and −100,000,000 the franchise base it changes. The XOR
   guard label `DO_NOT_DEDUCT_SALVAGE_AND_TRANSFER_IT` is emitted in both. Expected-failure marker
   `test_ia05_incomplete_title_transfer_cannot_pay_total_loss` remains strict and correctly red at
   head — the suite does not close this.
2. **F-02 / IA-08 — P0, both revisions.** A non-zero franchise attributed to `INSURER_MANUAL` with
   no reference and no version pays exactly what a dated policy term pays (C101 = C13D =
   1,432,000,000); the result even omits `franchise_source_version`. Marker
   `test_ia08_unversioned_manual_franchise_cannot_pay` remains strict red.
3. **F-03 / IA-14 — P2 with P0 blast radius at the boundary, both revisions.** INT-07/08/09 all pay
   1,900: a missing salvage operand, an explicit retained-salvage claim with no valuation and a
   documented zero are indistinguishable inside `compute()`. Both parametrised markers
   (`disposition-absent`, `retained-value-absent`) remain strict red. The supported Review path
   contains the same facts (C65/C66 block), so this stays an internal-boundary asymmetry, not a
   payment route.
4. **F-04 / IA-11 — P2, both revisions.** Graph numeric payloads do not execute. Mutating
   `annual_rate` to 0.20 or `maximum_rate` to 0.01 leaves depreciation and payable unchanged.
   Relevant to PR-03 specifically because that PR edits `knowledge/operators.json` (formula text and
   `inputs`) for the replacement predicate while the arithmetic lives in Python: the graph edit is
   descriptive, not executable, so graph/runtime parity remains **PARTIAL**.
5. **F-05 / IA-03, IA-04 — P0 at the accepted baseline, corrected at the proposed head.** §7.1 and
   §7.4 quantify both: a 108,000,000 (C13A) and 27,000,000 (C21) underpayment from ageing repair-only
   work; a silently accepted contradictory component record; and a strict-threshold bypass that paid
   6,761/6,860 where the evidenced numerator said 75.01%/76%. The proposed head matches the
   reference in all six rows and in INT-01..INT-04/INT-14, while INT-13 shows the documented-override
   route is still available where evidence is complete. **These are the PR's own scope and they
   verify.**

**B. Incomplete case evidence (the model is right to withhold; nothing to fix in arithmetic)**

6. At the proposed head, 27 of the 47 cases issue no payable — 14 `INSUFFICIENT_INFORMATION`,
   4 input-contract refusals (exit 1) and 9 engine-side blocked/scenario rows — because a required
   fact, document or branch artifact is missing. C43/C44 show the shape PR-03 intends: the branch is
   reclassified correctly and the *total-loss* evidence set is then demanded, rather than paying a
   partial figure. (The accepted baseline issues 23 payables where the reference supports 20.) Note
   also that the questionnaire is imperfect: with `Q-S4-01 = AGGREGATE_ONLY` the file must still
   answer `Q-S4-03` (an "amount" blocking question) even though an aggregate assessment by definition
   cannot itemise — C47 fails closed, but the advertised aggregate route cannot reach `COMPUTE`.
   Record as a procedure-design gap, not a numeric defect.

**C. Unresolved legal or contractual interpretation (do not treat as defects)**

7. **F-06 / IA-06 (RQ-02)** — C104 pays 7,200,000,000 with a caller-selected occurrence anchor while
   Article 19 (classification) and Article 20 (payment) name different clocks. Amount undisputed;
   authorization is the open question.
8. **IA-09 (RQ-03/RQ-04/RQ-07)** — C64 pays on a pre-salvage franchise base; C71 correctly returns
   both U01 scenarios. Selecting one requires an applicable circular/policy artifact.
9. **RQ-07** — C67 treats `NOT_APPLICABLE` as `INSURED_RETAINS` silently (see §7.3).
10. **IA-10 (RQ-05/RQ-06)** — C97/C98 pay with review labels only.
11. **IA-13 / U15** — C81 blocks before any arithmetic: `blocking_conditions =
    ["RISK_INTENSIFICATION_PREMIUM_RATIO_UNRESOLVED"]`, `live_uncertainties =
    ["U15_RISK_INTENSIFICATION_PREMIUM_RATIO"]`, `calculation = null`, and the same at the baseline.
    Because no calculation runs, the capital ratio was not substituted for the premium ratio; the
    engine-side `RISK_INTENSIFICATION_PREMIUM_RATIO_UNRESOLVED` status (which the gates document for
    a risk-intensified case) was therefore never reached on the supported path — that fail-closed
    path stays verified by the repository's own tests, not by this inspection.

**D. Unsupported implementation scope (advertised, not reachable)**

12. **F-07 / IA-13.** Battery/tyre: `PS_PART_NEW_PRICE` stays `NOT_APPLICABLE`/`NOT_TRIGGERED` and
    `PS_BATTERY_TIRE_INTERACTION` never binds, so **no** interaction mode can be selected through
    `claim.py review` (C31–C35 are identical at the engine). Fail-closed, so safe — but the T1/T3
    ladder and `Q-S4-04`/`Q-S8-02` prose describe a supported route that does not exist. The new
    head-side narrowing of U04 liveness (`review.py:390-394`) also still defaults
    `requires_replacement` to `True` for a raw BATTERY/TIRE record, whereas `case.py`, `operators.py`
    and `review.py:508-510` default it to `category != "REPAIR_ONLY"` — a third default in the same
    change set.
13. **IA-13, second instance.** `Q-S4-05 = ASSESSED_FIGURE` cannot bind (C48): a choice-valued
    answer against a money slot, and the engine takes the per-part route regardless.
14. `Q-S6-03` declares that it binds `PS_FRANCHISE.base_and_minimum`, which no code reads; the shipped
    and generated cases therefore smuggle `calculation_base` into the same object instead. Answered
    ≠ bound.
15. **Exception shape.** At the baseline, unknown material facts raised `InputSchemaError` out of
    `compute()` (INT-04/INT-05) rather than returning a machine-visible blocked result. Universal
    invariant 10 ("invalid input and guard violations are machine-visible failures") is met by the
    CLI exit code but not by the library call. Worth a check when PR-05A/PR-11 revisits the boundary.

**E. Differences from insurer practice that do not yet establish a defect**

16. The insurer-published franchise schedule (`SRC_IRANINSURANCE_BODY_FRANCHISE_SCHEDULE`) shows
    first-versus-later claim rates, not-at-fault reductions and separate theft/glass lines. The model
    stores `claim_sequence_rule: "first claim"` as metadata and applies one rate. That is a
    documented-scope gap (U02), not arithmetic, and the register itself forbids executing those rates
    before a dated instrument is ingested.
17. The parts-theft endorsement line (50% of new for tyres/battery/spare wheel, 20% franchise) is not
    implemented; the model blocks (`ENDORSEMENT_LIMIT_AND_FRANCHISE_REQUIRED`). Blocking is the
    correct posture without wording.

**F. Documentation-integrity finding (IA-16 class), verified directly in this session**

18. Shipped documents state a suite and gate size that no longer exist at the reviewed revision:
    `README.md:62`, `docs/BODY_CLAIM_ACCEPTANCE_MODEL.md:311,319`,
    `docs/RESEARCH_REPORT_MODEL_VALIDATION.md:280,281`, `docs/STAGE0_REMEDIATION_BASELINE.md:95,98,138`,
    `docs/PR01_CANONICAL_DATES_VALUES.md:191` assert **515 passed / 11 strict expected failures /
    24/24 mutants**, while `6f655f1` measures **609 passed, 4 xfailed, 28/28 killed** and
    `docs/MUTATION_REPORT.md:8` says 28/28. The generated-doc gate (`sync_review_docs.py`,
    `sync_customer_faq.py`) passes because these numbers are not inside generated blocks, so a green
    documentation gate does not mean the shipped suite claims are current.

---

## 9. Invariant checks requested by the brief

| Invariant | Evidence | Verdict at proposed head |
|---|---|---|
| A missing fact cannot improve entitlement | Supported path: C45 (omitted rescue) → no amount at **both** revisions, while C46 (documented 0) → 6,660 and C44 (evidenced 200) → reclassified total loss, no amount. Engine boundary: INT-01 at the baseline paid **6,660** for an absent operand; at the head it is blocked | **holds at head**; the supported path held it at both revisions, the accepted baseline's engine boundary did not |
| Rescue is counted exactly once | C47: `Q-S4-11` binds the aggregate figure 7,400 to both gross and repair total, separately evidenced rescue is 200, and Review derives **TOTAL_LOSS** — a derivation impossible unless the numerator is 7,600 and not 7,800 (7,400 alone is 74%). INT-04 blocks when the assessment already embeds rescue. Classification reads `rescue_for_total_loss_test_*` (source `DERIVED_FROM_ACTUAL_RESCUE`), settlement reads `rescue_transport_actual_irr` under the 20% ceiling | holds |
| Total-loss reclassification demands its own evidence | C43 `open_blocking_questions=[Q-S4-08]`, `evidence_blocks=[EVT_SALVAGE_VALUATION]`; C44 identical; C47 also carries the un-itemised `Q-S4-03` | holds |
| Repair-only depreciation is zero | C13A/C13B dep 0; C21 dep 120,000,000 across four component kinds | holds |
| A classification override cannot bypass unresolved rescue | INT-02/INT-14 blocked (`this evidence gate cannot be overridden`), while INT-13 with complete operands still pays 9,200 | holds |
| Strict threshold semantics | C41 74.99% partial, C42 exactly 75% partial, C43 75.01% total | holds |
| Blocked cases were not bypassed to obtain an amount | 18 of 47 review cases end with no calculation at all at the head (14 `INSUFFICIENT_INFORMATION` + 4 exit-1 input refusals); none was pushed through `--emit-case` or an internal path to manufacture a payable, and the 14 engine-boundary probes in §7.4 (8 of which issue an amount) are visibly `INTERNAL_TEST_DIRECT` and are reported apart from the supported path | holds |
| No authorization manufactured | every amount above comes either from `Review.authorize()` (COMPUTE/SCENARIO_SET) or a row visibly labelled `INTERNAL_TEST_DIRECT` | holds |

---

## 10. Status of the counterexamples that must be preserved

`IA-05`, `IA-08` and both `IA-14` counterexamples are **preserved and still failing** at the
proposed head: their `xfail(strict=True)` markers are untouched (`tests/test_stage0_counterexamples.py:135,162,179`),
they appear in the 4-xfail set measured here, and this inspection reproduced each one
independently through the supported path (C61 ≡ C62, C101 ≡ C13D) and the internal boundary
(INT-07/08/09). **A passing fixture suite (50/50), a 609-test suite and a 28/28 mutation gate do not
close them.** No expected-failure marker was removed, altered or converted by this work.

---

## 11. Insurer examples this inspection could not author, and what would unlock them

| Needed document | Would resolve | Blocking case family | Status |
|---|---|---|---|
| One underinsured partial-loss worksheet (gross parts/labour, depreciation, franchise, final payment) per insurer, dated | U01, RQ-04, and the F4 single-amount question | C71/C72 | not held; not invented |
| Franchise schedule by product, coverage line and policy version with an effective date | U02, RQ-10, IA-08 remediation test | F7, C61..C67 total-loss franchise lines | register page exists but is undated and marked `requires_primary_revalidation` |
| Standalone-glass endorsement wording (installation inclusion, rate/minimum, valuation condition, underinsurance treatment) | U03, U11, U14, RQ-11 | C102 | one company's wording only, no version |
| Article 8 component valuation map + annual conventional reference set | U06, U07 | outside body scope | not held |
| Primary 1405 diyah announcement | U08 | third-party scope | secondary only |
| Claims-department statement on old battery/tyre cap-vs-depreciation | U04, RQ-09 | C31–C35 | not held |
| Signed circular 1400/401/146850 with repeal history + applicable policy version | RQ-03 / IA-09 | C64 | compilation copy read; no page/paragraph locator |

Until those exist, "unresolved authority" rows in §7.3 cannot be converted into defects, and no
anonymised real-insurer case can be truthfully added to this matrix.

---

## 12. Disposition

* The **proposed head** (`6f655f1`) is the only revision that matches the independently derived
  reference for IA-03 and IA-04, and it closes the unresolved-rescue payment gate including the
  override bypass reported at `99bdb4d`. Its stated scope verifies.
* The **accepted integration baseline** (`a8a2047`) still contains IA-03 and IA-04 as live
  supported-path defects (§7.1, §7.4). Any conclusion drawn "from main" or "from the merged line"
  must not credit the head's corrections to it.
* Out-of-scope content inside PR #56 that a reviewer must decide on separately: the Python support
  narrowing to `>=3.11,<3.12` with a single CI job, the new `sync_customer_faq.py` CI gate, the
  rewrite of the customer-facing `Q-S4-11` ask text and six bilingual FAQ answers, three new
  `damage` schema fields, and the reordering of the `reconcile_classification` outcome ladder (which
  changes behaviour for any undeclared-branch case, not only rescue cases).
* `CONTRIBUTING.md` requires engineering **and** domain review for eligibility, operator-order,
  deduction, cap and contractual-authority changes. PR #56 records **no review decision**; CI green
  alone is not acceptance, and this inspection is not a review approval.
* **Release: BLOCKED.** Confirmed P0 defects remain (IA-05, IA-08; IA-14 at the boundary),
  authority-dependent scope remains unresolved (theft clocks, franchise base authority, notice and
  recourse adjudication, premium-ratio mechanism, glass economics), graph/runtime parity remains
  PARTIAL, and no source in the register has integrity evidence.
* This document changes no runtime rule, no marker, no remote issue and no PR state.

---

## Appendix A — input digests (SHA-256, first 16 hex chars)

Files live in `cases/inspection-*.json`. The read-only runner passes those same absolute inputs to
each pinned worktree and records the full SHA-256 before execution, so both revisions receive
byte-identical submissions.

| file | sha256(16) | | file | sha256(16) |
|---|---|---|---|---|
| inspection-c101-manual-franchise-unversioned | `05316e9ebac1cc19` | | inspection-c62-title-transferred | `d78dcfbed713cc66` |
| inspection-c102-glass-endorsement-token-only | `f3f5d55b7fd4e163` | | inspection-c63-retains-after-salvage | `2a12919471dd7f80` |
| inspection-c104-theft-60-59-clock | `85400a7bf8e6484c` | | inspection-c64-retains-settlement-base | `8bad08490a94b6fa` |
| inspection-c105-theft-59-days | `3db7872e9de20ce6` | | inspection-c65-retains-salvage-missing | `b848c4c44c7aa4db` |
| inspection-c106-theft-clock-unbound | `a28986645826de4f` | | inspection-c66-disposition-unresolved | `d9f929e3aab79b9e` |
| inspection-c13a-repair-only | `26d63d6c891a0a4a` | | inspection-c67-disposition-not-applicable | `f13d7ac3a5cae5ea` |
| inspection-c13b-replaced-but-flag-false | `d29f47bafb1763e6` | | inspection-c71-underinsured-unresolved | `b2539abf950ccf93` |
| inspection-c13c-repair-only-flag-true | `737a7ca8f18bc9a3` | | inspection-c72-underinsured-order-locked | `34534983734a01cd` |
| inspection-c13d-replacement-control | `144228295be21ad8` | | inspection-c73-overinsured | `648b455836f19fe9` |
| inspection-c21mix-four-kinds | `49ba540c3d9e6a22` | | inspection-c74-underinsured-total-loss | `96a3d5761819dad8` |
| inspection-c31u04-unresolved | `cc61e89c40e10e81` | | inspection-c81-risk-intensified-yes | `564b54ce03eb4ba7` |
| inspection-c32u04-cap-then-dep | `49ea0519aa898bc7` | | inspection-c82-risk-intensified-unknown | `02b99991f665af32` |
| inspection-c33u04-dep-then-cap | `b9f6671bdbfbd768` | | inspection-c83-instalment-overdue | `60d18ac32dc98de6` |
| inspection-c34u04-cap-only | `fec9c411cca2657d` | | inspection-c84-policy-state-unknown | `e110ef7f59885f80` |
| inspection-c35q404-battery-new-price | `b9ae0647ee6a8241` | | inspection-c91-prior-full-compensation | `1073a82fee9e4bc5` |
| inspection-c41-below-7499 | `26c256fecb7391ac` | | inspection-c92-prior-zero-documented | `8b03d474a4b90c4a` |
| inspection-c42-at-7500 | `dd61139e55545c27` | | inspection-c93-causation-asserted-only | `8f552ca5a43b5b43` |
| inspection-c43-above-7501 | `3821317644084ffb` | | inspection-c94-event-date-impossible | `6becf935aa0c2b8f` |
| inspection-c44-rescue-crosses-7600 | `db3646ed56219672` | | inspection-c95-production-year-future | `e5addec28b04eff4` |
| inspection-c45-rescue-omitted | `12786999319df80a` | | inspection-c96-conflicting-money-aliases | `2627fc6398dfca77` |
| inspection-c46-rescue-explicit-zero | `c6a93d3286d84df0` | | inspection-c97-late-notice-no-excuse | `5d9e9c8436725ec2` |
| inspection-c47-aggregate-only-rescue | `e2012fd4319adc4d` | | inspection-c98-recourse-released | `11971f8614b318d9` |
| inspection-c48-assessed-depreciation-figure | `9540923711177f29` | | inspection-c99-third-party-split | `744ac8f15a16c936` |
| inspection-c61-title-not-transferred | `97e7862aaecc913f` | | | |

## Appendix B — reproduction and continued use

> **Corrected comparator (PR #57):** the historical prose expectations and
> 37/10 observation below are preserved, but the enforceable v1 manifest and
> derived-verdict acceptance policy are documented in
> `docs/CASE_COMPARATOR_V1.md`. `docs/case-reference-manifest-v1.json` is the
> machine-readable oracle; the runner never regenerates it from model output.

Run the complete corpus against any pinned checkout from the inspection branch. The output is a
machine-readable observation record; it does not update an expected result or approve a legal
interpretation.

```bash
python scripts/run_case_based_inspection.py \
  --root /path/to/pinned-model-worktree \
  --cases cases \
  --internal \
  --output /tmp/case-inspection.json
```

The runner performs both documented supported-path commands for all 47 inputs. With `--internal`,
it additionally runs the 14 probes through the established `INTERNAL_TEST_DIRECT` helper and keeps
them in a separate JSON section. It does not generate inputs, alter the checkout, issue a
production authorization, contact GitHub or compare against model output as its own oracle.

To investigate one supported case interactively, run these commands from the pinned model
worktree, using the absolute path to the committed inspection case when the corpus is on a separate
branch:

```bash
# IA-05: title state is inert; compare C61 with C62
python claim.py review /path/to/inspection/cases/inspection-c61-title-not-transferred.json --json --calc
python claim.py review /path/to/inspection/cases/inspection-c62-title-transferred.json --json --calc

# IA-08: unversioned manual franchise authority
python claim.py calc /path/to/inspection/cases/inspection-c101-manual-franchise-unversioned.json

# IA-04 and missing-rescue containment
python claim.py calc /path/to/inspection/cases/inspection-c44-rescue-crosses-7600.json
python claim.py calc /path/to/inspection/cases/inspection-c45-rescue-omitted.json

# preserved strict counterexamples, including both IA-14 variants
python -m pytest -q -rx --no-header tests/test_stage0_counterexamples.py
```

For future model revisions:

1. create a clean worktree at the candidate commit and record its commit/tree;
2. use Python 3.11 and run the repository gate before the corpus;
3. copy neither expected amounts nor prior observed output into the new reference column;
4. add a new case only after writing its independent expectation and source/provenance record;
5. vary one material fact, retain missing versus explicit zero, and never fill missing Review facts
   merely to reach a payable;
6. diff the two JSON observation reports and classify each change as defect, incomplete evidence,
   unresolved authority, unsupported scope or practice-only difference;
7. keep the release blocked until the applicable engineering and domain reviews are complete.


Current follow-up (2026-11-03): see docs/reconciliation-evidence/rc1-followup/CASE_DISPOSITIONS.md and VALIDATION_REPORT.md. The observations above remain pinned historical evidence; this pointer does not rebaseline or relabel them. Canonical release status: docs/RELEASE_STATUS.md, BLOCKED.
