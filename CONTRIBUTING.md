# Contributing

This is a legal/financial decision-support project. A green test suite does not
authorize a legal conclusion or production payment.

## Workflow

1. Select or create an issue from `planning/issues.json`.
2. Add the smallest failing case that demonstrates the required behavior.
3. Make the implementation, schema, or knowledge change.
4. Run the full gate in `docs/VALIDATION_GATES.md`.
5. Open a PR containing source evidence, affected branches, risk, validation
   output, and rollback instructions.

Use the issue ID in commits, for example:

```text
fix(P0-04): cap Article 8 payment by actual proven loss
```

## Knowledge changes

An amount-affecting knowledge change must include:

- Publishing authority and source class.
- Stable document locator and retrieval date.
- Instrument, article, effective date, and version/supersession status.
- Exact structured payload and affected branches/operators.
- Confidence or explicit blocking uncertainty.
- At least one positive, boundary, and refusal/regression case.
- Human review when the change contradicts or supersedes existing knowledge.

Do not treat an insurer FAQ, educational article, or third-party mirror as the
publishing authority. Mirrors may support accessibility but must be identified
as mirrors.

## Claim data and privacy

Never commit real names, national identifiers, policy numbers, vehicle plates,
phone numbers, addresses, photos, or unredacted claim documents. Golden cases
must be anonymized and reviewed for re-identification risk.

## Pull-request review

Calculation or source changes require engineering review and a domain reviewer.
No author may self-approve a change that alters eligibility, operator order,
deductions, caps, annual parameters, or insurer procedures.
