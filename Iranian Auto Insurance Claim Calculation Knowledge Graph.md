make a knowledge model for this :


# Summary of the Iranian Auto Insurance Claim Calculation Knowledge Graph

## Core thesis

The report replaces the naive formula:

```
خسارت − استهلاک − فرانشیز − ماده ۱۰ = پرداخت
```

with a **classification-first, provenance-backed, uncertainty-aware rule engine**:

```
EVENT → LEGAL/POLICY SNAPSHOT → COVERAGE + CAUSATION + EXCLUSION GATE
     → CLAIM BRANCH CLASSIFICATION → BRANCH-SPECIFIC VALUATION
     → COMPONENT CLASSIFICATION → APPLICABLE OPERATORS
     → CONFIGURABLE OPERATOR ORDER → STATUTORY/CONTRACTUAL CAPS
     → DUAL-COVERAGE ALLOCATION → SUBROGATION/LEGAL RECOVERY
     → PAYABLE + RULE TRACE + PROVENANCE + CONFIDENCE + UNRESOLVED VARIABLES
```

## Major corrections to internet templates

| Topic | Common internet claim | Actual rule-engine finding |
|---|---|---|
| Article 10 | A deduction | An **underinsurance ratio** `min(1, insured/market)`, capped at 1 |
| Depreciation | Only consumables (battery, tires, plastics) | **All replacement parts except glass/lamp glass**, 5%/year from 5th production year, max 25% |
| Battery/tires | Regular depreciation | **Separate 50%-of-new-price cap**; interaction with aging depreciation is **unresolved** |
| Glass | Universal 20% franchise | **No universal statutory 20%**; franchise is policy-defined |
| Glass & Article 10 | Automatically exempt | **No authoritative blanket exemption**; depends on endorsement wording |
| Total loss | 75% threshold | **Strictly `> 75%`**, not `>=`; theft → total loss at **60 days** |
| Total loss + underinsurance | Apply ratio after `min(market, insured)` | **Double application prohibited** — guardrail required |
| Salvage vs franchise | Franchise first | **Salvage first, then franchise** (Central Insurance circular 1400/401/146850) |
| Article 8 | `damage × threshold / luxury_value` | **Component-wise correspondence** to most expensive conventional car (1398 amendment) |
| Article 8 excess | Sue at-fault driver for all excess | **Capped against at-fault party too**; excess may be covered by victim's own body policy |
| "عامل بلافصل حادثه" | A numerical multiplier | **Not in Reg. 53**; causation predicate, not a multiplier |
| Exclusions | Single `coverage = false` | Two states: **`EXCLUDED_BUT_ENDORSABLE`** vs **`NON_COMPENSABLE`** |

## Branch engines

1. **Partial damage** — repair + parts − depreciation → ratio/franchise (configurable order) → + rescue
2. **Total loss** — `min(market, insured) − salvage − franchise + rescue`, capped at insured sum; no double ratio
3. **Glass-only** — requires endorsement; depreciation = 0; Article 10 treatment unresolved
4. **Theft** — whole vehicle: pending <60 days, total ≥60 days with title transfer
5. **Third-party financial** — `min(assessed, policy_limit)`; Article 8 only if non-conventional
6. **Article 8** — component correspondence first, financial cap second
7. **Legal recovery** — court award, prior compensation subtracted, subrogation rights allocated

## Shared operators

- **Depreciation**: `year_index = claim_year − production_year + 1`; `rate = 0 if <5 else min(0.25, 0.05 × (year_index − 4))`; glass/lamp glass = 0
- **Franchise**: policy-configured; not a universal rate
- **Underinsurance ratio**: `min(1, insured / market)`
- **Salvage**: deducted before total-loss franchise
- **Rescue/transport**: capped at 20% of gross damage
- **Liability cap**: contractual financial limit + Article 8 corresponding-damage cap

## Contradiction matrix (calibration backbone)

| Topic | Status | Controlling authority |
|---|---|---|
| Article 10 order vs franchise | **UNRESOLVED / configurable** | Reg. 53 Art. 19(b) + Art. 20 n.2 |
| Glass franchise | **Policy-specific** | Reg. 53 + endorsement |
| Total loss threshold | **Resolved** `> 75%` | Reg. 53 Art. 19 |
| Article 8 method | **Resolved: component correspondence** | 1398/06/13 amendment |
| Depreciation schedule | **Resolved: 5%/yr, max 25%** | Reg. 53 Art. 19 |
| Battery/tire + depreciation interaction | **UNRESOLVED** | Reg. 53 Arts. 3 & 19 |
| Salvage vs franchise | **Resolved: salvage first** | Central Insurance 1400 circular |
| Article 8 excess vs at-fault | **Resolved: capped** | Art. 8 + 1404 circular |
| Article 10 in total loss | **Resolved: no double application** | Reg. 53 Art. 19 |
| Glass exemption from Article 10 | **Unproven** | Reg. 53 |

## Confidence model

High confidence (0.98–0.99): regulatory text items.
Low confidence (0.05–0.20): universal glass franchise, glass Article 10 exemption, whole-car Article 8 ratio, mandatory franchise on Article 8 body-excess.
Medium confidence (0.86): 1405 diyah (secondary source, requires primary revalidation).
Low confidence (0.35): insurer-specific franchise tables (manuals not obtained).

## Unknowns requiring claims-department validation

1. Article 10 operator order in partial loss
2. Franchise base schedules by product/version
3. Glass-only endorsement wording
4. Battery/tire cap vs depreciation interaction
5. Rescue denominator under underinsurance
6. Article 8 component catalogue (valuation map)
7. Annual conventional-car reference set
8. 1405 primary diyah announcement
9. Diminution of value (افت قیمت) in third-party context
10. "Immediate cause" terminology handling

## Deliverables in the report

- Full decision tree
- JSON Schema (production-grade, with provenance)
- Pseudocode for every branch engine
- 50 synthetic test cases (P01–L50)
- Contradiction matrix
- Confidence scores per rule
- Source register with URLs

---

# Suggested Ontology Model

## Design principles

1. **Every node carries provenance** — source class, authority, instrument, article, version, effective date, confidence.
2. **Uncertainty is a first-class node**, not a missing value.
3. **Contradictions are edges**, not prose.
4. **Operators are separate from branches** — branches compose operators.
5. **Order is data** — `OperatorOrder` is a configurable node, not hardcoded.
6. **Annual parameters are versioned nodes** — they change yearly without invalidating rules.

## Core ontology classes

```
┌─────────────────────────────────────────────────────────────┐
│                     CLAIM DOMAIN                            │
├─────────────────────────────────────────────────────────────┤
│  Claim                                                      │
│  ├── claim_id, event_date, fault_status, cause              │
│  ├── classified_as → Branch                                 │
│  ├── requires → Evidence                                    │
│  ├── subject_to → Operator                                  │
│  ├── governed_by → LegalRule                                │
│  └── produces → Payment                                     │
├─────────────────────────────────────────────────────────────┤
│  Branch (enum)                                              │
│  ├── PARTIAL_DAMAGE                                         │
│  ├── TOTAL_LOSS                                             │
│  ├── GLASS_ONLY                                             │
│  ├── THEFT                                                  │
│  ├── THIRD_PARTY_FINANCIAL                                  │
│  ├── ARTICLE_8_NON_CONVENTIONAL                             │
│  └── LEGAL_RECOVERY                                         │
├─────────────────────────────────────────────────────────────┤
│  Vehicle                                                    │
│  ├── market_value_at_event, insured_sum                     │
│  ├── production_year, is_passenger_car                      │
│  ├── salvage_value, salvage_disposition                     │
│  └── has_component → DamageComponent                        │
├─────────────────────────────────────────────────────────────┤
│  DamageComponent                                            │
│  ├── category (GLASS, LAMP_GLASS, BATTERY, TIRE,            │
│  │             OTHER_REPLACEMENT_PART, REPAIR_ONLY)         │
│  ├── assessed_loss, new_price                               │
│  ├── subject_to → DepreciationOperator                      │
│  ├── subject_to → SpecialPartCap                            │
│  └── mapped_to → CorrespondingArticle8Component             │
├─────────────────────────────────────────────────────────────┤
│  Policy                                                     │
│  ├── insurer, policy_version                                │
│  ├── third_party_financial_limit                            │
│  ├── has_endorsement → Endorsement                          │
│  └── configures → FranchiseOperator                         │
├─────────────────────────────────────────────────────────────┤
│  Endorsement                                                │
│  ├── type (GLASS_ONLY, PARTIAL_THEFT, FLOOD, ...)           │
│  ├── restores → Exclusion                                   │
│  └── configures → Operator                                  │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                     RULE DOMAIN                             │
├─────────────────────────────────────────────────────────────┤
│  LegalRule                                                  │
│  ├── rule_id, source_class                                  │
│  ├── authority, instrument, article                         │
│  ├── effective_version, effective_date                      │
│  ├── rule_payload (structured)                              │
│  └── confidence                                             │
├─────────────────────────────────────────────────────────────┤
│  SourceClass (hierarchy)                                    │
│  ├── STATUTE (قانون)                                        │
│  ├── REGULATION (آییننامه / مصوبه شورای عالی بیمه)          │
│  ├── CIRCULAR (بخشنامه / دستورالعمل بیمه مرکزی)              │
│  ├── POLICY (بیمهنامه / شرایط خصوصی / الحاقیه)               │
│  ├── INSURER_PROCEDURE (رویه / manual شرکت بیمه)            │
│  └── EDUCATIONAL (مقاله آموزشی / تجربه کارشناسی)             │
├─────────────────────────────────────────────────────────────┤
│  Operator                                                   │
│  ├── operator_id                                            │
│  ├── type (DEPRECIATION, FRANCHISE, UNDERINSURANCE_RATIO,   │
│  │         SALVAGE_DEDUCTION, RESCUE_CAP, LIABILITY_CAP,    │
│  │         SPECIAL_PART_CAP, CORRESPONDING_DAMAGE)          │
│  ├── formula (expression tree or reference)                 │
│  ├── inputs, outputs                                        │
│  └── configured_by → PolicyVersion | InsurerProcedure       │
├─────────────────────────────────────────────────────────────┤
│  OperatorOrder                                              │
│  ├── branch                                                 │
│  ├── sequence: [Operator, Operator, ...]                    │
│  ├── status (RESOLVED, UNRESOLVED, INSURER_SPECIFIC)        │
│  └── scenarios (when unresolved)                            │
├─────────────────────────────────────────────────────────────┤
│  Exclusion                                                  │
│  ├── type (ENDORSABLE, NON_COMPENSABLE)                     │
│  ├── restorable_by → Endorsement                            │
│  └── cause_predicate                                        │
├─────────────────────────────────────────────────────────────┤
│  AnnualParameter                                            │
│  ├── year (e.g., 1405)                                      │
│  ├── name (DIYAH, CONVENTIONAL_THRESHOLD, MIN_FINANCIAL)    │
│  ├── value, currency                                        │
│  ├── source_tier (PRIMARY, SECONDARY_CURRENT)               │
│  └── confidence, requires_primary_revalidation              │
├─────────────────────────────────────────────────────────────┤
│  Uncertainty                                                │
│  ├── uncertainty_id                                         │
│  ├── topic                                                  │
│  ├── blocking (boolean)                                     │
│  ├── scenarios (list of candidate outcomes)                 │
│  └── resolved_by → InsurerProcedure | LegalClarification    │
├─────────────────────────────────────────────────────────────┤
│  Contradiction                                              │
│  ├── contradiction_id                                       │
│  ├── topic                                                  │
│  ├── candidate_rule, candidate_source_class                 │
│  ├── controlling_rule, controlling_source_class             │
│  ├── resolution (REJECT_CANDIDATE, ACCEPT_CANDIDATE,        │
│  │              UNRESOLVED)                                 │
│  └── confidence                                             │
├─────────────────────────────────────────────────────────────┤
│  SubrogationRight                                           │
│  ├── holder (BODY_INSURER, TP_INSURER, INSURED)             │
│  ├── amount, cap                                            │
│  ├── created_by → Payment                                   │
│  └── impaired_by → InsuredAction                            │
└─────────────────────────────────────────────────────────────┘
```

## Core edges

```
Claim          --classified_as-->     Branch
Branch         --governed_by-->       LegalRule
Branch         --composes-->          Operator (ordered)
Claim          --requires-->          Evidence
Claim          --subject_to-->        Operator
Vehicle        --has_component-->     DamageComponent
DamageComponent --subject_to-->       Operator
DamageComponent --mapped_to-->        CorrespondingArticle8Component
Policy         --configures-->        Operator
Endorsement    --restores-->          Exclusion
Endorsement    --configures-->        Operator
Operator       --ordered_by-->        OperatorOrder
Operator       --sourced_from-->      LegalRule
LegalRule      --belongs_to-->        SourceClass
AnnualParameter --used_by-->          Operator
Uncertainty    --blocks-->            Operator
Uncertainty    --resolved_by-->       InsurerProcedure
Contradiction  --about-->             LegalRule
Contradiction  --rejects-->           CandidateRule
Payment        --creates-->           SubrogationRight
```

## Provenance envelope (every executable node)

```json
{
  "node_id": "REG53_ART19_PARTIAL_DEPRECIATION",
  "source_class": "REGULATION",
  "authority": "High Insurance Council",
  "instrument": "Regulation 53",
  "article": "19(b)",
  "effective_version": "current-researched-version",
  "effective_date": "1384/12/09",
  "confidence": 0.99,
  "payload": { },
  "last_validated": "2026-09-18",
  "next_revalidation": "2027-09-18"
}
```

---

# How to Make a Chatbot with an Expandable Ontology Knowledge Model

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                     CHATBOT LAYERS                           │
├──────────────────────────────────────────────────────────────┤
│  Layer 1: Intent Router                                      │
│  ├── FAQ / definition question                               │
│  ├── Claim calculation request                               │
│  ├── Rule lookup                                             │
│  ├── Contradiction query                                     │
│  └── Uncertainty escalation                                  │
├──────────────────────────────────────────────────────────────┤
│  Layer 2: Ontology Retrieval (GraphRAG)                      │
│  ├── Vector index over node descriptions                     │
│  ├── Graph traversal for related rules/operators             │
│  ├── Provenance-aware ranking                                │
│  └── Confidence-weighted context assembly                    │
├──────────────────────────────────────────────────────────────┤
│  Layer 3: Rule Engine                                        │
│  ├── Claim classifier (decision tree)                        │
│  ├── Operator executor (formula evaluation)                  │
│  ├── Order resolver (configurable, scenario-aware)           │
│  ├── Guardrail checker (double-application, caps)            │
│  └── Uncertainty propagator                                   │
├──────────────────────────────────────────────────────────────┤
│  Layer 4: Response Generator                                 │
│  ├── Natural language explanation                            │
│  ├── Rule trace + provenance citation                        │
│  ├── Confidence score                                        │
│  └── Escalation prompt when uncertain                        │
├──────────────────────────────────────────────────────────────┤
│  Layer 5: Knowledge Expander                                 │
│  ├── New rule ingestion (with provenance)                    │
│  ├── Contradiction detector                                  │
│  ├── Version migration                                       │
│  └── Human-in-the-loop validation                            │
└──────────────────────────────────────────────────────────────┘
```

## Making the ontology expandable

### 1. Schema-first ingestion

Every new rule enters through a validated schema. No free-text insertion.

```yaml
new_rule_submission:
  rule_id: required
  source_class: required (enum)
  authority: required
  instrument: required
  article: required
  effective_date: required
  payload:
    type: required (matches existing operator/rule types)
    formula: optional
    inputs: optional
    outputs: optional
  confidence: required (0-1)
  evidence_url: required
  submitted_by: required
  validation_status: pending
```

### 2. Contradiction-first ingestion

Before a new rule is committed, the expander runs:

```
For each existing rule with same topic:
    if new_rule.contradicts(existing_rule):
        create Contradiction node
        if new_rule.source_class > existing_rule.source_class:
            mark existing as SUPERSEDED
        else:
            mark new as REJECTED
        flag for human review
```

### 3. Versioned annual parameters

Annual parameters (diyah, threshold) are **separate nodes** with year keys. The chatbot retrieves the correct year without re-ingesting rules.

```
AnnualParameter(1405, DIYAH, 2.8e9, SECONDARY_CURRENT, 0.86)
AnnualParameter(1405, CONVENTIONAL_THRESHOLD, 1.4e9, DERIVED, 0.86)
AnnualParameter(1405, MIN_FINANCIAL, 7e7, DERIVED, 0.86)
```

When the Judiciary announces 1406, only these nodes change. All rules referencing them stay intact.

### 4. Uncertainty as queryable data

The chatbot can answer:

- "What is the Article 10 order?" → *"There are two sourced interpretations. Scenario A: … Scenario B: …. Blocking uncertainty: `ARTICLE10_ORDER`."*
- "Is there a universal glass franchise?" → *"No. Confidence 0.10. Here is why."*

### 5. Operator registry

New operators (e.g., a new special-part cap) are registered with:

```
operator_id
type
formula
inputs
outputs
applies_to_branches
sourced_from
confidence
```

Branches reference operators by ID. Adding an operator does not require rewriting branches.

### 6. Branch composition

Branches are declared as ordered operator lists:

```yaml
branch: PARTIAL_DAMAGE
operators:
  - DEPRECIATION
  - UNDERINSURANCE_RATIO (order: configurable)
  - FRANCHISE
  - RESCUE_CAP
order_status: UNRESOLVED
scenarios:
  - [DEPRECIATION, RATIO, FRANCHISE, RESCUE]
  - [DEPRECIATION, FRANCHISE, RATIO, RESCUE]
```

The chatbot can compute both scenarios and present them.

### 7. Human-in-the-loop escalation

When the rule engine returns `UNCERTAINTY` or `SCENARIO_SET`, the chatbot:

1. Explains what is known (high confidence)
2. Explains what is unresolved (low confidence)
3. Lists the two or more scenarios with numbers
4. Asks the user to confirm insurer/product
5. Optionally routes to a human adjuster

### 8. Knowledge graph query patterns

The chatbot uses these query templates:

| User intent | Graph query |
|---|---|
| "How is partial damage calculated?" | `Branch(PARTIAL_DAMAGE) → composes → Operator[] → ordered_by → OperatorOrder` |
| "What is depreciation rate for 8-year-old car?" | `Operator(DEPRECIATION) → formula → evaluate(year_index=8)` |
| "Is glass depreciated?" | `DamageComponent(GLASS) → subject_to → DepreciationOperator?` |
| "What is Article 8?" | `LegalRule(ARTICLE8) → payload + contradiction(ARTICLE8_RATIO_VS_COMPONENT)` |
| "Why did I get this amount?" | `Claim → rule_trace → [LegalRule, Operator, OperatorOrder, Confidence]` |
| "What's unresolved?" | `Uncertainty[] where blocking=true` |

### 9. Expandability without breaking

- **Add a new branch**: register `Branch` node, define operator sequence, add test cases.
- **Add a new operator**: register in operator registry, reference from branches.
- **Add a new insurer**: add `InsurerProcedure` nodes, attach to `PolicyVersion`, override configurable operators only.
- **Add a new annual parameter**: add `AnnualParameter(year, name, value)`, no rule changes.
- **Resolve an uncertainty**: update `OperatorOrder.status`, add `resolution_source`, keep old scenarios for audit.
- **Detect a contradiction**: create `Contradiction` node, run resolution logic, flag for review.

### 10. Chatbot response template

```
CLAIM CLASSIFICATION
  Branch: PARTIAL_DAMAGE
  Confidence: 0.95

APPLICABLE RULES
  - Reg. 53 Art. 19(b): partial loss = labor + parts − depreciation
  - Reg. 53 Art. 20 n.2: underinsurance ratio
  - Policy franchise schedule (loaded: Iran Insurance 1404)

CALCULATION
  Gross eligible:        400,000,000 IRR
  Depreciation (10%):    −37,500,000 IRR
  After depreciation:    362,500,000 IRR
  Underinsurance ratio:  0.75
  Scenario A (ratio first):  (362.5M × 0.75) − 40M = 231.9M
  Scenario B (franchise first): ((362.5M − 40M) × 0.75) = 241.9M
  Rescue (capped):       +20,000,000 IRR

  STATUS: ORDER_UNRESOLVED
  Blocking uncertainty: ARTICLE10_PARTIAL_ORDER

ESCALATION
  This claim requires insurer-specific validation.
  Which insurer issued your policy?
  [Iran Insurance] [Asia] [Pasargad] [Parsian] [Other]

SOURCES
  [1] Regulation 53, Art. 19(b) — confidence 0.99
  [2] Regulation 53, Art. 20 n.2 — confidence 0.99
  [3] Insurer manual — pending
```

---

# Practical priorities for building this

| Priority | Task | Impact | Effort |
|---|---|---|---|
| 1 | Implement provenance envelope on every node | 5 | Low |
| 2 | Build claim classifier decision tree | 5 | Medium |
| 3 | Register operators with formulas | 5 | Medium |
| 4 | Encode OperatorOrder as configurable data | 5 | Medium |
| 5 | Build contradiction matrix as queryable nodes | 5 | Low |
| 6 | Implement guardrails (double-application, caps) | 4 | Medium |
| 7 | Build GraphRAG retrieval over ontology | 4 | High |
| 8 | Implement scenario-set responses for uncertainties | 4 | Medium |
| 9 | Add insurer adapter slots (empty until manuals arrive) | 4 | Low |
| 10 | Build annual parameter refresh pipeline | 3 | Medium |
| 11 | Add 50 test cases as validation suite | 4 | Low |
| 12 | Human-in-the-loop escalation UI | 3 | Medium |

---

# Bottom line

The report gives you a **production-grade rule engine blueprint**. To turn it into an expandable chatbot ontology:

1. **Model every rule, operator, uncertainty, and contradiction as a node** with a provenance envelope.
2. **Separate branches from operators** so new branches compose existing operators.
3. **Make order configurable** so unresolved sequences return scenario sets, not fake precision.
4. **Version annual parameters** separately from rules.
5. **Ingest new knowledge through schema validation and contradiction detection**, not free-text.
6. **Let the chatbot escalate when confidence is low** rather than hallucinate a number.

The result is a **Claim Calculation Knowledge Graph** that grows by adding nodes and edges — not by rewriting formulas — and a chatbot that can explain, cite, and flag uncertainty at every step.



# Iranian Auto Insurance Claim Calculation Knowledge Graph

This report defines a rule-engine architecture for Iranian motor claims as of **September 18, 2026**. The governing model is deliberately **classification-first**: the engine identifies the legal/insurance branch, tests coverage and exclusions, determines the relevant valuation regime, and only then executes mathematical operators.

The research produces several corrections to common internet templates. Most importantly: **قاعده نسبی / Article 10 is a ratio, not a deduction; the base Regulation 53 depreciation rule is broader than “consumables only”; standalone glass does not have a universal statutory 20% franchise; total-loss underinsurance must not be applied twice; and the current Article 8 method for non-conventional cars is not a simple whole-vehicle price ratio.** citeturn18search3turn19view3turn25view1

## Authority model and controlling findings

The rule engine should attach a `source_class` to every rule. The hierarchy is:

| Rank | Source class | Engine treatment |
|---|---|---|
| Highest | **قانون — Statute** | Mandatory; overrides policy/manual inconsistency |
| High | **آیین‌نامه / مصوبه شورای عالی بیمه** | Mandatory within delegated scope |
| High | **بخشنامه / دستورالعمل بیمه مرکزی** | Operational/regulatory interpretation; respect effective date |
| Contractual | **بیمه‌نامه، شرایط خصوصی، الحاقیه** | Governs configurable items where regulation leaves them to the contract |
| Operational | **رویه / manual شرکت بیمه** | Useful only when consistent with higher authority and applicable policy version |
| Evidentiary only | **مقاله آموزشی / تجربه کارشناسی** | Never a formula authority; useful for contradiction discovery |

Regulation 53 was approved by the High Insurance Council on **1384/12/09** and provides the general conditions of land-vehicle body insurance. Its structure covers insured perils, excluded/non-compensable losses, policyholder duties, subrogation, total/partial-loss calculation, underinsurance, double insurance, dispute resolution, and geographic scope. citeturn18search0turn18search3turn21search13

### The controlling conclusions

| Question | Deep-research conclusion | Rule-engine status |
|---|---|---|
| What is “Article 10”? | Treat it as `UNDERINSURANCE_RATIO = insured_sum / actual_value_at_loss`, capped at `1`. Regulation 53 Article 20 note 2 independently states the same proportional-liability mechanism for body claims. citeturn25view1turn25view2 | **Resolved as a ratio** |
| Where in a partial-loss pipeline does that ratio run? | Regulation 53 explicitly says partial loss is based on repair/labor/current replacement-part prices after depreciation and franchise, with rescue/transport added; the underinsurance provision appears separately and does not expressly state its position relative to franchise. citeturn25view1 | **Unresolved; configurable** |
| What is the statutory depreciation schedule? | For replaced parts, except vehicle glass and lamp glass, depreciation starts from the beginning of the fifth production year, 5% per year, capped at 25%. citeturn25view1 | **Resolved for base Reg. 53** |
| Are depreciation rules only for battery, tires, plastics, etc.? | No. That internet shorthand is too narrow. Regulation 53 speaks generally of replaced parts, while battery and tires have a separate rule limiting covered loss to 50% of new price. citeturn22view0turn25view1 | **Corrected** |
| Is glass depreciated? | Glass and lamp glass are expressly excluded from the standard replacement-part depreciation calculation. citeturn25view1 | **Resolved** |
| Does glass-only universally use a 20% franchise? | No universal 20% rate appears in Regulation 53. Franchise is defined as the insured's share whose amount is specified in the policy. Public insurer practices can differ. citeturn25view2turn9search20 | **Policy-specific** |
| Is standalone glass automatically exempt from Article 10? | I found no authoritative basis for a blanket exemption. The underinsurance clause is general; a standalone-glass endorsement may modify the result, but its actual wording must be loaded. citeturn25view1 | **Do not hard-code exemption** |
| When is physical damage a total loss? | If covered repair/replacement costs including rescue exceed—strictly **more than**—75% of vehicle value on the accident date, or the whole vehicle remains unrecovered for at least 60 days after theft. citeturn22view1turn25view2 | **Resolved** |
| What is the total-loss valuation base? | Market/transaction value on the loss date, no more than the insured sum; probable salvage and prescribed deductions are subtracted and allowable rescue/transport added, subject to the insured-sum ceiling. citeturn25view1turn25view2 | **Resolved** |
| Should underinsurance be applied again after using `min(market_value, insured_sum)` in total loss? | **No double application.** For a complete loss, applying the underinsurance ratio to full market-value loss mathematically produces the insured sum. Applying the ratio again to an already capped insured-sum base would double-reduce the claim. This is an implementation inference from the two controlling clauses. citeturn25view1 | **Guardrail required** |
| Salvage before or after franchise? | Central Insurance circular no. `1400/401/146850`, dated `1400/09/13`, clarifies that salvage is not itself “damage” and that total-loss franchise is calculated after probable salvage has been deducted. citeturn4view0turn18search3 | **Resolved for ordinary salvage-retained settlement** |
| Is Article 8 a simple `damage × threshold / expensive-car-value` formula? | Not under the current amended instruction. The 1398 amendment requires determination of **corresponding damage** using the relevant part of the most expensive conventional car; where no exact counterpart exists, a similar part is used. citeturn19view3 | **Whole-car ratio rejected as primary method** |
| Can the victim collect the Article 8 excess directly from the at-fault driver? | Not the portion above the statutory corresponding-damage ceiling. Article 8 limits compensation through the third-party policy **or the at-fault person** to corresponding conventional-car damage. Central Insurance's 1404 circular says the excess may instead be taken to the victim's own body insurer if coverage exists. citeturn19view2turn19view3 | **Major correction** |

A second conceptual correction is important. **“عامل بلافصل حادثه” is not a numerical multiplier found in Regulation 53.** The regulation repeatedly requires causal relationships between a peril/exclusion and the damage, but the legally significant “بلافاصله” wording often encountered in insurance-law discussion instead concerns the value of property immediately before and immediately after an event under Article 19 of the Insurance Law. Those are different concepts: one is causation; the other is valuation. citeturn18search24turn22view0

Regulation 53 divides exclusions into two useful rule-engine classes. Article 5 lists risks that are outside the basic cover but can be brought back by endorsement, including flood/earthquake/volcano, racing/speed testing, certain hazardous cargo, chemical/paint damage unless caused by an insured peril, scratching, loss of use, and diminution in vehicle value. Article 6 contains non-compensable circumstances such as war, nuclear events, intentional damage, certain police-flight losses, inappropriate/no valid licence, causally established alcohol/drug use, unauthorized towing, inherent electrical/electronic malfunction and overload. citeturn22view0turn22view4

That means the engine needs two different failure states:

```text
EXCLUDED_BUT_ENDORSABLE
    ≠
NON_COMPENSABLE
```

It should not collapse both into a generic `coverage=false`.

The body policy also imposes operational duties. Loss is to be notified within five working days of awareness unless an unavoidable cause prevented compliance; the insured must mitigate damage, refrain from unauthorized movement/repair, provide requested evidence, and avoid acts that destroy the insurer's recourse against the responsible party. Breach of the subrogation-preservation duty can permit denial or recovery of an already paid amount. citeturn22view1

## Decision system and branch engines

The correct top-level graph is:

```text
CLAIM
│
├── establish event + vehicle + policy snapshot
│
├── coverage gate
│   ├── base insured peril?
│   ├── endorsable exclusion + endorsement?
│   ├── Article 6 non-compensable condition?
│   ├── policy duties complied with?
│   └── causal relationship established?
│
├── classify insurance/legal domain
│
├── BODY
│   │
│   ├── whole vehicle stolen?
│   │   ├── missing < 60 days ───────────────► THEFT_PENDING
│   │   └── missing ≥ 60 days ───────────────► THEFT_TOTAL
│   │
│   ├── physical repair + rescue > 75% market value?
│   │   └── yes ─────────────────────────────► TOTAL_LOSS
│   │
│   ├── independent glass breakage?
│   │   └── yes ── check endorsement ────────► GLASS_ONLY
│   │
│   └── otherwise ───────────────────────────► PARTIAL_DAMAGE
│
├── THIRD_PARTY_FINANCIAL
│   │
│   ├── damaged property is passenger vehicle?
│   │   └── no ──────────────────────────────► ORDINARY_FINANCIAL
│   │
│   ├── value < annual conventional threshold?
│   │   ├── yes ─────────────────────────────► CONVENTIONAL_VEHICLE
│   │   └── no ──────────────────────────────► ARTICLE_8
│   │
│   └── apply purchased financial limit
│
└── LEGAL / RECOVERY
    ├── body insurer subrogation
    ├── direct uncompensated liability
    ├── third-party insurer statutory recourse
    ├── double-insurance contribution
    └── subrogation impairment
```

The body branches above follow Regulation 53 Articles 3–6 and 19–21; the third-party split follows Article 8 and the amended High Insurance Council instruction. citeturn22view0turn25view1turn19view3

### Branch specification

| Branch | Legal basis | Required calculation inputs | Formula / engine | Deduction order | Major exceptions and evidence |
|---|---|---|---|---|---|
| **Partial damage — خسارت جزئی** | Reg. 53 Art. 19(b), Art. 20 n.2, Arts. 3–6. citeturn25view1turn22view0 | Fair labor, replacement-part assessment by category, production year, market value at event, insured sum, contractual franchise, rescue/transport, endorsements | Determine eligible repair cost; apply depreciation; apply underinsurance ratio when applicable; franchise; allowable rescue. Exact ratio/franchise ordering remains configurable. | `depreciation → {ratio/franchise configurable} → rescue` | Glass/lamp glass depreciation = 0; battery/tires capped at 50% new price; Article 5/6 gates; market-value evidence needed for underinsurance. |
| **Total loss — خسارت کلی** | Reg. 53 Art. 19(a); Central Insurance circular `1400/401/146850`. citeturn25view1turn4view0 | Market value, insured sum, repair/replacement + rescue estimate, salvage, franchise/other prescribed deductions, rescue/transport | `base = min(market_value, insured_sum)`; normal salvage-retained settlement: `base - salvage - deductions/franchise + allowable_rescue`, capped at insured sum | Salvage precedes total-loss franchise under the Central Insurance clarification. | No second underinsurance multiplier after insured-sum capping. If insurer takes title to salvage after disagreement, use the ownership-transfer path rather than subtracting salvage twice. |
| **Glass-only — شکست شیشه به تنهایی** | Reg. 53 Art. 19 depreciation exception plus actual glass endorsement/policy. citeturn25view1 | Cause, endorsement existence, glass and installation cost, policy franchise, market/insured value | If damage came from ordinary collision/fire/etc., use the underlying body branch. If it is independent breakage, require the glass endorsement. Glass depreciation = 0. | Franchise and underinsurance treatment must follow applicable endorsement/company procedure. | **No universal statutory 20% franchise located. No authoritative blanket Article-10 exemption located.** |
| **Theft — سرقت** | Reg. 53 Arts. 3 and 19. citeturn22view4turn25view1 | Whole vs partial theft; missing days; vehicle market/insured value; title transfer; theft/partial-theft terms; franchise | Whole vehicle unrecovered ≥60 days routes to theft-total settlement. Attempted theft damage can be partial damage. | Whole-theft settlement is its own branch; do not treat as ordinary repair loss. | Title is transferred to insurer before total-theft settlement. If recovered within one year after settlement/title transfer, Regulation 53 provides a recovery/sale sharing mechanism. |
| **Third-party financial — ثالث مالی** | Compulsory Third-Party Insurance Law 1395, especially Art. 8. citeturn4view2turn18search3 | Assessed damage, liability, damaged property type, damaged vehicle value if passenger car, purchased financial limit | Ordinary/conventional case: `min(legally assessed financial loss, policy_financial_limit)`. Excess beyond policy limit moves to legal-liability analysis. | No body-policy depreciation/franchise stack is imported automatically. | Before calculating, test whether passenger vehicle is conventional/non-conventional. |
| **Article 8 — ماده ۸ خودروی نامتعارف** | Art. 8 notes 3–4 + High Insurance Council instruction, amended `1398/06/13`. citeturn19view3turn19view2 | Annual bodily cap, threshold, victim vehicle market value, damaged components, corresponding conventional-car parts/repair values, TP financial limit | `TP_payable = min(corresponding_damage, policy_financial_limit)`; **do not derive corresponding damage with a whole-car-value ratio unless an authoritative current procedure explicitly requires it.** | Component correspondence first, policy financial cap second. | If exact part absent in conventional vehicle, use analogous part; where qualifying conventional models differ, the highest qualifying part value is used. |
| **Legal recovery — محاسبه حقوقی / جانشینی** | Reg. 53 Art. 14; Insurance Law valuation principles; TP law statutory recourse. citeturn22view1turn18search24turn18search3 | Judicial/expert award, insurer payment, responsible party, legal cap, subrogation status, releases/waivers | Not a body-formula engine. Determine legally recoverable loss, subtract prior compensation, impose statutory caps, then allocate rights between insured/insurer. | Legal entitlement first; insurance contribution/subrogation second. | For Article 8 cars, direct liability remains subject to the corresponding-damage cap. Impairing insurer recourse can trigger denial/recovery. |

### Shared operators

**Depreciation — استهلاک**

The base Regulation 53 operator is component-level, not vehicle-level. Replacement parts other than glass/lamp glass begin accruing depreciation in the fifth production year at 5% per production year, capped at 25%. citeturn25view1

```text
production_year_index =
    claim_year - production_year + 1

if production_year_index < 5:
    depreciation_rate = 0

else:
    depreciation_rate =
        min(
            0.25,
            0.05 × (production_year_index - 4)
        )
```

This conversion of the regulation into an arithmetic year index is an implementation interpretation. Exact treatment of manufacture dates crossing the Iranian calendar year should be confirmed against claims-department practice before production use.

Battery and tire claims need an additional special rule: Regulation 53 limits covered damage to these components to 50% of new price when damaged by an insured peril. citeturn22view0

The regulation does not expressly explain whether, for an old vehicle, the 50%-of-new battery/tire cap and Article 19 replacement-part depreciation are cumulative. That interaction should therefore be an uncertainty record rather than silently stacked.

**Franchise — فرانشیز**

At the regulatory level:

```text
franchise = policy-defined insured share of loss
```

not:

```text
franchise = universally 10%
```

or:

```text
glass_franchise = universally 20%
```

Regulation 53 expressly leaves the amount to the insurance contract. citeturn25view2

An Iran Insurance public FAQ surfaced in this research stating 10% for a first body claim and 20% from the next claim onward, but this is an **insurer practice**, not a statutory universal schedule, and it cannot safely be applied to other insurers, products, coverages or policy vintages. citeturn9search20

The implementation therefore needs:

```text
franchise:
    source = policy | endorsement | insurer_manual
    mode = absolute | percent | percent_with_minimum
    rate
    minimum
    calculation_base
    claim_sequence_rule
    coverage_specific_rule
    source_version
```

**Underinsurance ratio — قاعده نسبی / Article 10**

```text
underinsurance_ratio =
    min(
        1,
        insured_sum / actual_market_value_at_event
    )
```

Regulation 53 Article 20 note 2 says that where the insured amount is lower than the actual value on the event date, the insurer's liability is proportional to the ratio between the insured amount and real value. citeturn25view1turn25view2

For source-code clarity, use:

```text
UNDERINSURANCE_RATIO
```

as the canonical operator name and treat:

```text
ARTICLE_10
QAEDE_NESBI
قاعده_نسبی
ماده_10
```

as aliases.

**Salvage — ارزش بازیافتی**

For ordinary total-loss settlement where salvage remains with the insured:

```text
loss_after_salvage =
    covered_total_loss_base - probable_salvage_value
```

Central Insurance's 1400 clarification then places total-loss franchise after this salvage adjustment. citeturn4view0turn18search3

If salvage ownership transfers to the insurer following disagreement over its value, the engine should switch to a different disposition branch rather than both transferring the wreck and also subtracting its salvage price. Regulation 53 expressly provides for insurer ownership transfer in that circumstance. citeturn25view1

**Rescue and transport — نجات و حمل**

Regulation 53 covers reasonable rescue, mitigation and transportation to the nearest suitable repair location up to **20% of total damage**. Article 19 then adds permitted rescue/transport in partial and total settlement calculations, subject in total loss to the insured-sum ceiling. citeturn22view0turn25view1

**Liability cap — سقف تعهد**

The third-party engine has at least two independent caps:

```text
contractual_financial_limit
```

and, for a non-conventional passenger car:

```text
article8_corresponding_damage_cap
```

The payable amount is therefore bounded by both. citeturn19view3

### Annual dynamic parameters

Article 8 defines a conventional passenger car as one with market value **less than 50%** of the annual bodily-liability ceiling; a car at or above the threshold is non-conventional. The minimum third-party financial commitment is 2.5% of the bodily commitment. citeturn4view2turn19view3

Current 1405 secondary sources report a sacred-month full diyah of **2.8 billion tomans**. Applying the statutory formulas gives:

```text
1405 bodily reference          = 2,800,000,000 toman
conventional threshold         = 1,400,000,000 toman
minimum financial commitment   =    70,000,000 toman
```

The 1.4-billion and 70-million values are calculated results, not separately legislated figures. citeturn23search10

I did not retrieve a primary Judiciary-hosted 1405 diyah announcement through the official-domain searches conducted here. Therefore the current `1405` number should enter production as:

```json
{
  "value": 28000000000,
  "currency": "IRR",
  "source_tier": "secondary_current",
  "confidence": 0.86,
  "requires_primary_revalidation": true
}
```

The rule itself—50% for the conventional threshold and 2.5% for minimum financial cover—is primary-law material and has much higher confidence. citeturn4view2turn19view3

### Dual coverage and subrogation

Two superficially similar situations should not be merged.

**Multiple body insurance:** Regulation 53 Article 21 says that where the same vehicle/risk has multiple insurance contracts without fraudulent intent, the body insurer pays according to the rule and then pursues contribution from other insurers; there can be no double recovery by the insured. citeturn25view1

**Third-party + own body insurance for an Article 8 vehicle:** Central Insurance's circular dated `1404/06/10` expressly recognizes payment of the non-corresponding excess from the damaged owner's body policy. It also says there is no regulatory requirement to treat that specific body payment as a claims-history event or to deduct a franchise; an insurer that nevertheless intends to do either must disclose it transparently at issuance, with ambiguity interpreted in favor of the insured/beneficiary under Regulation 71. citeturn19view2

This yields:

```text
Actual damage to non-conventional car
                │
                ├── corresponding conventional damage
                │       │
                │       ├── TP insurer up to financial limit
                │       └── at-fault party may remain liable
                │           for unpaid amount inside this cap
                │
                └── non-corresponding excess
                        │
                        ├── own body insurance, if available
                        └── NOT automatically recoverable
                            from at-fault party beyond Art. 8 cap
```

This is one of the strongest reasons **not** to model Article 8 as merely another percentage multiplier. citeturn19view2turn19view3

## Executable schema and calculation functions

A production implementation should store money internally as integer **IRR**, even if user interfaces display tomans. It also needs provenance on every variable because the same numeric-looking parameter can come from law, an endorsement, an insurer manual or an adjuster's finding.

### JSON Schema

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "iran-auto-claim.schema.json",
  "title": "Iran Auto Claim Calculation Case",
  "type": "object",
  "required": [
    "claim_id",
    "regulatory_snapshot",
    "classification",
    "vehicle",
    "event",
    "policy",
    "evidence",
    "calculation_config"
  ],
  "properties": {
    "claim_id": {
      "type": "string"
    },

    "regulatory_snapshot": {
      "type": "object",
      "required": ["as_of_date"],
      "properties": {
        "as_of_date": {
          "type": "string",
          "format": "date"
        },
        "iranian_year": {
          "type": "integer"
        },
        "bodily_limit_irr": {
          "type": ["integer", "null"],
          "minimum": 0
        },
        "conventional_vehicle_threshold_irr": {
          "type": ["integer", "null"],
          "minimum": 0
        },
        "minimum_financial_limit_irr": {
          "type": ["integer", "null"],
          "minimum": 0
        },
        "annual_parameter_source": {
          "type": ["string", "null"]
        },
        "annual_parameter_confidence": {
          "type": ["number", "null"],
          "minimum": 0,
          "maximum": 1
        }
      }
    },

    "classification": {
      "type": "object",
      "required": ["domain", "branch"],
      "properties": {
        "domain": {
          "enum": [
            "BODY",
            "THIRD_PARTY_FINANCIAL",
            "LEGAL_RECOVERY"
          ]
        },
        "branch": {
          "enum": [
            "PARTIAL_DAMAGE",
            "TOTAL_LOSS",
            "GLASS_ONLY",
            "THEFT",
            "THIRD_PARTY_FINANCIAL",
            "ARTICLE_8_NON_CONVENTIONAL",
            "LEGAL_RECOVERY"
          ]
        },
        "classification_confidence": {
          "type": "number",
          "minimum": 0,
          "maximum": 1
        }
      }
    },

    "vehicle": {
      "type": "object",
      "required": ["market_value_at_event_irr"],
      "properties": {
        "vehicle_type": {
          "type": "string"
        },
        "is_passenger_car": {
          "type": "boolean"
        },
        "production_year_shamsi": {
          "type": ["integer", "null"]
        },
        "market_value_at_event_irr": {
          "type": "integer",
          "minimum": 0
        },
        "insured_sum_irr": {
          "type": ["integer", "null"],
          "minimum": 0
        },
        "salvage_value_irr": {
          "type": ["integer", "null"],
          "minimum": 0
        },
        "salvage_disposition": {
          "enum": [
            "NOT_APPLICABLE",
            "INSURED_RETAINS",
            "INSURER_TAKES_TITLE",
            "UNRESOLVED"
          ]
        }
      }
    },

    "event": {
      "type": "object",
      "properties": {
        "event_date": {
          "type": "string",
          "format": "date"
        },
        "cause": {
          "type": "string"
        },
        "days_vehicle_missing": {
          "type": ["integer", "null"],
          "minimum": 0
        },
        "fault_status": {
          "enum": [
            "INSURED_FAULT",
            "THIRD_PARTY_FAULT",
            "SHARED",
            "UNKNOWN",
            "NOT_APPLICABLE"
          ]
        },
        "intoxication_causally_confirmed": {
          "type": "boolean"
        },
        "valid_licence": {
          "type": ["boolean", "null"]
        }
      }
    },

    "damage": {
      "type": "object",
      "properties": {
        "labor_irr": {
          "type": "integer",
          "minimum": 0
        },
        "repair_total_irr": {
          "type": "integer",
          "minimum": 0
        },
        "rescue_transport_actual_irr": {
          "type": "integer",
          "minimum": 0
        },
        "actual_financial_loss_irr": {
          "type": ["integer", "null"],
          "minimum": 0
        },
        "article8_corresponding_damage_irr": {
          "type": ["integer", "null"],
          "minimum": 0
        },
        "parts": {
          "type": "array",
          "items": {
            "type": "object",
            "required": ["category", "assessed_loss_irr"],
            "properties": {
              "name": {
                "type": "string"
              },
              "category": {
                "enum": [
                  "GLASS",
                  "LAMP_GLASS",
                  "BATTERY",
                  "TIRE",
                  "OTHER_REPLACEMENT_PART",
                  "REPAIR_ONLY"
                ]
              },
              "new_price_irr": {
                "type": ["integer", "null"],
                "minimum": 0
              },
              "assessed_loss_irr": {
                "type": "integer",
                "minimum": 0
              },
              "requires_replacement": {
                "type": "boolean"
              },
              "article8_corresponding_part_irr": {
                "type": ["integer", "null"],
                "minimum": 0
              }
            }
          }
        }
      }
    },

    "policy": {
      "type": "object",
      "properties": {
        "insurer": {
          "type": ["string", "null"]
        },
        "policy_version": {
          "type": ["string", "null"]
        },
        "third_party_financial_limit_irr": {
          "type": ["integer", "null"],
          "minimum": 0
        },
        "endorsements": {
          "type": "array",
          "items": {
            "type": "string"
          }
        },
        "franchise": {
          "type": ["object", "null"],
          "properties": {
            "mode": {
              "enum": [
                "ABSOLUTE",
                "PERCENT",
                "PERCENT_WITH_MINIMUM"
              ]
            },
            "absolute_irr": {
              "type": ["integer", "null"]
            },
            "rate": {
              "type": ["number", "null"]
            },
            "minimum_irr": {
              "type": ["integer", "null"]
            },
            "calculation_base": {
              "type": ["string", "null"]
            },
            "source": {
              "enum": [
                "POLICY",
                "ENDORSEMENT",
                "INSURER_MANUAL",
                "UNKNOWN"
              ]
            },
            "source_reference": {
              "type": ["string", "null"]
            }
          }
        }
      }
    },

    "coverage_gate": {
      "type": "object",
      "properties": {
        "base_peril": {
          "type": "boolean"
        },
        "endorsement_restores_excluded_peril": {
          "type": "boolean"
        },
        "non_compensable_exclusion": {
          "type": "boolean"
        },
        "subrogation_impaired": {
          "type": "boolean"
        },
        "late_notice_issue": {
          "type": "boolean"
        }
      }
    },

    "evidence": {
      "type": "object",
      "properties": {
        "policy_terms_available": {
          "type": "boolean"
        },
        "expert_assessment_available": {
          "type": "boolean"
        },
        "market_value_evidence_available": {
          "type": "boolean"
        },
        "police_or_authority_record_available": {
          "type": "boolean"
        },
        "photos_available": {
          "type": "boolean"
        },
        "ownership_evidence_available": {
          "type": "boolean"
        },
        "article8_component_mapping_available": {
          "type": "boolean"
        }
      }
    },

    "calculation_config": {
      "type": "object",
      "required": ["article10_partial_order"],
      "properties": {
        "article10_partial_order": {
          "enum": [
            "AFTER_DEPRECIATION_BEFORE_FRANCHISE",
            "AFTER_DEPRECIATION_AND_FRANCHISE",
            "INSURER_SPECIFIC",
            "UNRESOLVED"
          ]
        },
        "battery_tire_depreciation_interaction": {
          "enum": [
            "CAP_THEN_DEPRECIATE",
            "DEPRECIATE_THEN_CAP",
            "CAP_ONLY",
            "INSURER_SPECIFIC",
            "UNRESOLVED"
          ]
        }
      }
    },

    "result": {
      "type": "object",
      "properties": {
        "payable_irr": {
          "type": ["integer", "null"]
        },
        "payable_scenarios_irr": {
          "type": "array",
          "items": {
            "type": "integer"
          }
        },
        "formula_confidence": {
          "type": "number",
          "minimum": 0,
          "maximum": 1
        },
        "blocking_uncertainties": {
          "type": "array",
          "items": {
            "type": "string"
          }
        },
        "rule_trace": {
          "type": "array",
          "items": {
            "type": "string"
          }
        }
      }
    }
  }
}
```

### Calculation pseudocode

The functions below encode only rules supported by the cited authorities. Where the authorities do not resolve an operation, the function returns an uncertainty rather than inventing a value. The partial-loss, total-loss, depreciation, rescue and underinsurance behavior comes from Regulation 53, with total-loss salvage/franchise ordering supplemented by the Central Insurance circular. citeturn22view0turn25view1turn4view0

```text
function underinsurance_ratio(insured_sum, market_value):
    require market_value > 0

    if insured_sum is null:
        return ERROR("insured sum required")

    return min(1, insured_sum / market_value)
```

```text
function replacement_part_depreciation_rate(
    production_year,
    claim_year,
    part_category
):
    if part_category in ["GLASS", "LAMP_GLASS"]:
        return 0

    year_index = claim_year - production_year + 1

    if year_index < 5:
        return 0

    return min(
        0.25,
        0.05 * (year_index - 4)
    )
```

```text
function apply_special_part_cap(part):
    if part.category not in ["BATTERY", "TIRE"]:
        return part.assessed_loss

    require part.new_price is known

    return min(
        part.assessed_loss,
        0.50 * part.new_price
    )
```

Because Regulation 53 does not expressly resolve the interaction between the battery/tire 50% cap and old-vehicle replacement-part depreciation, the next function deliberately halts if both operators might apply. citeturn22view0turn25view1

```text
function eligible_part_loss(part, vehicle_age, config):
    capped_loss = apply_special_part_cap(part)

    rate = replacement_part_depreciation_rate(
        production_year,
        claim_year,
        part.category
    )

    if part.category in ["BATTERY", "TIRE"] and rate > 0:
        if config.battery_tire_depreciation_interaction == "UNRESOLVED":
            return UNCERTAINTY(
                "battery/tire cap versus depreciation order"
            )

    return apply_configured_interaction(
        capped_loss,
        rate,
        config
    )
```

```text
function allowable_rescue_transport(actual_cost, gross_damage):
    statutory_cap = 0.20 * gross_damage

    return min(
        actual_cost,
        statutory_cap
    )
```

**Partial-damage engine**

```text
function calculate_partial_damage(case):
    assert case.branch == PARTIAL_DAMAGE

    coverage = evaluate_body_coverage(case)

    if coverage.status == NON_COMPENSABLE:
        return payable(0)

    if coverage.status == ENDORSEMENT_REQUIRED:
        return NEEDS_POLICY_TERM

    replacement_loss = 0

    for part in case.damage.parts:
        replacement_loss += eligible_part_loss(
            part,
            case.vehicle,
            case.calculation_config
        )

    gross_eligible =
        case.damage.labor
        + replacement_loss

    depreciation_amount =
        calculate_component_depreciation(case)

    after_depreciation =
        gross_eligible - depreciation_amount

    ratio = underinsurance_ratio(
        case.vehicle.insured_sum,
        case.vehicle.market_value_at_event
    )

    franchise = resolve_franchise_from_policy(case)

    rescue = allowable_rescue_transport(
        case.damage.rescue_transport_actual,
        gross_eligible
    )

    if ratio == 1:
        return max(
            0,
            after_depreciation
            - franchise
            + rescue
        )

    if case.calculation_config.article10_partial_order
        == AFTER_DEPRECIATION_BEFORE_FRANCHISE:

        return max(
            0,
            after_depreciation * ratio
            - franchise
            + rescue
        )

    if case.calculation_config.article10_partial_order
        == AFTER_DEPRECIATION_AND_FRANCHISE:

        return max(
            0,
            (after_depreciation - franchise)
            * ratio
            + rescue
        )

    return SCENARIO_SET(
        scenario_A =
            after_depreciation * ratio
            - franchise
            + rescue,

        scenario_B =
            (after_depreciation - franchise)
            * ratio
            + rescue,

        blocking_uncertainty =
            "Article 10 operator order requires insurer-level validation"
    )
```

That last branch is intentional: **an executable legal/claims engine should sometimes return “two sourced interpretations” instead of false precision.**

**Total-loss engine**

The 75% test is strict `>` rather than `>=`. The total settlement base is market value no greater than insured sum. citeturn25view1turn25view2

```text
function is_physical_total_loss(case):
    combined =
        case.damage.repair_and_replacement
        + case.damage.rescue_for_total_loss_test

    return combined >
        0.75 * case.vehicle.market_value_at_event
```

```text
function calculate_total_loss(case):
    assert is_physical_total_loss(case)

    base = min(
        case.vehicle.market_value_at_event,
        case.vehicle.insured_sum
    )

    rescue = allowable_rescue_transport(...)

    if case.vehicle.salvage_disposition == INSURED_RETAINS:
        after_salvage =
            base - case.vehicle.salvage_value

        franchise =
            resolve_total_loss_franchise(
                base = after_salvage
            )

        result =
            after_salvage
            - franchise
            - other_prescribed_deductions
            + rescue

    else if case.vehicle.salvage_disposition == INSURER_TAKES_TITLE:
        franchise =
            resolve_total_loss_franchise(...)

        result =
            base
            - franchise
            - other_prescribed_deductions
            + rescue

    else:
        return UNCERTAINTY("salvage disposition unresolved")

    return min(
        result,
        case.vehicle.insured_sum
    )
```

Critical guard:

```text
NEVER:

base = min(market_value, insured_sum)
base = base * underinsurance_ratio

because this applies underinsurance twice.
```

**Glass-only engine**

The absence of a statutory universal glass franchise is important. Glass depreciation, however, is resolved: zero under Article 19's replacement-part rule. citeturn25view1turn25view2

```text
function calculate_glass(case):
    if glass_damage_was_caused_by_base_body_peril(case):
        return calculate_partial_damage(case)

    if not case.policy.has("GLASS_ONLY_ENDORSEMENT"):
        return payable(0, reason="standalone peril not insured")

    depreciation = 0

    franchise =
        resolve_franchise_from_glass_endorsement(case)

    ratio =
        underinsurance_ratio(
            case.vehicle.insured_sum,
            case.vehicle.market_value_at_event
        )

    if ratio < 1 and
       article10_order_for_glass is not contractually_resolved:

        return SCENARIO_SET(
            blocking_uncertainty =
                "glass endorsement / Article 10 interaction"
        )

    return execute_configured_glass_pipeline(...)
```

**Theft engine**

Whole-vehicle theft is not just a partial-loss formula with a different deductible. Regulation 53 makes an unrecovered whole vehicle a total loss after at least 60 days, and requires title transfer before total-theft payment. citeturn25view1

```text
function calculate_theft(case):
    if case.theft_type == WHOLE_VEHICLE:
        if case.days_missing < 60:
            return PENDING

        require title_transfer_to_insurer

        return calculate_theft_total_settlement(case)

    if case.theft_type == ATTEMPTED_VEHICLE_THEFT_DAMAGE:
        return calculate_partial_damage(case)

    if case.theft_type == PARTIAL_PARTS_THEFT:
        return calculate_from_partial_theft_endorsement(case)
```

**Ordinary third-party financial engine**

Article 8's special vehicle-value rule should only activate after vehicle classification. citeturn4view2turn19view3

```text
function calculate_third_party_financial(case):
    if case.damaged_property != PASSENGER_VEHICLE:
        return min(
            legally_assessed_damage,
            policy_financial_limit
        )

    threshold =
        case.regulatory_snapshot.conventional_vehicle_threshold

    if case.vehicle.market_value_at_event < threshold:
        return min(
            legally_assessed_damage,
            policy_financial_limit
        )

    return calculate_article8(case)
```

**Article 8 engine**

The current instruction requires a component/repair correspondence assessment. It does not tell the calculator to multiply total repair cost by `threshold / luxury_vehicle_value`. citeturn19view3

```text
function calculate_article8(case):
    require case.vehicle.is_passenger_car
    require case.vehicle.market_value_at_event >= threshold
    require article8_component_mapping_available

    corresponding_damage = 0

    for damaged_component in case.damage.components:
        if same_component_exists_in_qualifying_conventional_vehicle:
            reference =
                highest_eligible_corresponding_component_value

        else:
            reference =
                similar_component_value_in_most_expensive_conventional_vehicle

        corresponding_damage +=
            assessed_corresponding_damage(
                damaged_component,
                reference
            )

    tp_payable = min(
        corresponding_damage,
        case.policy.third_party_financial_limit
    )

    return {
        "actual_damage": actual_damage,
        "corresponding_damage_cap": corresponding_damage,
        "tp_insurer_payable": tp_payable,
        "remaining_within_article8_cap":
            max(0, corresponding_damage - tp_payable),
        "non_corresponding_excess":
            max(0, actual_damage - corresponding_damage)
    }
```

The final field is a **body-insurance candidate**, not automatically a debt of the at-fault driver. Central Insurance's 1404 circular expressly supports use of the victim's own body policy for that excess. citeturn19view2

**Legal recovery and subrogation**

```text
function legal_recovery(case):
    legal_loss =
        court_or_authorized_expert_determination(case)

    if case.is_article8_nonconventional_vehicle:
        recoverable_against_tp_or_at_fault =
            min(
                legal_loss,
                article8_corresponding_damage
            )
    else:
        recoverable_against_tp_or_at_fault =
            legal_loss

    already_paid =
        sum(all_valid_prior_indemnities)

    remaining =
        max(
            0,
            recoverable_against_tp_or_at_fault
            - already_paid
        )

    return remaining
```

For body-insurer subrogation, Regulation 53 Article 14 transfers the insured's rights against the responsible person to the insurer to the extent the insurer accepts or pays the claim. If the insured makes recovery difficult or impossible, the insurer can refuse payment or seek repayment. citeturn22view1turn21search10

```text
function body_subrogation(case):
    if insured_impaired_recovery_rights:
        return SUBROGATION_IMPAIRMENT_REVIEW

    insurer_recovery_right =
        min(
            body_amount_accepted_or_paid,
            legally_recoverable_amount
        )

    return insurer_recovery_right
```

The compulsory third-party statute has a different recourse structure: the insurer first protects the victim and may then recover from the at-fault party in specified statutory cases, including serious traffic violations and circumstances such as intentional conduct, intoxication/drug use, licensing defects and knowingly using a stolen vehicle. This recourse belongs in a separate `TP_INSURER_REGRESS` module rather than being confused with a deduction from the victim's claim. citeturn18search3turn4view1

## Contradiction matrix

This is the calibration backbone. A status of **configurable** means the engine must store the uncertainty and require a policy/manual/version before issuing one deterministic number.

| Topic | Source A / interpretation | Source B / competing evidence | Controlling authority | Resolution / engine status |
|---|---|---|---|---|
| **Article 10 execution order** | Reg. 53 Art. 19(b) describes partial loss as fair labor + replacement parts, after depreciation and franchise, then rescue/transport. citeturn25view1 | Art. 20 n.2 separately imposes proportional underinsurance liability but does not say whether its ratio runs before or after franchise. citeturn25view1 | Same High Insurance Council regulation | **UNRESOLVED.** Ratio itself is mandatory; insertion point relative to franchise must remain configurable until insurer procedure/official clarification is obtained. |
| **Glass franchise** | Market articles often present a simple glass-specific percentage; insurer FAQs also show company-specific body deductibles. | Reg. 53 defines franchise as the insured's portion whose amount is specified in the policy; no universal standalone-glass percentage is stated. Iran Insurance's public FAQ itself illustrates insurer-specific claim-order rates. citeturn25view2turn9search20 | Regulation 53 + actual policy/endorsement | **NO UNIVERSAL 20%.** Load product terms. |
| **Total-loss threshold** | Educational sources commonly state 75%. | Official Regulation 53 text is more precise: repair/replacement **including rescue must exceed 75%**; unrecovered whole theft reaches total-loss status after at least 60 days. citeturn22view1turn25view2 | Regulation 53 Art. 19 | **RESOLVED.** Use `> 0.75`, not `>= 0.75`. |
| **Article 8 calculation** | Some secondary material still describes a proportional formula using vehicle values. | The instruction as amended `1398/06/13` uses corresponding damage to the most expensive conventional car, with explicit same/similar-part rules. citeturn9search16turn19view3 | High Insurance Council amended instruction | **RESOLVED IN FAVOR OF COMPONENT CORRESPONDENCE.** Whole-car ratio must not be the primary current algorithm. |
| **Depreciation schedule** | Secondary summaries frequently narrow depreciation to “consumables” or present miscellaneous part tables. | Reg. 53 Art. 19 applies 5%/year from the fifth production year, max 25%, to replacement parts except glass/lamp glass; Art. 3 separately caps battery/tires at 50% of new price. citeturn22view0turn25view1 | Regulation 53 | **BASE RULE RESOLVED.** Battery/tire interaction with aging depreciation still needs operational validation. |
| **Franchise by coverage type** | Iran Insurance's public information shows company-specific body claim rates; commercial products may include deductible-removal endorsements. citeturn9search20turn16search34 | Regulation 53 itself supplies no universal rate table; the policy specifies the amount. citeturn25view2 | Regulation 53 + policy/endorsement | **CONFIGURABLE. Never globally hard-code 10%, 20%, fixed minimums, theft rates, or glass rates.** |
| **Total-loss salvage vs franchise** | A naive engine might deduct franchise from the full total-loss base and then salvage. | Central Insurance circular `1400/401/146850` states franchise is determined after probable salvage is deducted. citeturn4view0turn18search3 | Central Insurance clarification | **RESOLVED: salvage → franchise** for the ordinary salvage-retained route. |
| **Article 8 excess against at-fault person** | A widespread intuitive model says “TP pays capped amount, owner sues at-fault driver for all excess.” | Article 8/official Central Insurance guidance limits TP **or the at-fault party** to corresponding conventional-car damage; own body cover can handle the non-corresponding excess. citeturn19view2turn19view3 | Statute + Central Insurance circular | **REJECT unrestricted direct-excess model.** |
| **Article 10 in total loss** | Some calculators apply `min(market, insured)` and then multiply again by insured/market. | Art. 19 already caps total-loss base at insured sum; Art. 20 proportionality applied to a full market-value loss produces that same insured-sum result. citeturn25view1 | Regulation 53 | **Double application prohibited.** |
| **Glass exemption from Article 10** | Common simplified guides may treat glass as an isolated 20%-franchise claim with no other reduction. | Reg. 53 expressly exempts glass from **depreciation**, not from the general underinsurance rule. citeturn25view1 | Regulation 53 + actual glass endorsement | **UNPROVEN EXEMPTION. Configurable.** |

The insurer-manual portion remains materially incomplete. Public search produced an official Iran Insurance FAQ and official/general Regulation 53 material, but I did **not** retrieve sufficiently detailed, current, authoritative public claims manuals for Asia, Pasargad and Parsian that resolve the Article 10 ordering or provide a versioned franchise matrix. Secondary material about those companies exists, but using it as executable authority would violate the requested source hierarchy. An insurer adapter should therefore remain unpopulated until actual current manuals, endorsements or claims circulars are obtained.

## Validation corpus

The following are **synthetic Iranian claims test fixtures**, not records of actual customers. They are designed to exercise the sourced rules and, equally importantly, force the engine to return uncertainty where the source base does not justify one number.

To keep the fixtures readable, monetary values are in **million tomans**. Production code should convert all values to integer IRR. Cases `P01–TH33` implement Regulation 53's body rules; `TP34–A48` exercise the compulsory-law/Article 8 branches; `L49–L50` exercise subrogation. citeturn22view0turn25view1turn19view3turn19view2

```json
[
  {
    "id": "P01",
    "branch": "PARTIAL_DAMAGE",
    "unit": "million_toman",
    "inputs": {"market": 3000, "insured": 3000, "gross": 100, "depreciation": 0, "franchise": 10, "rescue": 0},
    "expected": {"payable": 90}
  },
  {
    "id": "P02",
    "branch": "PARTIAL_DAMAGE",
    "unit": "million_toman",
    "inputs": {"gross": 200, "depreciable_parts": 120, "depreciation_rate": 0.05, "franchise": 20, "rescue": 10},
    "expected": {"depreciation": 6, "payable": 184}
  },
  {
    "id": "P03",
    "branch": "PARTIAL_DAMAGE",
    "unit": "million_toman",
    "inputs": {"gross": 300, "depreciable_parts": 180, "depreciation_rate": 0.10, "franchise": 30, "rescue": 20},
    "expected": {"depreciation": 18, "payable": 272}
  },
  {
    "id": "P04",
    "branch": "PARTIAL_DAMAGE",
    "unit": "million_toman",
    "inputs": {"gross": 400, "depreciable_parts": 250, "depreciation_rate": 0.15, "franchise": 40, "rescue": 20},
    "expected": {"depreciation": 37.5, "payable": 342.5}
  },
  {
    "id": "P05",
    "branch": "PARTIAL_DAMAGE",
    "unit": "million_toman",
    "inputs": {"gross": 500, "depreciable_parts": 300, "depreciation_rate": 0.20, "franchise": 50, "rescue": 30},
    "expected": {"depreciation": 60, "payable": 420}
  },
  {
    "id": "P06",
    "branch": "PARTIAL_DAMAGE",
    "unit": "million_toman",
    "inputs": {"gross": 600, "depreciable_parts": 400, "depreciation_rate": 0.25, "franchise": 60, "rescue": 40},
    "expected": {"depreciation": 100, "payable": 480}
  },
  {
    "id": "P07",
    "branch": "PARTIAL_DAMAGE",
    "unit": "million_toman",
    "inputs": {"gross": 80, "replacement_parts": [{"type": "GLASS", "loss": 80}], "franchise": 16},
    "expected": {"depreciation": 0, "payable": 64}
  },
  {
    "id": "P08",
    "branch": "PARTIAL_DAMAGE",
    "unit": "million_toman",
    "inputs": {"battery_new_price": 40, "battery_loss": 40, "franchise": 2},
    "expected": {"eligible_before_other_terms": 20, "payable_if_no_further_deduction": 18, "flag": "BATTERY_50_PERCENT_CAP"}
  },
  {
    "id": "P09",
    "branch": "PARTIAL_DAMAGE",
    "unit": "million_toman",
    "inputs": {"tires_new_price": 100, "tire_loss": 100, "franchise": 5},
    "expected": {"eligible_before_other_terms": 50, "payable_if_no_further_deduction": 45, "flag": "TIRE_50_PERCENT_CAP"}
  },
  {
    "id": "P10",
    "branch": "PARTIAL_DAMAGE",
    "unit": "million_toman",
    "inputs": {"market": 4000, "insured": 3000, "gross": 400, "depreciation": 20, "franchise": 40},
    "expected": {"article10_ratio": 0.75, "scenario_ratio_then_franchise": 245, "scenario_franchise_then_ratio": 255, "status": "ORDER_UNRESOLVED"}
  },
  {
    "id": "P11",
    "branch": "PARTIAL_DAMAGE",
    "unit": "million_toman",
    "inputs": {"market": 4000, "insured": 2000, "gross": 500, "depreciation": 50, "franchise": 50, "rescue": 20},
    "expected": {"article10_ratio": 0.5, "scenario_ratio_then_franchise": 195, "scenario_franchise_then_ratio": 220, "status": "ORDER_UNRESOLVED"}
  },
  {
    "id": "P12",
    "branch": "PARTIAL_DAMAGE",
    "unit": "million_toman",
    "inputs": {"gross": 200, "franchise": 20, "actual_rescue": 60},
    "expected": {"rescue_cap": 40, "payable": 220}
  },
  {
    "id": "P13",
    "branch": "PARTIAL_DAMAGE",
    "unit": "million_toman",
    "inputs": {"peril": "FLOOD", "endorsement": false, "gross": 300},
    "expected": {"payable": 0, "reason": "EXCLUDED_WITHOUT_ENDORSEMENT"}
  },
  {
    "id": "P14",
    "branch": "PARTIAL_DAMAGE",
    "unit": "million_toman",
    "inputs": {"peril": "FLOOD", "endorsement": true, "gross": 300},
    "expected": {"payable": null, "status": "ENDORSEMENT_TERMS_REQUIRED"}
  },
  {
    "id": "P15",
    "branch": "PARTIAL_DAMAGE",
    "unit": "million_toman",
    "inputs": {"cause": "DRIVER_INTOXICATION_CAUSALLY_CONFIRMED", "gross": 250},
    "expected": {"payable": 0, "reason": "NON_COMPENSABLE"}
  },

  {
    "id": "T16",
    "branch": "TOTAL_LOSS",
    "unit": "million_toman",
    "inputs": {"market": 2000, "insured": 2000, "repair": 1600, "rescue_for_threshold": 50, "salvage": 300, "franchise": 100, "rescue_payable": 50},
    "expected": {"is_total": true, "payable": 1650}
  },
  {
    "id": "T17",
    "branch": "TOTAL_LOSS_TEST",
    "unit": "million_toman",
    "inputs": {"market": 2000, "repair": 1500, "rescue_for_threshold": 0},
    "expected": {"is_total": false, "reason": "EXACTLY_75_PERCENT_IS_NOT_MORE_THAN_75_PERCENT"}
  },
  {
    "id": "T18",
    "branch": "TOTAL_LOSS",
    "unit": "million_toman",
    "inputs": {"market": 2000, "insured": 2000, "repair": 1480, "rescue_for_threshold": 30, "salvage": 300, "franchise": 100, "rescue_payable": 30},
    "expected": {"is_total": true, "payable": 1630}
  },
  {
    "id": "T19",
    "branch": "TOTAL_LOSS",
    "unit": "million_toman",
    "inputs": {"market": 3000, "insured": 2400, "salvage": 400, "franchise": 120, "rescue_payable": 50},
    "expected": {"underinsurance_ratio_equivalent": 0.8, "settlement_base": 2400, "payable": 1930, "guard": "DO_NOT_APPLY_RATIO_TWICE"}
  },
  {
    "id": "T20",
    "branch": "TOTAL_LOSS",
    "unit": "million_toman",
    "inputs": {"market": 2000, "insured": 2500, "salvage": 300, "franchise": 100, "rescue_payable": 20},
    "expected": {"settlement_base": 2000, "payable": 1620}
  },
  {
    "id": "T21",
    "branch": "TOTAL_LOSS",
    "unit": "million_toman",
    "inputs": {"market": 2000, "insured": 2000, "salvage_disposition": "INSURER_TAKES_TITLE", "franchise": 100, "rescue_payable": 20},
    "expected": {"payable_if_no_other_deductions": 1920, "guard": "DO_NOT_DEDUCT_SALVAGE_AND_TRANSFER_IT"}
  },
  {
    "id": "T22",
    "branch": "TOTAL_THEFT",
    "unit": "million_toman",
    "inputs": {"days_missing": 59, "market": 1800, "insured": 1800},
    "expected": {"payable": null, "status": "60_DAY_TOTAL_LOSS_CRITERION_NOT_MET"}
  },
  {
    "id": "T23",
    "branch": "TOTAL_THEFT",
    "unit": "million_toman",
    "inputs": {"days_missing": 60, "market": 1800, "insured": 1800, "franchise": 180, "title_transferred": true},
    "expected": {"total_loss_criterion": true, "payable_if_no_other_deductions": 1620}
  },

  {
    "id": "G24",
    "branch": "GLASS_ONLY",
    "unit": "million_toman",
    "inputs": {"glass_endorsement": true, "market": 2500, "insured": 2500, "gross": 50, "franchise_from_policy": 10},
    "expected": {"depreciation": 0, "payable": 40}
  },
  {
    "id": "G25",
    "branch": "GLASS_ONLY",
    "unit": "million_toman",
    "inputs": {"glass_endorsement": false, "cause": "INDEPENDENT_BREAKAGE", "gross": 50},
    "expected": {"payable": 0, "reason": "NO_STANDALONE_COVER"}
  },
  {
    "id": "G26",
    "branch": "GLASS_ONLY",
    "unit": "million_toman",
    "inputs": {"cause": "COLLISION", "gross": 50, "franchise": 5},
    "expected": {"route": "PARTIAL_DAMAGE", "depreciation": 0, "payable": 45}
  },
  {
    "id": "G27",
    "branch": "GLASS_ONLY",
    "unit": "million_toman",
    "inputs": {"glass_endorsement": true, "market": 3000, "insured": 2400, "gross": 100, "franchise": 20},
    "expected": {"article10_ratio": 0.8, "scenario_ratio_then_franchise": 60, "scenario_franchise_then_ratio": 64, "status": "ENDORSEMENT_AND_ORDER_REQUIRED"}
  },
  {
    "id": "G28",
    "branch": "PARTIAL_DAMAGE",
    "unit": "million_toman",
    "inputs": {"lamp_glass": 20, "other_replacement_part": 40, "other_part_depreciation_rate": 0.05, "franchise": 6},
    "expected": {"glass_depreciation": 0, "other_depreciation": 2, "payable": 52}
  },

  {
    "id": "TH29",
    "branch": "THEFT",
    "unit": "million_toman",
    "inputs": {"theft_type": "WHOLE_VEHICLE", "days_missing": 30},
    "expected": {"status": "PENDING_60_DAY_CRITERION"}
  },
  {
    "id": "TH30",
    "branch": "THEFT",
    "unit": "million_toman",
    "inputs": {"theft_type": "WHOLE_VEHICLE", "days_missing": 65, "market": 2200, "insured": 2200, "franchise": 220, "title_transferred": true},
    "expected": {"route": "THEFT_TOTAL_SETTLEMENT", "payable_if_no_other_deductions": 1980}
  },
  {
    "id": "TH31",
    "branch": "THEFT",
    "unit": "million_toman",
    "inputs": {"theft_type": "ATTEMPTED_VEHICLE_THEFT_DAMAGE", "gross": 50, "franchise": 5},
    "expected": {"route": "THEFT_PARTIAL_DAMAGE", "payable_if_fully_insured": 45}
  },
  {
    "id": "TH32",
    "branch": "THEFT",
    "unit": "million_toman",
    "inputs": {"theft_type": "PARTS_STOLEN_AFTER_ACCIDENT", "gross": 80, "endorsement": false},
    "expected": {"payable": 0, "reason": "BASE_POLICY_EXCLUSION"}
  },
  {
    "id": "TH33",
    "branch": "THEFT",
    "unit": "million_toman",
    "inputs": {"theft_type": "PARTIAL_PARTS_THEFT", "gross": 100, "partial_theft_endorsement": true},
    "expected": {"payable": null, "status": "ENDORSEMENT_LIMIT_AND_FRANCHISE_REQUIRED"}
  },

  {
    "id": "TP34",
    "branch": "THIRD_PARTY_FINANCIAL",
    "unit": "million_toman",
    "inputs": {"victim_vehicle_value": 1000, "actual_damage": 60, "policy_financial_limit": 70, "conventional_threshold": 1400},
    "expected": {"vehicle_class": "CONVENTIONAL", "insurer_payable": 60}
  },
  {
    "id": "TP35",
    "branch": "THIRD_PARTY_FINANCIAL",
    "unit": "million_toman",
    "inputs": {"victim_vehicle_value": 1000, "actual_damage": 100, "policy_financial_limit": 70, "conventional_threshold": 1400},
    "expected": {"vehicle_class": "CONVENTIONAL", "insurer_payable": 70, "remaining_legal_claim_candidate": 30}
  },
  {
    "id": "TP36",
    "branch": "THIRD_PARTY_FINANCIAL",
    "unit": "million_toman",
    "inputs": {"victim_vehicle_value": 1399, "actual_damage": 70, "policy_financial_limit": 70, "conventional_threshold": 1400},
    "expected": {"vehicle_class": "CONVENTIONAL", "insurer_payable": 70}
  },
  {
    "id": "TP37",
    "branch": "THIRD_PARTY_FINANCIAL",
    "unit": "million_toman",
    "inputs": {"victim_vehicle_value": 1400, "actual_damage": 70, "policy_financial_limit": 70, "conventional_threshold": 1400},
    "expected": {"vehicle_class": "NON_CONVENTIONAL", "route": "ARTICLE_8"}
  },
  {
    "id": "TP38",
    "branch": "THIRD_PARTY_FINANCIAL",
    "unit": "million_toman",
    "inputs": {"victim_vehicle_value": 900, "actual_damage": 30, "policy_financial_limit": 200, "conventional_threshold": 1400},
    "expected": {"vehicle_class": "CONVENTIONAL", "insurer_payable": 30}
  },
  {
    "id": "TP39",
    "branch": "THIRD_PARTY_FINANCIAL",
    "unit": "million_toman",
    "inputs": {"property_type": "NON_VEHICLE_PROPERTY", "actual_damage": 50, "policy_financial_limit": 70},
    "expected": {"insurer_payable": 50, "article8_vehicle_cap": "NOT_APPLICABLE"}
  },

  {
    "id": "A40",
    "branch": "ARTICLE_8_NON_CONVENTIONAL",
    "unit": "million_toman",
    "inputs": {"vehicle_value": 1400, "actual_damage": 120, "corresponding_damage": 80, "policy_financial_limit": 200, "threshold": 1400},
    "expected": {"insurer_payable": 80, "own_body_excess_candidate": 40}
  },
  {
    "id": "A41",
    "branch": "ARTICLE_8_NON_CONVENTIONAL",
    "unit": "million_toman",
    "inputs": {"vehicle_value": 2500, "actual_damage": 300, "corresponding_damage": 180, "policy_financial_limit": 200, "threshold": 1400},
    "expected": {"insurer_payable": 180, "own_body_excess_candidate": 120}
  },
  {
    "id": "A42",
    "branch": "ARTICLE_8_NON_CONVENTIONAL",
    "unit": "million_toman",
    "inputs": {"vehicle_value": 2500, "actual_damage": 300, "corresponding_damage": 180, "policy_financial_limit": 100, "threshold": 1400},
    "expected": {"insurer_payable": 100, "remaining_inside_article8_cap": 80, "own_body_non_corresponding_excess_candidate": 120}
  },
  {
    "id": "A43",
    "branch": "ARTICLE_8_NON_CONVENTIONAL",
    "unit": "million_toman",
    "inputs": {"vehicle_value": 3000, "actual_damage": 200, "similar_part_corresponding_damage": 90, "policy_financial_limit": 200},
    "expected": {"insurer_payable": 90, "own_body_excess_candidate": 110}
  },
  {
    "id": "A44",
    "branch": "ARTICLE_8_NON_CONVENTIONAL",
    "unit": "million_toman",
    "inputs": {"vehicle_value": 3500, "actual_damage": 400, "corresponding_damage": 250, "policy_financial_limit": 200},
    "expected": {"insurer_payable": 200, "remaining_inside_article8_cap": 50, "own_body_non_corresponding_excess_candidate": 150}
  },
  {
    "id": "A45",
    "branch": "ARTICLE_8_NON_CONVENTIONAL",
    "unit": "million_toman",
    "inputs": {"vehicle_value": 3500, "actual_damage": 400, "corresponding_damage": 250, "policy_financial_limit": 500},
    "expected": {"insurer_payable": 250, "own_body_excess_candidate": 150}
  },
  {
    "id": "A46",
    "branch": "ARTICLE_8_NON_CONVENTIONAL",
    "unit": "million_toman",
    "inputs": {"vehicle_value": 3500, "actual_damage": 400, "corresponding_damage": 250, "policy_financial_limit": 500, "has_body_policy": false},
    "expected": {"tp_or_at_fault_statutory_cap": 250, "non_corresponding_residual": 150}
  },
  {
    "id": "A47",
    "branch": "ARTICLE_8_DUAL_COVERAGE",
    "unit": "million_toman",
    "inputs": {"vehicle_value": 2500, "actual_damage": 300, "corresponding_damage": 180, "tp_limit": 200, "has_body_policy": true, "body_franchise_for_excess_disclosed": false},
    "expected": {"third_party": 180, "body_candidate_before_other_body_terms": 120, "regulatory_mandatory_franchise_on_this_excess": 0}
  },
  {
    "id": "A48",
    "branch": "ARTICLE_8_DUAL_COVERAGE",
    "unit": "million_toman",
    "inputs": {"vehicle_value": 2500, "actual_damage": 300, "corresponding_damage": 180, "tp_limit": 200, "has_body_policy": true, "body_franchise_for_excess_disclosed": true},
    "expected": {"third_party": 180, "body_candidate_before_disclosed_terms": 120, "franchise": "APPLY_VALID_DISCLOSED_POLICY_TERM"}
  },

  {
    "id": "L49",
    "branch": "LEGAL_RECOVERY",
    "unit": "million_toman",
    "inputs": {"body_insurer_paid": 150, "responsible_third_party_identified": true, "insured_preserved_recovery_rights": true},
    "expected": {"insurer_subrogation_ceiling": 150, "status": "INSURER_MAY_PURSUUE_RESPONSIBLE_PARTY"}
  },
  {
    "id": "L50",
    "branch": "LEGAL_RECOVERY",
    "unit": "million_toman",
    "inputs": {"body_insurer_paid": 150, "insured_released_responsible_party": true, "recovery_right_impaired": true},
    "expected": {"payable_or_recovery_amount": null, "status": "ARTICLE_14_SUBROGATION_IMPAIRMENT_REVIEW"}
  }
]
```

Several cases intentionally have `null` rather than a guessed payout. That behavior is a feature. For example, P10/P11/G27 demonstrate that a claim can be perfectly classified while its final amount remains unresolved because the primary text does not settle operator order. P14 and TH33 show a different type of incompleteness: the law identifies the coverage architecture, but the **endorsement** provides the missing economic parameters. citeturn25view1turn25view2

Cases A40–A48 embody another important distinction: `corresponding_damage` is an **assessment result** produced by the Article 8 component-comparison process, not a number the engine should manufacture from a luxury-car/conventional-car value ratio. citeturn19view3

## Confidence, unresolved questions, and source register

### Confidence model

These confidence scores are **research-engine confidence scores**, not probabilities that a court or insurer will decide a case in a particular way.

| Rule | Confidence | Reason |
|---|---:|---|
| Reg. 53 total-loss threshold `>75%` | **0.99** | Explicit regulatory text |
| Whole-theft 60-day total-loss criterion | **0.99** | Explicit regulatory text |
| Total-loss market value capped at insured sum | **0.99** | Explicit regulatory text |
| Glass/lamp-glass depreciation exemption | **0.99** | Explicit regulatory text |
| Replacement-part 5% annual depreciation from fifth year, max 25% | **0.99** | Explicit regulatory text |
| Battery/tire 50% new-price cap | **0.98** | Explicit regulatory text |
| Underinsurance ratio existence | **0.99** | Explicit Regulation 53 note |
| Partial-loss Article 10/franchise operator order | **0.55** | Both operators are explicit, their relative sequence is not |
| Total-loss salvage before franchise | **0.96** | Central Insurance clarification directly addresses issue |
| Universal glass franchise of 20% | **0.10** | No universal regulatory support found |
| Glass depreciation = 0 | **0.99** | Explicit |
| Glass universally exempt from underinsurance | **0.20** | No authoritative exemption found |
| Article 8 threshold test `<50%` versus `>=50%` | **0.99** | Explicit amended instruction |
| Article 8 corresponding-component method | **0.98** | Explicit amended instruction |
| Whole-car proportional Article 8 ratio as current default | **0.10** | Conflicts with current amended instruction located |
| Article 8 non-corresponding excess eligible for own body insurance | **0.99** | Current Central Insurance circular |
| Mandatory franchise on Article 8 body-excess payment | **0.05** | Central Insurance says no regulatory mandate; disclosure can create contractual treatment |
| 1405 sacred-month diyah = 2.8bn toman | **0.86** | Current secondary sources agree, but primary Judiciary source not retrieved |
| Derived 1405 conventional threshold = 1.4bn toman | **0.86** | Arithmetic from current secondary annual parameter + primary 50% rule |
| Derived minimum 1405 financial cover = 70m toman | **0.86** | Arithmetic from current secondary annual parameter + primary 2.5% rule |
| Reg. 53 body-insurer subrogation | **0.99** | Explicit Article 14 |
| Insurer-specific franchise tables for Asia/Pasargad/Parsian | **0.35** | Current authoritative manuals not obtained |

### Unknowns requiring claims-department or regulator validation

The highest-priority calibration request is **not another batch of general internet articles**. It is a small set of insurer/internal documents.

**Article 10 ordering.** Obtain a current claims calculation worksheet or official claims circular from Iran Insurance, Asia, Pasargad, Parsian and at least two private insurers showing a single underinsured partial-loss example with gross parts/labor, depreciation, franchise and final payment. That will reveal whether the industry executes:

```text
(loss - depreciation) × ratio - franchise
```

or:

```text
(loss - depreciation - franchise) × ratio
```

or a third implementation. Regulation 53 itself does not settle that placement clearly enough for a high-confidence universal engine. citeturn25view1

**Franchise base.** For every coverage/product/version, acquire the actual schedule defining first/second/subsequent claims, minimum deductible, theft, partial theft, glass, natural disaster, driver-age/licence surcharges, and deductible-removal endorsements. Regulation 53 deliberately leaves franchise amount to the policy. citeturn25view2

**Glass-only conditions.** Acquire the wording of each insurer's شکست شیشه به تنهایی endorsement. The engine specifically needs: covered causes, whether installation is included, rate/minimum franchise, underinsurance treatment, claim-history treatment, and any glass valuation ceiling. The only universal calculation fact established here is the Regulation 53 depreciation exclusion for glass/lamp glass. citeturn25view1

**Battery/tire interaction.** Ask whether the 50%-new-price ceiling in Article 3 and the Article 19 age depreciation schedule stack for older vehicles, and in which order. Both rules exist, but their interaction is not expressly described in the text located. citeturn22view0turn25view1

**Rescue denominator.** Regulation 53 gives a 20%-of-total-damage ceiling for rescue/mitigation/transport costs. Claims departments should confirm the precise computational denominator they use where underinsurance, depreciation or total-loss classification is also involved. citeturn22view0

**Article 8 component catalogue.** The biggest practical missing dataset is not a legal formula; it is the valuation map that turns damaged luxury/non-conventional components into their “corresponding” or “similar” components in the most expensive qualifying conventional vehicle. The amended instruction delegates that work to adjusters/official experts. A production engine therefore needs either insurer valuation tables or a human-assessor input—not a guessed price ratio. citeturn19view3

**Annual conventional-car reference set.** The law gives a value threshold, not a permanently named model. The engine needs annual/continuous market valuation capable of identifying the qualifying conventional reference vehicle(s), because the instruction directs assessors to choose the highest relevant part price where multiple qualifying conventional cars differ. citeturn19view3

**1405 primary annual data.** Replace the current secondary diyah input with the Judiciary's primary announcement or an official Central Insurance annual third-party schedule before certification. The legal formulas can remain static while the annual parameter table changes.

**Diminution of value — افت قیمت.** Regulation 53 expressly excludes reduction in the insured vehicle's value from the base body policy. That does **not** justify reusing the same exclusion automatically in third-party/legal recovery. Because third-party diminution rules have their own regulatory history, that subject should be implemented as a separate current-law module rather than inferred from body insurance. citeturn22view4

**“Immediate cause” terminology.** Do not create an `IMMEDIATE_CAUSE_VALUE` multiplier. Store causation as a coverage/exclusion predicate. Separately store the Insurance Law Article 19 before/after-event valuation concept where the legal engine needs it. citeturn18search24

### Recommended knowledge-graph primitives

The resulting graph should use nodes such as:

```text
Claim
Vehicle
Policy
PolicyVersion
Peril
Exclusion
Endorsement
LegalRule
RegulatoryInstruction
InsurerProcedure
Evidence
DamageComponent
Valuation
Operator
OperatorOrder
AnnualParameter
CorrespondingArticle8Component
Payment
SubrogationRight
Uncertainty
Contradiction
```

and edges such as:

```text
Claim ──classified_as──► Branch

Branch ──governed_by──► LegalRule

Claim ──requires──► Evidence

DamageComponent ──subject_to──► DepreciationOperator

Glass ──exempt_from──► DepreciationOperator

Claim ──subject_to──► UnderinsuranceRatio

FranchiseOperator ──configured_by──► PolicyVersion

Article8Claim ──mapped_to──► CorrespondingArticle8Component

Rule ──contradicts──► SecondaryTemplate

Uncertainty ──resolved_by──► InsurerProcedure

BodyPayment ──creates──► SubrogationRight
```

Every executable rule should carry provenance:

```json
{
  "rule_id": "REG53_ART19_PARTIAL_DEPRECIATION",
  "source_class": "REGULATION",
  "authority": "High Insurance Council",
  "instrument": "Regulation 53",
  "article": "19(b)",
  "effective_version": "current-researched-version",
  "rule": {
    "replacement_part_depreciation_start_year": 5,
    "annual_rate": 0.05,
    "maximum_rate": 0.25,
    "excluded_part_categories": [
      "GLASS",
      "LAMP_GLASS"
    ]
  },
  "confidence": 0.99
}
```

A contradiction should likewise be data, not prose:

```json
{
  "contradiction_id": "ARTICLE8_RATIO_VS_COMPONENT_METHOD",
  "topic": "ARTICLE_8_CALCULATION",
  "candidate_rule": "damage * conventional_threshold / damaged_vehicle_value",
  "candidate_source_class": "EDUCATIONAL",
  "controlling_rule": "component-wise corresponding damage",
  "controlling_source_class": "HIGH_INSURANCE_COUNCIL_INSTRUCTION",
  "controlling_amendment_date": "1398/06/13",
  "resolution": "REJECT_CANDIDATE_AS_PRIMARY_METHOD",
  "confidence": 0.98
}
```

That structure turns recalibration into a controlled database migration rather than rewriting formulas whenever an insurer FAQ changes.

### Source register

**[REGULATION / PRIMARY COMPILATION] Central Insurance of Iran — “بیمه‌های خودرو.”** This Central Insurance PDF compiles the relevant motor-insurance regulations, statutory material and circulars, including Regulation 53 and the `1400/401/146850` clarification used for salvage/franchise analysis. Accessed September 18, 2026. citeturn18search3turn4view0
URL: `https://centinsur.ir/_douranportal/documents/2277/carinsurance.pdf`

**[REGULATION / OFFICIAL INSURER COPY] Iran Insurance — “آیین نامه شماره 53.”** Regulation 53, High Insurance Council approval date `1384/12/09`. Searchable official insurer copy; direct open timed out during research, so clause-level cross-checking used the Central Insurance compilation and complete mirror below. citeturn18search0
URL: `https://www.iraninsurance.ir/fa/w/%D8%A2%DB%8C%DB%8C%D9%86-%D9%86%D8%A7%D9%85%D9%87-%D8%B4%D9%85%D8%A7%D8%B1%D9%87-53-5`

**[REGULATION MIRROR / SECONDARY HOST] Complete text of Regulation 53.** Used to inspect Articles 3–6, 10–14 and 19–24 against the official Central Insurance compilation. It states the policy-defined franchise, rescue-cost ceiling, exclusions, subrogation, total/partial-loss rules, depreciation and underinsurance provision. Accessed September 18, 2026. citeturn22view0turn22view1turn25view1turn25view2
URL: `https://www.gostareshins.com/%D8%A2%D8%A6%DB%8C%D9%86-%D9%86%D8%A7%D9%85%D9%87-%D8%B4%D9%85%D8%A7%D8%B1%D9%87-53-%D8%A8%DB%8C%D9%85%D9%87-%D8%A8%D8%AF%D9%86%D9%87-%D8%AE%D9%88%D8%AF%D8%B1%D9%88.html`

**[HIGH INSURANCE COUNCIL INSTRUCTION] Article 8 corresponding-damage instruction.** Approved `1396/05/29`; definitions and calculation provisions amended `1398/06/13`. The current displayed text defines `<50%` as conventional, `>=50%` as non-conventional and specifies same/similar-component correspondence. citeturn19view3
URL: `https://davoudabadi.ir/page/90973652`

**[CENTRAL INSURANCE CIRCULAR / PRIMARY] Central Insurance circular concerning non-conventional vehicles and own body insurance.** Dated `1404/06/10`. It confirms that Article 8's non-corresponding excess may be compensated by the victim's own body policy and that franchise/claim-history treatment for this payment is not regulatorily mandatory unless properly disclosed by the insurer. citeturn19view2
URL: `https://www.centinsur.ir/fa-IR/Portal/1/news/view/15628/5736/Staging`

**[LAW / PRIMARY MATERIAL WITHIN CENTRAL INSURANCE COMPILATION] Compulsory Third-Party Insurance Law 1395.** Article 8 establishes minimum bodily and financial commitments, the non-conventional-vehicle limitation, and the 50% conventional-vehicle definition. The Central Insurance motor-insurance compilation was used as the authoritative accessible source. citeturn4view2turn18search3
URL: `https://centinsur.ir/_douranportal/documents/2277/carinsurance.pdf`

**[INSURER PRACTICE] Iran Insurance public claims FAQ — “آنالیز خسارت پرداختی چگونه است؟”** The indexed official page reports insurer-specific body-franchise treatment, illustrating why deductible rates must live in insurer/policy configuration rather than statutory constants. The page itself timed out when opened during the research, so it should not be elevated above the actual policy wording. Accessed September 18, 2026. citeturn9search20
URL: `https://iraninsurance.ir/fa/w/%D8%A2%D9%86%D8%A7%D9%84%DB%8C%D8%B2-%D8%AE%D8%B3%D8%A7%D8%B1%D8%AA-%D9%BE%D8%B1%D8%AF%D8%A7%D8%AE%D8%AA%DB%8C-%DA%86%DA%AF%D9%88%D9%86%D9%87-%D8%A7%D8%B3%D8%AA%D8%9F`

**[CURRENT PARAMETER / SECONDARY] Bimeh.com — 1405 diyah table.** Current secondary source reporting the 1405 sacred-month full diyah at 2.8 billion tomans. This report uses it provisionally to derive the 1.4-billion-toman Article 8 threshold and 70-million-toman minimum financial commitment, while expli
[truncated]