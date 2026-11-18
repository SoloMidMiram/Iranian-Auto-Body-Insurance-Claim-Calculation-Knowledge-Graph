# Settlement evidence and operator sequencing

These are bounded software controls. Synthetic records support regression calculations; real source-review assertions still require external authentication and domain acceptance.

## Physical total loss

```mermaid
flowchart TD
  A["Complete physical total-loss evidence"] --> B{"Explicit supported disposition?"}
  B -- "Missing, unresolved or not applicable" --> N["SALVAGE_DISPOSITION_UNRESOLVED: no payable"]
  B -- "Conflicting facts" --> X["Structured conflicting_alias: no payable; identify documents"]
  B -- "Insured retains" --> C{"Valuation amount bound?"}
  C -- "No, even with a source token" --> V["SALVAGE_VALUE_REQUIRED: no payable"]
  C -- "Yes, including explicit zero" --> D{"Supporting valuation evidence?"}
  D -- "No" --> E["SALVAGE_VALUATION_EVIDENCE_REQUIRED: no payable"]
  D -- "Yes" --> F["Deduct salvage once"]
  B -- "Insurer ownership route" --> G{"Completed transfer AND supporting proof?"}
  G -- "No, pending, missing or unproved" --> T["TITLE_TRANSFER_REQUIRED: no payable"]
  G -- "Yes" --> H["No salvage deduction on this route"]
  F --> J["Validate franchise authority and remaining conditions"]
  H --> J
  J --> K["Supported settlement, separate rescue, insured ceiling, zero floor"]
```

This does not impose transfer on every physical loss. Whole theft retains separate classification/time/transfer gates and its established ownership route.

## Franchise authority

```mermaid
flowchart TD
  A["Proposed monetary term"] --> B{"Mode, amount/rate, named base and minimum complete?"}
  B -- "No" --> N["Structured terms required: no payable"]
  B -- "Yes" --> C{"Instrument reference and version nonblank?"}
  C -- "No, positive or zero" --> U["FRANCHISE_AUTHORITY_REQUIRED: no payable; U02"]
  C -- "Yes" --> D{"Reviewed source status, hash, locator and reviewer?"}
  D -- "Missing or unresolved" --> U
  D -- "Recorded review" --> E{"Governs this insurer/product/policy and coverage?"}
  E -- "No or unknown" --> U
  E -- "Yes" --> F{"Interval covers BOTH policy and event dates?"}
  F -- "No, missing date or wrong version" --> U
  F -- "Yes" --> G{"Exact terms bound and declarations agree?"}
  G -- "No" --> H["Authority/terms conflict: no payable; retain competing evidence"]
  G -- "Yes" --> I["Apply supported term and record provenance/guards"]
```

A manual's existence is insufficient without governing-contract evidence. Unsupported evidence does not establish that a rate is legally invalid. SYNTHETIC_TEST requires matching synthetic context. VERIFIED is a recorded review attestation, not authentication performed by the calculator.

## Partial loss: Article 10 and franchise

```mermaid
flowchart TD
  A["Eligible loss after supported replacement depreciation"] --> B{"Market and insured sum established?"}
  B -- "No" --> N["Value evidence required: no single payable"]
  B -- "Yes" --> C["Derive capped ratio"]
  C --> D{"Ratio equals one?"}
  D -- "Yes" --> E["No numerical ratio effect; ordinary supported arithmetic"]
  D -- "No" --> F{"Selected order has matching applicable authority record?"}
  F -- "Token only, absent, inapplicable or conflicting" --> G["Execute both existing plans"]
  G --> H["Controlled example: preserve 700 and 720; never average or choose lower"]
  H --> I["ORDER_UNRESOLVED; U01; single payable null; request authority"]
  F -- "Yes" --> J["Execute only that record's bound order"]
  E --> K["Supported rescue, limits, floor, trace and result"]
  J --> K
```

Controlled arithmetic: `(1,000 × .8) − 100 = 700` and `(1,000 − 100) × .8 = 720`, with rescue zero. Equal amounts in another claim do not prove universal legal order; unresolved underinsured equal alternatives remain explicit.
