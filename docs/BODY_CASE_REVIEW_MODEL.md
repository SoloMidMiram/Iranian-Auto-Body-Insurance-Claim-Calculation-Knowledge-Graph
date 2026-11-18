# Body-insurance case review and calculation model

> Compact FAQ-facing architecture: [Body Claim Acceptance Model](BODY_CLAIM_ACCEPTANCE_MODEL.md).
> This file is the detailed review procedure and generated implementation reference.

Scope: **بیمه بدنه** — monetary damage to the insured vehicle itself, under the
general conditions of Regulation 53. Not bodily injury, and not the third-party
branches, which the same graph carries separately (`THIRD_PARTY_FINANCIAL`,
`ARTICLE_8_NON_CONVENTIONAL`, `LEGAL_RECOVERY`).

This document describes the layer that decides *what to calculate*, and it sits in
front of the calculation engine that is already documented in
[README.md](../README.md). The engine answers "what is the amount, on which
authority, with what confidence". This layer answers the two questions that must be
settled before it may be asked at all: **has this claim been investigated far enough
to be classified**, and **is every parameter it will consume actually sourced**.

| Concern | Where it lives |
|---|---|
| What happened, and what evidence proves it | `knowledge/review_procedure.json`, `knowledge/evidence_items.json` |
| Which values the calculation needs, and who may supply them | `knowledge/parameter_slots.json` |
| How complex the case is, and what may be issued | `knowledge/case_tiers.json` |
| Branch, operators, order, caps | `knowledge/branches.json`, `knowledge/operators.json` |
| Law, policy terms, provenance, confidence | `knowledge/rules.json`, `knowledge/sources.json`, `knowledge/uncertainties.json` |
| Arithmetic and guardrails | `src/iran_auto_claim/{operators,guards,engine}.py` |

## 1. The model

Five stages, each of which may only consume what the previous one produced:

```
FILE            establish dates, parties, cover in force, territorial scope
  |             -> evidence items demanded by Regulation 53 vs by insurer procedure
  v
INVESTIGATION   gate-ordered questions; each answer is a token or a measurement
  |             -> parameter slots bound, UNKNOWN recorded as absence
  v
CLASSIFICATION  coverage gate, then the branch decision tree
  |             -> PARTIAL_DAMAGE | TOTAL_LOSS | GLASS_ONLY | THEFT | (other domains)
  v
PARAMETER LOCK  operator order, caps, bases, dispositions - each with a source
  |             -> or left UNRESOLVED, which forces a scenario set later
  v
DECISION        COMPUTE | SCENARIO_SET | REFUSE | INSUFFICIENT_INFORMATION
```

Three invariants hold everywhere in this layer:

1. **A questionnaire can select knowledge, never create it.** Answers bind declared
   `ParameterSlot` nodes; a slot names the operator that reads it and the rule that
   governs it. A binding that carries a numeric literal fails
   `python claim.py validate`, because an intake form is not a source of law
   (`test_a_questionnaire_answer_can_never_carry_an_amount`).
2. **Absence is a recorded state.** `UNKNOWN`, `NOT_STATED` and `NOT_REVIEWED` are
   admissible answers that bind nothing. A slot the file cannot fill is reported as
   `UNANSWERED`, `NOT_TRIGGERED`, `NOT_APPLICABLE` or `MISSING` — and the decision
   stops. Nothing in this layer defaults a franchise to zero or a ratio to one.
3. **The decision belongs to the review layer; the outcome belongs to the engine.**
   Review says whether a file may be run. The engine then says what the claim is
   worth — including "pending" and "nothing payable", which are outcomes, not
   review failures. An unanchored whole-vehicle theft file remains insufficient:
   its stored day-count does not identify a clock anchor, so U13 stops the handoff.
   A complete review can now bind and emit the sourced clock instead.

## 2. Execution model

Three diagrams, all printed by `python claim.py flowchart` and parity-checked
in `tests/test_review.py`. They describe how a file is accepted and how this
repository runs. They are not a picture of one payable.

### 2.1 Acceptance pipeline

The stages come from the graph. Every path ends at one gate. A missing
franchise, a missing production year, an unresolved operator order, an unread
endorsement, or a live risk-intensification flag stops here. The engine is not
asked to fill the gap with zero, with a ratio of one, or with the underinsurance
ratio standing in for a premium ratio.

<!-- BEGIN GENERATED: flowchart -->

```mermaid
flowchart TD
  START "Claim file opened" --> S0 "0. Establish the file"
  S0 --> S1 "1. Identify the insured subject"
  S1 --> S2 "2. Establish what happened and what caused it"
  S2 --> S3 "3. Test cover before computing"
  S3 --> S4 "4. Scope and classify the damage"
  S4 --> S5 "5. Fix the value anchors"
  S5 --> S6 "6. Read the contract's own economics"
  S6 --> S7 "7. Classify the branch"
  S7 --> S8 "8. Lock the operators and their order"
  S8 --> S9 "9. Allocation, recourse and double cover"
  S9 --> S10 "10. Decide what may be issued"
  S10 --> GATE {"Decision gate"}
  GATE -- cover defeated --> REFUSE "REFUSE: name the provision, run no arithmetic"
  GATE -- a required question is open --> INSUF "INSUFFICIENT_INFORMATION: print the question"
  GATE -- a blocking uncertainty is live --> SCEN "SCENARIO_SET: do not pick or average"
  GATE -- classified and sourced --> RUN "COMPUTE: hand the case to the engine"
  REFUSE --> TRACE "Trace: rules, provenance, confidence"
  INSUF --> TRACE
  SCEN --> TRACE
  RUN --> TRACE
```

<!-- END GENERATED: flowchart -->

The gate has four exits: refuse with the provision named, print the open
question, return a scenario set, or hand a sourced case to the engine. Nothing
in the investigation stages has an edge to a payment figure.

Cover that defeats payment is a refusal, and it is decided before arithmetic:
the policy is not in force, the loss is outside Iran with no agreement, the
stated cause is contradicted, the damage was intentional or caused in flight
from the police, another non-compensable condition applies, the licence is
missing, void, or the wrong class, intoxication is confirmed and causal, or the
vehicle was transferred after an accident that was never declared. An expired
licence is not in that list. An unpaid instalment on a policy the insurer has
not cancelled is not in it either: settlement then follows the private
conditions. `INSTALMENT_OVERDUE` therefore stops as
`INSUFFICIENT_INFORMATION` until cancellation and the private conditions are
resolved; `LAPSED` still refuses before arithmetic.

Two stops are enforced by review but not yet by direct `calc`. A missing
production year still yields depreciation of 0, and a missing franchise is
stored as 0 when calculation is called without the review gate. Review blocks
both incomplete inputs. U13 remains live for a whole-vehicle theft until the
questionnaire binds the start event, start date, as-of date, calendar, and source.
A count of 70 or a confirmed title transfer cannot clear it by itself. Once all
five clock fields exist, review emits `event.theft_clock`, U13 clears for that
file, and the engine verifies the stored day count against the derived interval.
A missing event year is omitted from review emission,
while direct `calc` still defaults to 1405 and remains work for P0-01/P1-02.

### 2.2 Knowledge graph to calculation engine

Review sits on this path because a file can be refused, or left insufficient,
without the engine inventing an input. `COMPUTE` and `SCENARIO_SET` are the
only edges into the engine.

<!-- BEGIN GENERATED: architecture -->

```mermaid
flowchart TD
  SRC "Sources"
  RULE "LegalRule, Circular, or Policy"
  KG "Knowledge graph"
  OG "Operator graph"
  VAL "Validation gate"
  REV "Review decision"
  ENG "Calculation engine"
  OUT "Result, provenance, confidence, uncertainty"
  SRC --> RULE
  RULE --> KG
  KG --> OG
  OG --> VAL
  VAL --> REV
  REV -- "COMPUTE or SCENARIO_SET" --> ENG
  REV -- "REFUSE or INSUFFICIENT" --> OUT
  ENG --> OUT
```

<!-- END GENERATED: architecture -->

### 2.3 Claim branch decision

Selection order is theft, then the 75% test, then standalone glass, then partial
damage. A repair that is not above 75% is not yet a partial loss: glass is
still open. Regulation wording and insurer procedure do not currently give this
repository one universal anchor for the 60-day theft clock, so `U13` must surface
whenever a case lacks a complete sourced clock. Reaching 60 days under that clock
without a title transfer is `TITLE_TRANSFER_REQUIRED`, which is a different stop
from `PENDING_60_DAY_CRITERION`. The declaration date also starts the insurer's
payment period; that is a separate clock.
Attempted-theft damage is partial damage. Parts taken after the accident are
an exclusion unless that endorsement has been read.

`review` derives the branch and emits that derivation. `calc` uses a branch
already written on the case and does not re-check it, so a contradictory
declaration has to be caught before that handoff.

<!-- BEGIN GENERATED: branch-tree -->

```mermaid
flowchart TD
  CLAIM "Cover gate passed"
  RECON "Reconcile a declared branch with the evidence"
  REFUSE "REFUSE before arithmetic"
  THEFT "Theft?"
  CLOCK "60-day clock under the sourced anchor, and title transferred?"
  PENDING "PENDING_60_DAY_CRITERION"
  TITLE "TITLE_TRANSFER_REQUIRED"
  TSET "Theft total settlement"
  EXCL "Exclusion unless that endorsement is read"
  TERMS "INSUFFICIENT: endorsement terms"
  TOTAL "Repair + replacement + rescue above 75% of day value?"
  TLOSS "Total loss settlement"
  GLASS "Standalone glass?"
  GCALC "Glass calculation, depreciation zero"
  INSUF "INSUFFICIENT_INFORMATION"
  PARTIAL "Partial damage"
  CLAIM --> RECON
  RECON -- "contradicts the evidence" --> REFUSE
  RECON -- "agrees, or none declared" --> THEFT
  THEFT -- "whole vehicle" --> CLOCK
  CLOCK -- "under 60 days" --> PENDING
  CLOCK -- "at least 60 days, no title" --> TITLE
  CLOCK -- "at least 60 days and title transferred" --> TSET
  THEFT -- "attempted theft" --> PARTIAL
  THEFT -- "parts after the accident" --> EXCL
  THEFT -- "partial parts theft" --> TERMS
  THEFT -- "not a theft" --> TOTAL
  TOTAL -- "above 75%" --> TLOSS
  TOTAL -- "not total" --> GLASS
  GLASS -- "endorsement read" --> GCALC
  GLASS -- "wording missing" --> INSUF
  GLASS -- "with other damage, or not glass" --> PARTIAL
```

<!-- END GENERATED: branch-tree -->

## 3. Investigation procedure

Eleven stages, each with a closing condition. A stage is *worked* when its
conditional questions have been either answered or gated off by an earlier answer,
which is why the report prints "not asked" separately from "still open": a battery
new price is not an omission on a claim with no battery damage.

| Stage | Closes when | Why it is a gate |
|---|---|---|
| S0 Establish the file | three event dates, insurer, driver, cover in force | every clock in this branch is event-dated |
| S1 Identify the insured subject | type, use, declared accessories matched to the proposal | the thing insured must match the thing damaged |
| S2 What happened and what caused it | one peril from the closed list, causation evidenced | peril selects branch, endorsement set and exclusion list |
| S3 Test cover before computing | non-compensable conditions excluded or escalated; endorsements separated from their terms | the two failure states must stay distinct |
| S4 Scope and classify the damage | per-component category, labour/parts split, theft or total-loss artefacts | component class selects the operators |
| S5 Fix the value anchors | market value, insured sum, production year all evidenced | three jobs from one figure: 75% test, ratio, settlement base |
| S6 Read the contract's own economics | franchise mode, rate, base, sequence, source version, other policies | the regulation leaves these to the policy |
| S7 Classify the branch | derived branch agrees with evidence, or an override is recorded | a declared branch that contradicts evidence is refused |
| S8 Lock the operators and their order | each configurable position has a source, or stays UNRESOLVED | order is data; locking it without a source is false precision |
| S9 Allocation, recourse, double cover | prior indemnity, other insurers, impairment of recourse | recovery is a separate entitlement computed afterwards |
| S10 Decide what may be issued | decision plus named reviewer recorded | the only place that answers "may we issue one number" |

The blocking level of a question states what an unanswered copy of it prevents:

* **hard** — the branch cannot be classified. The decision is `INSUFFICIENT_INFORMATION`.
* **amount** — the branch is known but no figure may be issued, because a slot it feeds is empty.
* **review** — an admissibility question that must reach a human. It never changes arithmetic silently.
* **not_blocking** — recorded for the file's own completeness.

The full form, one row per question with its admissible answers, the slots it binds,
the evidence it demands and the rung it belongs to
(`python claim.py questionnaire --format markdown`):

<!-- BEGIN GENERATED: questionnaire -->

| # | Ask | Admissible answers | Binds | Evidence | Blocking | Rung |
|---|---|---|---|---|---|---|
| Q-S0-01 | Which insurer issued the policy, and which product and policy version applies? | text | - | EVT_POLICY_COPY | hard | T0 |
| Q-S0-02 | On what date did the event occur? | date | PS_EVENT_DATE, PS_CLAIM_YEAR | EVT_CLAIM_FORM | hard | T0 |
| Q-S0-03 | On what date did the insured become aware of the loss? | date | PS_AWARENESS_DATE | EVT_CLAIM_FORM | hard | T0 |
| Q-S0-04 | When was the loss declared, and was it within five working days of awareness? | ONTIME, LATE, LATE_WITH_UNAVOIDABLE_CAUSE, UNKNOWN | PS_NOTICE_TIMELINESS, PS_NOTICE_TIMELINESS, PS_NOTICE_TIMELINESS | EVT_CLAIM_FORM, EVT_LATE_NOTICE_EXCUSE | review | T0 |
| Q-S0-07 | On what date was the loss declared to the insurer? | date | PS_DECLARATION_DATE | EVT_CLAIM_FORM | hard | T0 |
| Q-S0-05 | Who was driving, and in what capacity relative to the insured? | INSURED, EMPLOYEE, FAMILY, THIRD_PARTY, UNKNOWN_DRIVER, NOT_APPLICABLE_NO_DRIVER | - | - | hard | T0 |
| Q-S0-06 | Was the policy in force on the event date, with premium and instalments current? | IN_FORCE, LAPSED, INSTALMENT_OVERDUE, UNKNOWN | - | EVT_POLICY_COPY, EVT_PREMIUM_PROOF | hard | T0 |
| Q-S1-01 | What is the vehicle type and its declared use? | PASSENGER_CAR, VAN, TRUCK, BUS, MOTORCYCLE, AGRICULTURAL, SPECIALISED, UNKNOWN | - | EVT_PROPOSAL_FORM, EVT_OWNERSHIP_DOCS | hard | T0 |
| Q-S1-02 | Were the damaged accessories or fittings listed in the proposal and approved by the insurer? | LISTED, NOT_LISTED, PARTIALLY_LISTED, UNKNOWN | - | EVT_PROPOSAL_FORM | amount | T1 |
| Q-S1-03 | Was the loss inside the Islamic Republic of Iran, or covered by a special agreement? | INSIDE_IRAN, OUTSIDE_WITH_AGREEMENT, OUTSIDE_NO_AGREEMENT, UNKNOWN | - | - | hard | T0 |
| Q-S2-01 | Which insured peril caused the loss? | COLLISION, OVERTURN, FALL_OF_OBJECTS, OBJECTS_STRUCK_BY_VEHICLE, FIRE, LIGHTNING, EXPLOSION, THEFT, ATTEMPTED_THEFT_DAMAGE, DURING_RESCUE_OR_TRANSPORT, NATURAL_DISASTER, INDEPENDENT_GLASS_BREAKAGE, OTHER, UNKNOWN | PS_PERIL | EVT_ASSESSMENT_REPORT | hard | T0 |
| Q-S2-02 | Is the causal link between that peril and this specific damage established by a report, or only asserted? | ESTABLISHED, ASSERTED_ONLY, CONTRADICTED, UNKNOWN | PS_CAUSATION_ESTABLISHED | EVT_ASSESSMENT_REPORT, EVT_POLICE_CROQUIS | hard | T0 |
| Q-S2-03 | For damage from struck or falling objects, parts, or cargo: was the vehicle in motion? _(asked when: `{"answer_is": ["Q-S2-01", ["FALL_OF_OBJECTS", "OBJECTS_STRUCK_BY_VEHICLE", "OTHER"]]}`)_ | MOVING, PARKED, UNKNOWN | - | - | amount | T1 |
| Q-S2-04 | Was another party involved, and what is the fault position recorded by the authority? _(asked when: `{"not": {"answer_is": ["Q-S2-07", ["WHOLE_VEHICLE", "PARTIAL_PARTS_THEFT", "PARTS_STOLEN_AFTER_ACCIDENT"]]}}`)_ | INSURED_AT_FAULT, THIRD_PARTY_AT_FAULT, SHARED, NO_OTHER_PARTY, UNDETERMINED | - | EVT_POLICE_CROQUIS | amount | T1 |
| Q-S2-05 | Did the glass break on its own, or together with other damage from the same event? _(asked when: `{"any": [{"answer_is": ["Q-S2-01", "INDEPENDENT_GLASS_BREAKAGE"]}, {"slot_present": "PS_PART_CATEGORY", "category": "GLASS"}]}`)_ | ALONE, WITH_OTHER_DAMAGE, UNKNOWN | PS_GLASS_CAUSE_PRECEDENCE, PS_GLASS_CAUSE_PRECEDENCE | EVT_PHOTOS, EVT_ASSESSMENT_REPORT | hard | T1 |
| Q-S2-06 | For fire, lightning or explosion: is there an authority report establishing the cause? _(asked when: `{"answer_is": ["Q-S2-01", ["FIRE", "LIGHTNING", "EXPLOSION"]]}`)_ | REPORT_WITH_CAUSE, REPORT_NO_CAUSE, NO_REPORT, NOT_APPLICABLE | - | EVT_FIRE_CAUSE_REPORT | amount | T1 |
| Q-S2-07 | Which theft situation applies? _(asked when: `{"answer_is": ["Q-S2-01", ["THEFT", "ATTEMPTED_THEFT_DAMAGE"]]}`)_ | WHOLE_VEHICLE, ATTEMPTED_VEHICLE_THEFT_DAMAGE, PARTIAL_PARTS_THEFT, PARTS_STOLEN_AFTER_ACCIDENT, NOT_A_THEFT | PS_THEFT_TYPE | EVT_POLICE_STATION_REPORT, EVT_NON_DISCOVERY_ENQUIRY | hard | T1 |
| Q-S2-08 | What elapsed whole-day count is recorded for the missing vehicle? _(asked when: `{"answer_is": ["Q-S2-07", "WHOLE_VEHICLE"]}`)_ | integer | PS_DAYS_MISSING | EVT_NON_DISCOVERY_ENQUIRY | hard | T2 |
| Q-S2-10 | Which sourced event starts the sixty-day whole-vehicle theft clock? _(asked when: `{"answer_is": ["Q-S2-07", "WHOLE_VEHICLE"]}`)_ | THEFT_OCCURRENCE, AWARENESS, DECLARATION | PS_THEFT_CLOCK_START_EVENT | EVT_NON_DISCOVERY_ENQUIRY | hard | T2 |
| Q-S2-11 | What is the sourced start date for that selected theft-clock event? _(asked when: `{"answer_is": ["Q-S2-07", "WHOLE_VEHICLE"]}`)_ | date | PS_THEFT_CLOCK_START_DATE | EVT_NON_DISCOVERY_ENQUIRY | hard | T2 |
| Q-S2-12 | Through which sourced as-of date has the vehicle remained undiscovered? _(asked when: `{"answer_is": ["Q-S2-07", "WHOLE_VEHICLE"]}`)_ | date | PS_THEFT_CLOCK_AS_OF_DATE | EVT_NON_DISCOVERY_ENQUIRY | hard | T2 |
| Q-S2-13 | Which calendar do the theft-clock dates use? _(asked when: `{"answer_is": ["Q-S2-07", "WHOLE_VEHICLE"]}`)_ | SHAMSI, GREGORIAN | PS_THEFT_CLOCK_CALENDAR | EVT_NON_DISCOVERY_ENQUIRY | hard | T2 |
| Q-S2-14 | Which document and locator authorize this theft-clock anchor and its dates? _(asked when: `{"answer_is": ["Q-S2-07", "WHOLE_VEHICLE"]}`)_ | text | PS_THEFT_CLOCK_SOURCE | EVT_NON_DISCOVERY_ENQUIRY | hard | T2 |
| Q-S2-09 | Is the reported damage consistent with the stated event, or is there a discrepancy? | CONSISTENT, DISCREPANCY_PRE_EXISTING, DISCREPANCY_UNEXPLAINED, NOT_REVIEWED | - | EVT_PHOTOS, EVT_ASSESSMENT_REPORT | review | T1 |
| Q-S3-01 | What was the licence position of the driver at the time of the event? | VALID_AND_APPROPRIATE, EXPIRED, VOID_OR_SUSPENDED, WRONG_CLASS, UNLICENSED, NOT_DRIVING, UNKNOWN | PS_LICENSE_STATE | EVT_LICENCE | hard | T0 |
| Q-S3-02 | Is there a competent-authority finding that alcohol or drugs were used, with a causal link to the loss? | CONFIRMED_AND_CAUSAL, CONFIRMED_NOT_CAUSAL, SUSPECTED_NO_REPORT, NO, UNKNOWN | PS_INTOXICATION_CAUSAL | EVT_JUDICIAL_FINDING | hard | T0 |
| Q-S3-03 | Any sign of intentional damage by the insured, a beneficiary or the driver, or of loss while fleeing the authorities? | NO, YES_INTENTIONAL, YES_FLIGHT, UNKNOWN | - | EVT_JUDICIAL_FINDING | hard | T0 |
| Q-S3-04 | Do any of the remaining non-compensable conditions apply? | NONE, WAR_OR_NUCLEAR, UNAUTHORIZED_TOWING, OVERLOAD, INHERENT_ELECTRICAL, UNKNOWN | - | EVT_ASSESSMENT_REPORT | hard | T1 |
| Q-S3-05 | Which endorsements does this policy actually carry? | NONE, HELD, UNKNOWN | PS_ENDORSEMENTS | EVT_POLICY_COPY, EVT_ENDORSEMENT_WORDING | amount | T1 |
| Q-S3-06 | Was the vehicle moved or repaired before the insurer's consent or inspection? | NO, DONE_WITH_CONSENT, DONE_WITHOUT_CONSENT, POLICE_ORDERED_MOVE, UNKNOWN | - | EVT_REPAIR_CONSENT, EVT_PHOTOS | review | T1 |
| Q-S3-07 | Did the risk or the use of the vehicle intensify without notifying the insurer? | NO, YES, UNKNOWN | PS_RISK_INTENSIFICATION | EVT_RISK_INTENSIFICATION_RECORD | hard | T2 |
| Q-S3-08 | Was the vehicle sold or transferred after an accident that had not been declared? | NO, YES, UNKNOWN | - | EVT_OWNERSHIP_DOCS | hard | T1 |
| Q-S4-01 | Is the assessment itemised by component, or only an aggregate repair figure? _(asked when: `{"not": {"slot_present": "PS_DAYS_MISSING"}}`)_ | ITEMISED, AGGREGATE_ONLY, UNKNOWN | PS_GROSS_DAMAGE, PS_REPAIR_TOTAL | EVT_ASSESSMENT_REPORT, EVT_REPAIR_INVOICE | hard | T0 |
| Q-S4-02 | What is the fair repair labour, separated from parts? _(asked when: `{"not": {"slot_present": "PS_DAYS_MISSING"}}`)_ | money | PS_LABOR | EVT_ASSESSMENT_REPORT, EVT_REPAIR_INVOICE | amount | T1 |
| Q-S4-03 | For each component: is it replaced or repaired only, and which category is it? _(asked when: `{"not": {"slot_present": "PS_DAYS_MISSING"}}`)_ | GLASS, LAMP_GLASS, BATTERY, TIRE, OTHER_REPLACEMENT_PART, REPAIR_ONLY | PS_PART_CATEGORY | EVT_ASSESSMENT_REPORT | amount | T1 |
| Q-S4-04 | For each battery or tyre: what is its new price on the day of the event? _(asked when: `{"answer_is": ["Q-S4-03", ["BATTERY", "TIRE"]]}`)_ | money | PS_PART_NEW_PRICE | EVT_ASSESSMENT_REPORT, EVT_MARKET_VALUE_EVIDENCE | amount | T1 |
| Q-S4-05 | Did the assessor state depreciation as a figure, or should it be computed from the production year? _(asked when: `{"answer_is": ["Q-S4-03", ["OTHER_REPLACEMENT_PART", "BATTERY", "TIRE"]]}`)_ | ASSESSED_FIGURE, COMPUTE_FROM_YEAR, NOT_STATED | PS_ASSESSED_DEPRECIATION | EVT_ASSESSMENT_REPORT | amount | T1 |
| Q-S4-06 | Has the registration been transferred to the insurer, and when? _(asked when: `{"any": [{"answer_is": ["Q-S2-07", "WHOLE_VEHICLE"]}, {"slot_present": "PS_SALVAGE_DISPOSITION", "value": "INSURER_TAKES_TITLE"}]}`)_ | TRANSFERRED, NOT_TRANSFERRED, IN_PROGRESS, NOT_APPLICABLE | PS_TITLE_TRANSFERRED, PS_TITLE_TRANSFERRED | EVT_TITLE_TRANSFER_PROOF | amount | T2 |
| Q-S4-07 | What rescue, mitigation or transport cost was actually incurred, and with invoices? _(asked when: `{"not": {"slot_present": "PS_DAYS_MISSING"}}`)_ | money | PS_RESCUE_ACTUAL | EVT_ASSESSMENT_REPORT | amount | T1 |
| Q-S4-08 | What is the probable salvage value, and does the insured accept it? _(asked when: `{"branch_is": ["TOTAL_LOSS"]}`)_ | money | PS_SALVAGE_VALUE | EVT_SALVAGE_VALUATION | amount | T2 |
| Q-S4-09 | Who keeps the wreck? _(asked when: `{"branch_is": ["TOTAL_LOSS"]}`)_ | NOT_APPLICABLE, INSURED_RETAINS, INSURER_TAKES_TITLE, UNRESOLVED | PS_SALVAGE_DISPOSITION | EVT_SALVAGE_VALUATION | amount | T2 |
| Q-S4-10 | Is the vehicle repairable at all, or is repair technically impossible? _(asked when: `{"not": {"slot_present": "PS_DAYS_MISSING"}}`)_ | REPAIRABLE, TECHNICALLY_IRREPAIRABLE, ECONOMICALLY_TOTAL, UNKNOWN | - | EVT_ASSESSMENT_REPORT | hard | T2 |
| Q-S4-11 | Where the assessment cannot be itemised, what is the aggregate repair-and-replacement figure excluding rescue and transport? _(asked when: `{"answer_is": ["Q-S4-01", "AGGREGATE_ONLY"]}`)_ | money | PS_GROSS_DAMAGE, PS_REPAIR_TOTAL | EVT_ASSESSMENT_REPORT | hard | T0 |
| Q-S5-01 | What was the transactional value of the vehicle on the day of the event, and on what evidence? | money | PS_MARKET_VALUE | EVT_MARKET_VALUE_EVIDENCE, EVT_ASSESSMENT_REPORT | hard | T0 |
| Q-S5-02 | What insured sum does the policy state for the year of the event? | money | PS_INSURED_SUM | EVT_POLICY_COPY | hard | T0 |
| Q-S5-03 | What is the production (model) year, taken from the registration or the policy schedule? | integer | PS_PRODUCTION_YEAR | EVT_OWNERSHIP_DOCS, EVT_POLICY_COPY | amount | T1 |
| Q-S5-04 | Does the difference between market value and insured sum look like under-insurance, or like a value dispute? _(asked when: `{"all": [{"slot_present": "PS_MARKET_VALUE"}, {"slot_present": "PS_INSURED_SUM"}]}`)_ | UNDERINSURANCE_CLEAR, VALUE_DISPUTED, NO_MATERIAL_DIFFERENCE, UNKNOWN | - | EVT_MARKET_VALUE_EVIDENCE | amount | T3 |
| Q-S6-01 | How is the franchise expressed in this policy: a percentage, a fixed amount, or a percentage with a minimum? | PERCENT, ABSOLUTE, PERCENT_WITH_MINIMUM, NOT_STATED | PS_FRANCHISE | EVT_POLICY_COPY | amount | T0 |
| Q-S6-02 | What rate or amount, and for which coverage line (base damage, theft, partial theft, glass, natural disaster)? _(asked when: `{"not": {"answer_is": ["Q-S6-01", "NOT_STATED"]}}`)_ | text | PS_FRANCHISE | EVT_POLICY_COPY, EVT_ENDORSEMENT_WORDING | amount | T0 |
| Q-S6-03 | What is the calculation base the rate applies to, and is there a minimum? _(asked when: `{"answer_is": ["Q-S6-01", ["PERCENT", "PERCENT_WITH_MINIMUM"]]}`)_ | text | PS_FRANCHISE | EVT_POLICY_COPY | amount | T1 |
| Q-S6-04 | What is the claim-sequence rule and which dated document is its source? | text | PS_FRANCHISE | EVT_POLICY_COPY, EVT_PRIOR_CLAIM_HISTORY | amount | T1 |
| Q-S6-05 | Is the same vehicle insured against the same risk under any other policy? | NO, YES_OTHER_POLICIES, YES_SAME_INSURER, UNKNOWN | PS_MULTIPLE_POLICIES | EVT_OTHER_POLICIES | amount | T3 |
| Q-S6-06 | Does the glass endorsement print a valuation condition or a ceiling on the glass it will pay for? _(asked when: `{"all": [{"answer_is": ["Q-S2-05", "ALONE"]}, {"answer_is": ["Q-S3-05", "HELD"]}]}`)_ | CONDITION_ABSENT, REQUIRES_INSURED_AT_MARKET_VALUE, HAS_VALUATION_CEILING, WORDING_NOT_OBTAINED | PS_GLASS_VALUATION_CONDITION | EVT_ENDORSEMENT_WORDING | amount | T3 |
| Q-S7-01 | Is any part of this loss also a third-party or legal-recovery claim that must be split into its own file? | NO_BODY_ONLY, PART_OF_IT_ALSO_THIRD_PARTY, PART_OF_IT_ALSO_LEGAL_RECOVERY, UNKNOWN | - | - | hard | T2 |
| Q-S8-01 | Where does the underinsurance ratio run relative to the franchise, and on whose authority? _(asked when: `{"answer_is": ["Q-S5-04", ["UNDERINSURANCE_CLEAR", "UNKNOWN"]]}`)_ | UNRESOLVED, AFTER_DEPRECIATION_BEFORE_FRANCHISE, AFTER_DEPRECIATION_AND_FRANCHISE, INSURER_SPECIFIC | PS_ARTICLE10_PARTIAL_ORDER | EVT_POLICY_COPY | amount | T3 |
| Q-S8-02 | For an old vehicle with a damaged battery or tyre: cap then depreciate, depreciate then cap, or cap only? _(asked when: `{"slot_present": "PS_PART_NEW_PRICE"}`)_ | UNRESOLVED, CAP_THEN_DEPRECIATE, DEPRECIATE_THEN_CAP, CAP_ONLY, NOT_APPLICABLE | PS_BATTERY_TIRE_INTERACTION | EVT_POLICY_COPY | amount | T3 |
| Q-S8-03 | Which figure is the denominator of the 20% rescue ceiling for this claim? _(asked when: `{"slot_present": "PS_RESCUE_ACTUAL"}`)_ | ASSESSED_GROSS, ELIGIBLE_GROSS, SETTLEMENT_BASE | PS_RESCUE_CAP_BASE | EVT_POLICY_COPY | amount | T2 |
| Q-S8-04 | Will this settle as cash, repair in kind, or a replacement vehicle? | CASH, REPAIR_IN_KIND, REPLACEMENT_VEHICLE, NOT_DECIDED | PS_SETTLEMENT_MODE | - | not_blocking | T1 |
| Q-S8-05 | Which annual parameter set applies to the event year, and has it been revalidated against the primary announcement? _(asked when: `{"any": [{"branch_is": ["THIRD_PARTY_FINANCIAL", "ARTICLE_8_NON_CONVENTIONAL"]}, {"answer_is": ["Q-S7-01", ["PART_OF_IT_ALSO_THIRD_PARTY", "UNKNOWN"]]}]}`)_ | PRIMARY_VERIFIED, SECONDARY_ONLY, MISSING_YEAR, NOT_APPLICABLE_TO_BODY | - | EVT_POLICY_COPY | amount | T4 |
| Q-S9-01 | Has the insured released, settled with, or obstructed recovery against the responsible party? | NO, RELEASED_PARTY, SETTLED_DIRECTLY, DESTROYED_EVIDENCE, UNKNOWN | PS_SUBROGATION_IMPAIRED | EVT_JUDICIAL_FINDING, EVT_ARBITRATION_OR_COURT_AWARD | review | T5 |
| Q-S9-02 | Is a responsible party identified and solvent enough to be pursued? | IDENTIFIED_INSURED, IDENTIFIED_UNINSURED, UNKNOWN_DRIVER, NO_THIRD_PARTY | - | EVT_POLICE_CROQUIS, EVT_ARBITRATION_OR_COURT_AWARD | review | T5 |
| Q-S9-03 | Has any compensation already been received for this same damage, from any source? | money | PS_MULTIPLE_POLICIES | EVT_OTHER_POLICIES, EVT_ARBITRATION_OR_COURT_AWARD | amount | T5 |
| Q-S10-01 | Who reviewed the file, and does the issued decision match the computed outcome? | text | - | - | review | T0 |

<!-- END GENERATED: questionnaire -->

Per-question detail, including the conditional `when` each question is gated by and
the reason it is asked at all, is printed stage by stage with
`python claim.py questionnaire --stage S4_DAMAGE_SCOPE`.

## 4. Selecting the parameters

A parameter is *correct* only if three things are true at once: the value came from a
channel entitled to supply it, it is the value for this branch and this policy
version, and any ambiguity in how it is applied is surfaced instead of resolved by
habit. The matrix below is the whole contract
(`python claim.py parameters --format markdown`); the prose after it covers the cases
where people most often get it wrong.

<!-- BEGIN GENERATED: parameters -->

| Slot | Unit | Authority | Supplied by | Absent means | Uncertainty | Guardrail | Branches |
|---|---|---|---|---|---|---|---|
| PS_ARTICLE10_PARTIAL_ORDER | enum | ADJUSTER_CONFIG | Q-S8-01 | SCENARIO_SET | U01_ARTICLE10_PARTIAL_ORDER | - | PARTIAL_DAMAGE, GLASS_ONLY |
| PS_ASSESSED_DEPRECIATION | money | ASSESSOR | Q-S4-05 | NOT_APPLICABLE | - | - | PARTIAL_DAMAGE |
| PS_AWARENESS_DATE | date | REGULATION | Q-S0-03 | REVIEW_GATE | - | - | PARTIAL_DAMAGE, TOTAL_LOSS, GLASS_ONLY, THEFT |
| PS_BATTERY_TIRE_INTERACTION | enum | ADJUSTER_CONFIG | Q-S8-02 | SCENARIO_SET | U04_BATTERY_TIRE_CAP_VS_DEPRECIATION | - | PARTIAL_DAMAGE |
| PS_CAUSATION_ESTABLISHED | boolean | REGULATION | Q-S2-02 | REFUSE | - | G_COVERED_PERIL_CAUSATION_ESTABLISHED | PARTIAL_DAMAGE, TOTAL_LOSS, GLASS_ONLY, THEFT |
| PS_CLAIM_YEAR | integer | DERIVED | Q-S0-02 | REFUSE | - | - | PARTIAL_DAMAGE, TOTAL_LOSS, GLASS_ONLY, THEFT |
| PS_DAYS_MISSING | integer | REGULATION | Q-S2-08 | REFUSE | U13_THEFT_CLOCK_ANCHOR | - | THEFT |
| PS_DECLARATION_DATE | date | REGULATION | Q-S0-07 | REVIEW_GATE | - | - | PARTIAL_DAMAGE, TOTAL_LOSS, GLASS_ONLY, THEFT |
| PS_ENDORSEMENTS | list | POLICY | Q-S3-05 | REFUSE | U03_GLASS_ONLY_ENDORSEMENT_WORDING | G_NO_GUESSED_ENDORSEMENT_TERMS | GLASS_ONLY, THEFT, PARTIAL_DAMAGE |
| PS_EVENT_DATE | date | EVENT_FACT | Q-S0-02 | REFUSE | - | - | PARTIAL_DAMAGE, TOTAL_LOSS, GLASS_ONLY, THEFT |
| PS_FRANCHISE | object | POLICY | Q-S6-01, Q-S6-02, Q-S6-03, Q-S6-04 | REFUSE | U02_FRANCHISE_BASE_SCHEDULES | G_NO_HARDCODED_FRANCHISE_RATE | PARTIAL_DAMAGE, TOTAL_LOSS, GLASS_ONLY, THEFT |
| PS_GLASS_CAUSE_PRECEDENCE | boolean | POLICY | Q-S2-05 | REFUSE | - | - | GLASS_ONLY, PARTIAL_DAMAGE |
| PS_GLASS_VALUATION_CONDITION | enum | POLICY | Q-S6-06 | ESCALATE_INSURER | U14_GLASS_INSURED_AT_VALUE_CONDITION | G_NO_UNIVERSAL_GLASS_FRANCHISE | GLASS_ONLY |
| PS_GROSS_DAMAGE | money | ASSESSOR | Q-S4-01, Q-S4-11 | REFUSE | - | - | PARTIAL_DAMAGE |
| PS_INSURED_SUM | money | POLICY | Q-S5-02 | REFUSE | - | - | PARTIAL_DAMAGE, TOTAL_LOSS, GLASS_ONLY, THEFT |
| PS_INTOXICATION_CAUSAL | boolean | REGULATION | Q-S3-02 | REVIEW_GATE | - | - | PARTIAL_DAMAGE, TOTAL_LOSS, GLASS_ONLY, THEFT |
| PS_LABOR | money | ASSESSOR | Q-S4-02 | TREAT_AS_ZERO | - | - | PARTIAL_DAMAGE |
| PS_LICENSE_STATE | enum | REGULATION | Q-S3-01 | REVIEW_GATE | - | - | PARTIAL_DAMAGE, TOTAL_LOSS, GLASS_ONLY, THEFT |
| PS_MARKET_VALUE | money | REGULATION | Q-S5-01 | ASSESSOR_REQUIRED | - | - | PARTIAL_DAMAGE, TOTAL_LOSS, GLASS_ONLY, THEFT |
| PS_MULTIPLE_POLICIES | object | REGULATION | Q-S6-05, Q-S9-03 | REVIEW_GATE | - | G_RECOVERY_ALLOCATION_CONTAINED | PARTIAL_DAMAGE, TOTAL_LOSS, GLASS_ONLY, THEFT |
| PS_NOTICE_TIMELINESS | enum | REGULATION | Q-S0-04 | REVIEW_GATE | - | - | PARTIAL_DAMAGE, TOTAL_LOSS, GLASS_ONLY, THEFT |
| PS_PART_CATEGORY | enum | REGULATION | Q-S4-03 | REFUSE | - | - | PARTIAL_DAMAGE, GLASS_ONLY |
| PS_PART_NEW_PRICE | money | REGULATION | Q-S4-04 | REFUSE | U04_BATTERY_TIRE_CAP_VS_DEPRECIATION | - | PARTIAL_DAMAGE |
| PS_PERIL | enum | REGULATION | Q-S2-01 | REFUSE | - | G_NO_ASSUMED_CAUSATION | PARTIAL_DAMAGE, TOTAL_LOSS, GLASS_ONLY, THEFT |
| PS_PRODUCTION_YEAR | integer | REGULATION | Q-S5-03 | ASSESSOR_REQUIRED | - | - | PARTIAL_DAMAGE, GLASS_ONLY |
| PS_REPAIR_TOTAL | money | ASSESSOR | Q-S4-01, Q-S4-11 | ASSESSOR_REQUIRED | - | - | TOTAL_LOSS, PARTIAL_DAMAGE |
| PS_RESCUE_ACTUAL | money | REGULATION | Q-S4-07 | BLOCK_IF_MATERIAL | - | - | PARTIAL_DAMAGE, TOTAL_LOSS |
| PS_RESCUE_CAP_BASE | enum | ADJUSTER_CONFIG | Q-S8-03 | BLOCK_IF_MATERIAL | U05_RESCUE_DENOMINATOR | - | PARTIAL_DAMAGE, TOTAL_LOSS |
| PS_RISK_INTENSIFICATION | boolean | REGULATION | Q-S3-07 | REVIEW_GATE | - | G_NO_ASSUMED_CAUSATION | PARTIAL_DAMAGE, TOTAL_LOSS, GLASS_ONLY, THEFT |
| PS_SALVAGE_DISPOSITION | enum | REGULATION | Q-S4-09 | SCENARIO_SET | U12_SALVAGE_DISPOSITION | - | TOTAL_LOSS |
| PS_SALVAGE_VALUE | money | ASSESSOR | Q-S4-08 | REFUSE | - | G_SALVAGE_XOR_TITLE_TRANSFER | TOTAL_LOSS |
| PS_SETTLEMENT_MODE | enum | REGULATION | Q-S8-04 | NOT_APPLICABLE | - | - | PARTIAL_DAMAGE, TOTAL_LOSS |
| PS_SUBROGATION_IMPAIRED | boolean | REGULATION | Q-S9-01 | REVIEW_GATE | - | - | PARTIAL_DAMAGE, TOTAL_LOSS, THEFT, LEGAL_RECOVERY |
| PS_THEFT_CLOCK_AS_OF_DATE | date | EVENT_FACT | Q-S2-12 | REFUSE | U13_THEFT_CLOCK_ANCHOR | - | THEFT |
| PS_THEFT_CLOCK_CALENDAR | enum | EVENT_FACT | Q-S2-13 | REFUSE | U13_THEFT_CLOCK_ANCHOR | - | THEFT |
| PS_THEFT_CLOCK_SOURCE | text | INSURER_PROCEDURE | Q-S2-14 | REFUSE | U13_THEFT_CLOCK_ANCHOR | - | THEFT |
| PS_THEFT_CLOCK_START_DATE | date | EVENT_FACT | Q-S2-11 | REFUSE | U13_THEFT_CLOCK_ANCHOR | - | THEFT |
| PS_THEFT_CLOCK_START_EVENT | enum | INSURER_PROCEDURE | Q-S2-10 | REFUSE | U13_THEFT_CLOCK_ANCHOR | - | THEFT |
| PS_THEFT_TYPE | enum | REGULATION | Q-S2-07 | REFUSE | - | - | THEFT |
| PS_TITLE_TRANSFERRED | boolean | REGULATION | Q-S4-06 | REFUSE | - | G_SALVAGE_XOR_TITLE_TRANSFER | THEFT, TOTAL_LOSS |
| PS_UNDERINSURANCE_RATIO | ratio | DERIVED | - | SCENARIO_SET | U01_ARTICLE10_PARTIAL_ORDER | - | PARTIAL_DAMAGE, TOTAL_LOSS, GLASS_ONLY |

<!-- END GENERATED: parameters -->

### Who may supply what

| Authority on the slot | Only acceptable source | If it is missing |
|---|---|---|
| `REGULATION` / `CIRCULAR` | the instrument itself, at the effective date of the event | the case is refused or escalated; never approximated |
| `POLICY` | the declarations page, private conditions or endorsement schedule for *this* version | blocks on the named uncertainty (usually `U02`) |
| `INSURER_PROCEDURE` | a dated claims manual or worksheet | the adapter is empty by design; escalate |
| `ASSESSOR` | the assessment report, with its evidence | `ASSESSOR_REQUIRED` |
| `ADJUSTER_CONFIG` | a recorded decision with a source | stays `UNRESOLVED`, which produces scenarios |
| `DERIVED` | arithmetic on other evidenced slots | never hand-entered |

### The seven selection decisions that change the answer

1. **The year index, not the age.** Depreciation is driven by
   `claim_year − production_year + 1`: nothing before the fifth production year,
   5% a year after that, capped at 25%. The fifth year already attracts 5%, so an
   off-by-one is a real amount error. Take the production year from the registration
   or the policy schedule (`Q-S5-03`), and use the **event** year, not the settlement
   year, for `PS_CLAIM_YEAR`.
2. **One market value, three jobs.** The transactional value on the accident date is
   the 75% denominator, the ratio denominator and the total-loss settlement base. The
   insured sum may not substitute for it in any of the three (`Q-S5-01`).
3. **The ratio is derived, capped at one, and is not a subtraction.**
   `min(1, insured/market)`, computed here from the two evidenced figures rather than
   asked (`PS_UNDERINSURANCE_RATIO`). Over-insurance cannot increase a payment. Where
   it is below one in a partial loss, its position relative to the franchise is
   unstated in the regulation, so the honest output is a scenario set.
4. **Franchise needs a base and a version, not just a rate.** A percentage without a
   named calculation base is not a parameter the engine will accept, and an unsourced
   percentage is refused by `G_NO_HARDCODED_FRANCHISE_RATE`. First-claim and
   subsequent-claim rates, and whether a multi-year contract counts claims per policy
   year, are insurer terms and must carry a dated source (`Q-S6-01`…`Q-S6-04`).
5. **Salvage and title are alternatives.** If the insured keeps the wreck, subtract
   the probable salvage and *then* apply the total-loss franchise. If the insurer
   takes title, transfer the vehicle and do not also deduct its value.
   `UNRESOLVED` blocks (`G_SALVAGE_XOR_TITLE_TRANSFER`, `U12`).
6. **Settlement mode does not touch the arithmetic.** Cash, repair in kind or a
   replacement vehicle: franchise and depreciation remain the insured's responsibility
   either way, so a repair-in-kind settlement must not drop either operator
   (`Q-S8-04`).
7. **Category decides which operators apply at all.** Glass and lamp glass are exempt
   from depreciation — the one universally established calculation fact in this
   domain — battery and tyre take the 50%-of-new cap, other replaced parts take the age
   schedule, and repair-only items take neither. Whether the cap and the schedule stack
   is unresolved (`U04`), so an old vehicle with a damaged battery stops rather than
   stacking.

## 5. The iterative completion ladder

The ladder is the delivery model: one rung adds exactly one source of complexity, so a
failure always points at one operator, one configuration value, or one missing
document. Rung assignment is not a label — a rung certifies only the outcome class it
names, and passing it says nothing about the next one.

<!-- BEGIN GENERATED: ladder -->

| Rung | Adds | Permitted outcomes | Corpus | Calibration still needed |
|---|---|---|---|---|
| T0 One number, nothing assumed | Prove the pipeline can pay a fully specified claim without inventing a single input. | SINGLE_PAYABLE, ZERO_WITH_REASON | P01, P07, G24, G26, TP34, TP38, TP39 | nothing - complete as certified |
| T1 Computed deductions | Add the operators that compute rather than copy: the depreciation year index, the component categories, the special-part cap and the rescue ceiling. | SINGLE_PAYABLE | P02, P03, P04, P05, P06, P08, P09, P12, G28 | nothing - complete as certified |
| T2 Branch boundaries | Decide which engine the case belongs to, and prove the boundary is strict rather than rounded. | SINGLE_PAYABLE, PENDING, ZERO_WITH_REASON, REFUSE | T16, T17, T18, T20, T22, T23, G25, G26, P13, P15, TH29, TH30, TH31, TH32 | U12_SALVAGE_DISPOSITION, U13_THEFT_CLOCK_ANCHOR |
| T3 The ratio is live | Introduce under-insurance, where the correct answer is a set of sourced scenarios rather than one number. | SCENARIO_SET, SINGLE_PAYABLE | P10, P11, T19, G27 | U01_ARTICLE10_PARTIAL_ORDER, U04_BATTERY_TIRE_CAP_VS_DEPRECIATION, U05_RESCUE_DENOMINATOR |
| T4 The contract has not been read yet | Handle claims where the law is settled and the policy wording is missing - the engine must name the artefact it needs. | REFUSE, SCENARIO_SET, ESCALATE_REVIEW | P14, TH33, G27, T21 | U02_FRANCHISE_BASE_SCHEDULES, U03_GLASS_ONLY_ENDORSEMENT_WORDING, U11_GLASS_ARTICLE10_EXEMPTION, U14_GLASS_INSURED_AT_VALUE_CONDITION |
| T5 Two policies, one loss | Add allocation: contribution between insurers, prior indemnity, recourse, and the split between an ordinary and a non-conventional vehicle. | SINGLE_PAYABLE, ESCALATE_REVIEW, REFUSE | A40, A41, A42, A46, A47, A48, L49, L50 | U06_ARTICLE8_COMPONENT_CATALOGUE, U07_ANNUAL_CONVENTIONAL_REFERENCE_SET, U09_DIMINUTION_OF_VALUE_TP, U15_RISK_INTENSIFICATION_PREMIUM_RATIO |
| T6 Anything not yet certified | The default state for any case outside T0-T5: new peril, new product, new insurer, missing annual parameters, or a rule the graph does not carry. | NOT_CERTIFIED, ESCALATE_REVIEW | - | U08_DIYAH_1405_PRIMARY, U10_IMMEDIATE_CAUSE_TERMINOLOGY |

<!-- END GENERATED: ladder -->

Promotion rules, as declared in the data:

<!-- BEGIN GENERATED: promotion-rules -->

* A tier passes only on its own gate: every example case reaches its expected terminal state.
* A tier may not be promoted over a case whose outcome was produced by a parameter nobody supplied.
* Passing a tier certifies only the outcome class it names; it certifies nothing about the next tier.
* A tier that can produce a single payable must also produce it with a computed confidence and a rule trace.

<!-- END GENERATED: promotion-rules -->

Where the implementation actually stands against that ladder, measured by
`python claim.py fixtures` (the 50-case corpus) and the five worked review files in
`cases/`:

| Rung | Today | Evidence |
|---|---|---|
| T0 | certified | single payable, every deduction traceable, no defaulted input |
| T1 | certified | `cases/review_t1_fullcover_partial.json` → 165.70 m-toman, confidence 0.95 |
| T2 | tested boundary behavior; review theft handoff remains blocked | legacy engine fixtures exercise 59/60/61 days, but review requires a sourced clock anchor; equality at 75% stays partial |
| T3 | returns scenarios, does not certify one number | `cases/review_t3_underinsured_partial.json` → two outcomes, confidence 0.55 |
| T4 | refuses with the artefact named | `cases/review_t4_glass_terms_missing.json` |
| T5 | refuses where correspondence is absent | `TP37`, `U06`/`U07` remain open |
| T6 | the default for anything else | `claim.py ladder` prints why a file fell off |

The practical consequence: **this system may issue one number only for T0–T2 claims on
a fully specified policy**, and must not be represented as an unattended payment
authority for anything above that. That matches the release posture in
[docs/ROADMAP.md](ROADMAP.md).

## 6. Worked traces

| File | Rung | Decision | Outcome |
|---|---|---|---|
| `review_t0_intake_partial.json` | T4 | `INSUFFICIENT_INFORMATION` | 27 questions still open, earliest is in S1/S2; the ladder already sees that nobody has read the franchise schedule |
| `review_t1_fullcover_partial.json` | T1 | `COMPUTE` | 165.70 m-toman single payable, trace of five rules, confidence 0.95 |
| `review_t2_theft_pending.json` | T2 | `INSUFFICIENT_INFORMATION` | U13 blocks this unanchored whole-vehicle theft; a complete five-field clock now has a tested review-to-engine path |
| `review_t3_underinsured_partial.json` | T3 | `SCENARIO_SET` | 139.625 / 144.6875 m-toman, `U01` live, confidence capped at 0.55 |
| `review_t4_glass_terms_missing.json` | T4 | `INSUFFICIENT_INFORMATION` | coverage exists through the endorsement, its schedule does not; `U02`/`U03`/`U11` live |
| `review_refuse_wrong_licence.json` | T0 | `REFUSE` | licence class wrong: no depreciation, franchise or ratio is ever computed |

Run one end to end:

```bash
python claim.py review cases/review_t3_underinsured_partial.json --calc
python claim.py review cases/review_t1_fullcover_partial.json --emit-case /tmp/t1.json
python claim.py calc /tmp/t1.json          # the emitted case is a normal engine input
```

## 7. What the September 2026 source pass changed

A targeted re-read of the general conditions and of two insurers' published wording
(retrieved 2026-09-25, registered in `knowledge/sources.json`) sharpened the procedure
without altering a single formula. The distinction matters: this layer may add
*questions and evidence requirements* freely, but an amount-affecting rule enters only
through `claim.py ingest`, with contradiction checking and a human authorisation.

**Adopted into the procedure (no arithmetic changed):**

* Notice runs **five working days from awareness**, per the duties article — the model
  already encoded that, and the article number is now corroborated by three copies
  rather than one mirror. The excuse in the text is *unavoidable causes*, not
  عذر موجه, and the file must not soften it.
* **Three separate dates** are now mandatory (S0): occurrence, awareness, declaration.
  Insurer checklists anchor the sixty-day theft clock on the declaration while the
  regulation words it from the theft, and the payment provision carries its own clock.
  Recorded as `U13_THEFT_CLOCK_ANCHOR` rather than guessed.
* The regulation names **no expert or appraisal board**; the contractual dispute
  instrument is the arbitration/court article. So `EVT_ARBITRATION_OR_COURT_AWARD` is
  cited to that article, and any "official expert panel" must be sourced to insurer
  procedure or to the Central Insurance complaint machinery — not to the regulation.
* Per-peril document lists (croquis, fire cause report, police station and criminal
  investigation files, non-discovery enquiry, technical inspection, tax and municipality
  clearances, keys) exist only in **insurer procedure**. Every such evidence item now
  carries `source_class: INSURER_PROCEDURE` where that is true, so a company checklist
  can never masquerade as law.
* **Licence state is a three-way fact**, not a boolean: void, wrong class or absent
  defeats cover, while an expired licence expressly does not. Modelled as `Q-S3-01`
  with a seven-token vocabulary and the mapping stated in code.
* **Standalone glass has a cause-precedence condition** (causes outside the insurer's
  basic perils) *and*, in at least one insurer's printed wording, a condition that the
  vehicle be insured at market value — which would remove the glass route for an
  under-insured vehicle. That is a policy term observed in one company's wording, so it
  became `Q-S6-06` + `U14_GLASS_INSURED_AT_VALUE_CONDITION`, not a branch rule.

**Proposed but deliberately not imported (needs ingest review, because it is
amount-affecting):**

* **Intensification of risk**: the conditions provide a reduction in the ratio of the
  premium charged to the premium appropriate to the intensified risk. That is a
  *premium*-ratio mechanism, distinct from underinsurance, and no such operator exists
  in this engine. It is recorded as `U15_RISK_INTENSIFICATION_PREMIUM_RATIO` with
  `engine_status: NOT_IMPLEMENTED_DO_NOT_SUBSTITUTE`, and `Q-S3-07` escalates. Reusing
  the underinsurance ratio here would be the exact error this model is built to refuse.
* **An insurer's published body franchise table** (first-claim and subsequent-claim
  rates, minimum amounts, driver age and licence-history surcharges, a reduction where
  the insured was not at fault, a distinct theft rate). The page carries no version or
  effective date and some minima look legacy, so it is registered as a *calibration
  candidate* for `U02` and no rate from it reaches the graph.
* **Endorsement schedules** for standalone glass, parts theft (including a
  fifty-per-cent-of-new limit on tyres, battery and spare wheel, and the insurer's right
  to withdraw the parts-theft risk after a claim), loss of use, and price-fluctuation
  increases. All are `POLICY`-class, company-specific. They define the *fields*
  `Q-S3-05`/`Q-S6-06` must read; they do not populate them.
* **A third-party diminution-of-value instruction** dated 1403 with an explicit
  formula. It corroborates that `U09` is a live third-party topic with real current
  authority behind it, and it is registered as a secondary mirror pending an official
  copy. It does not touch the body branches, where diminution of value is an exclusion.

## 8. Limits of this layer

* **Liveness of an uncertainty is evaluated in code**, in
  `Review.uncertainty_is_live`, mirroring each node's `live_only_when` clause. It is
  testable and explicit, but it is a second statement of the same rule and must be kept
  in step with the data.
* **Questionnaire answers are not a legal record.** The emitted case is a calculation
  input; the review JSON is the audit artefact, and only `Q-S10-01` records who signed
  it.
* **No evidence is verified.** `evidence_present` is an assertion by the reviewer. The
  layer reports what is demanded and what is claimed; it cannot see the documents.
* **Date handling is deliberately thin**: a leading year between 1300 and 1500 is read
  as Shamsi to derive the claim year. Working-day arithmetic for the notice deadline,
  and any Shamsi/Gregorian conversion, are not implemented — the model records the
  judgement (`Q-S0-04`) rather than computing it.
* **Free-text answers are confined to identification and sign-off** (`Q-S0-01`,
  `Q-S10-01`). A narrative field can never move an amount, by construction.
