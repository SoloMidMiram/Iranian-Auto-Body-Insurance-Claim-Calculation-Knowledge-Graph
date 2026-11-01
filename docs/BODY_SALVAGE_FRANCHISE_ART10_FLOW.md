# Settlement authority target flows — work in progress

These are acceptance requirements, not a claim that all gates are implemented.

```mermaid
flowchart TD
  A["Physical total loss established"] --> B{"Explicit supported salvage disposition?"}
  B -- "Missing, conflicting, unresolved or not applicable" --> N["Evidence required: no single payable"]
  B -- "Insured retains" --> C{"Supported valuation including evidenced zero?"}
  C -- "No" --> N
  C -- "Yes" --> D["Deduct salvage once"]
  B -- "Insurer ownership route" --> E{"Transfer completed and proof present?"}
  E -- "No" --> N
  E -- "Yes" --> F["No salvage deduction on this route"]
  D --> G["Validate applicable franchise authority"]
  F --> G
  G --> H["Settlement with supported rescue and insured ceiling"]
```

```mermaid
flowchart TD
  A["Proposed monetary franchise"] --> B{"Reference and instrument version identifiable?"}
  B -- "No" --> N["FRANCHISE_AUTHORITY_REQUIRED: no payable"]
  B -- "Yes" --> C{"Source authenticated and governs this insurer/product contract?"}
  C -- "Unknown or no" --> N
  C -- "Yes" --> D{"Coverage, claim type, policy/event dates and effective version match?"}
  D -- "No" --> N
  D -- "Yes" --> E{"Conflicting terms resolved by applicable authority?"}
  E -- "No" --> N
  E -- "Yes" --> F{"Mode, amount/rate, named base, minimum and sequence supported?"}
  F -- "No" --> N
  F -- "Yes" --> G["Apply the supported term; zero requires the same evidence standard"]
```

```mermaid
flowchart TD
  A["Partial damage after supported replacement depreciation"] --> B{"Market and insured sum established?"}
  B -- "No" --> N["Evidence required: no single payable"]
  B -- "Yes" --> C["Derive capped Article 10 ratio"]
  C --> D{"Applicable instrument establishes operator order?"}
  D -- "No, conflicting or questionnaire token only" --> E["Retain both derivations: 700 and 720 in controlled example"]
  E --> F["U01 explicit; single payable null; request ordering authority"]
  D -- "Yes, scope and provenance verified" --> G["Run authorized sequence, supported rescue, limits and floor"]
  G --> H["Record exact formula, authority and guards"]
```

Ratio one or equal mathematical outcomes do not prove a universal legal sequence. Whole theft retains its separate ownership/time conditions.
