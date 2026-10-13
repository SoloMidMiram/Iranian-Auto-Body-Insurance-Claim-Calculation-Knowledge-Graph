# Inspection reference comparator v1

This document defines the acceptance semantics for
`case-reference-manifest-v1.json`. It does not approve a payment, authenticate a
legal source, close a release finding, or change runtime behavior. Release
remains **BLOCKED**.

## Reference and observation separation

The manifest is a versioned, reviewed input. Each of the 47 entries contains the
case identifier and exact input SHA-256, a reference-basis classification,
source and rule locators, applicability dates, unit and operator order, a
derivation, explicit review status, typed Review/authorization/calculation
expectations, blocking uncertainties, selected material trace assertions, and
accepted limitations. The runner never creates or updates this file.

Reference authority, observed behavior, and known implementation defects are
separate objects in the comparison report:

- `reference_authority` says what supports an expectation and how far that
  support reaches. It is not a verdict.
- `observed_behavior` comes from fresh supported-path Review and `calc`
  processes. The Review authorization object is recorded directly. Process exit
  status is recorded separately and is not treated as authorization.
- `known_implementation_defect` is an exact, reviewed drift envelope. If the
  current observation differs from both the reference and this envelope, the
  result is a new `MISMATCH`.

The manifest contains no `MATCH`, `DISCREPANCY`, success flag, or disposition
that the comparator can copy. Verdicts are derived assertion by assertion.
Missing fields fail. Money is normalized as exact integer IRR through
`Decimal`; binary floating-point comparison is not used.

## Acceptance gate

The comparator exits nonzero for a malformed manifest; duplicate, missing or
unexpected case; stale case digest; observation that does not describe the
current case bytes; or any assertion that matches neither the reference nor an
exact registered deviation.

`KNOWN_DEVIATION` is accepted only for drift detection. It is never converted
to `MATCH`, never establishes calculation correctness, and remains
release-blocking. Changing either a reference expectation or a known-deviation
envelope requires review of the manifest change.

The old comparator's `37 MATCH / 10 DISCREPANCY` is retained in the manifest as
`HISTORICAL_PRE_CORRECTED_COMPARATOR_OBSERVATION`. It is not an acceptance
result. At reviewed head `fa214d940cbfe79389ff1269800e52a69bff13b8`, the
corrected comparator derives:

- 37 `MATCH`;
- 10 `KNOWN_DEVIATION`;
- zero new `MISMATCH`; and
- acceptance gate `PASS`, with release still **BLOCKED** by every known
  deviation and the repository's outstanding authority/review findings.

The full derived report is preserved in
`docs/case-comparison-pr57-fa214d.json`; its revision identifies the inspected
parent behavior, while this PR changes only evidence tooling and documentation.

## Reference status

All 47 entries are structurally available for independent review, but they are
not all independently authority-verifiable. Every registered external source
lacks a content hash, complete effective interval, and revalidation evidence.
No case is therefore classified `PRIMARY_AUTHORITY` in v1.

Sixteen references are explicitly `UNRESOLVED`:

`C31`, `C32`, `C33`, `C34`, `C35`, `C64`, `C67`, `C71`, `C72`, `C81`, `C83`,
`C97`, `C98`, `C99`, `C104`, and `C106`.

In addition, C101 and C102 are `CONTRACT_TERM` cases whose required wording or
versioned schedule is incomplete, and C74 is a `DOMAIN_ASSUMPTION` because its
no-double-ratio result uses a documented implementation inference. Plausible
arithmetic in these cases is not promoted to a legally confirmed payment.

### Follow-up provenance relevance audit

The v1 manifest's 47 references were rechecked case by case after the initial
engineering review. This was a locator-relevance audit, not independent legal
authentication. Coverage by reference basis was:

- `CONTRACT_TERM` (2): C101, C102;
- `CONTROLLED_MATH` (13): C105, C13A, C13B, C13D, C21MIX, C41, C42, C43,
  C44, C46, C62, C63, C73;
- `DOMAIN_ASSUMPTION` (1): C74;
- `ENGINEERING_INVARIANT` (15): C13C, C45, C47, C48, C61, C65, C66, C82,
  C84, C91, C92, C93, C94, C95, C96; and
- `UNRESOLVED` (16): C104, C106, C31U04, C32U04, C33U04, C34U04, C35Q404,
  C64, C67, C71, C72, C81, C83, C97, C98, C99.

Seven reference records required metadata-only corrections. C102 now cites the
glass-endorsement wording and Article 10 uncertainty nodes; C81 cites the risk-
intensification premium-ratio mechanism; and C83 cites policy-state,
cancellation, policy-copy and premium-proof requirements. C97 and C98 were
narrowed respectively to notice and subrogation adjudication. C73 no longer
cites an order uncertainty that is immaterial when the ratio is capped at one,
and C74 now cites the documented no-double-underinsurance inference instead of
an unrelated salvage circular. No case bytes, input digests, typed expected
results, known-deviation envelopes, basis classifications, or authority-status
classifications changed.

The remaining locators were relevant to their case mechanisms; no additional
franchise-template or notice/subrogation copy-over was identified. Automated
checks now pin the corrected locator families and verify that every manifest
source ID resolves to the registered source catalogue. Independent reference
review remains pending, and the source authentication limitations above remain
unchanged.

## Reproduction

Use Python 3.11 from a clean, pinned worktree:

```bash
python scripts/run_case_based_inspection.py \
  --root . \
  --cases cases \
  --internal \
  --output /tmp/case-inspection.json

python scripts/build_case_comparison.py \
  /tmp/case-inspection.json \
  /tmp/case-comparison.json \
  --manifest docs/case-reference-manifest-v1.json \
  --cases cases
```

The adversarial regression suite mutates copies in pytest temporary directories;
it never rewrites the committed corpus. It covers the C42 strict-threshold
crossing, C45 omitted-versus-zero rescue distinction, authorization withdrawal,
same-branch payable drift, digest-only drift, missing/duplicate cases, and a
material trace change. An autouse integrity check verifies the original case
digests and `git diff -- cases` after every test.

```bash
python -m pytest -q tests/test_case_comparison.py
```

Fresh independent engineering review is still required for the comparator and
manifest. Domain/legal review must authenticate applicable source text,
effective dates and amendment history, and obtain the missing insurer
worksheets, schedules and endorsement wording before unresolved expectations
can become authority-backed payment conclusions.
