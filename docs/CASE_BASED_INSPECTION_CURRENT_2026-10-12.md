# Case-based inspection — accepted integration reconciliation

Date: 12 October 2026. This is current-state inspection evidence, not a
calculation change, legal approval, or release approval. The historical
expectations and observations remain unchanged in `CASE_BASED_INSPECTION.md`.
Release remains **BLOCKED**.

## Revision record

| Role | Commit | Tree | Note |
|---|---|---|---|
| Historical accepted parent | `a8a20472172fbb5700adcf7c52df639830fbd9f2` | `150091f01bbff30495abc29094a3e5a5e79070f3` | Original baseline comparator |
| Historical inspected PR #56 candidate | `6f655f178379c182947b28e29ff0fc7153d8e522` | `14b8e77c97abd4590f5eec4d72f852021fd1e9ae` | Original candidate comparator |
| PR #56 final head | `2df0f73508ce6de4d5bf252e981a381625a9b536` | `4c594155cf9404def9bb32896c711985f3abccb8` | Merged second parent |
| Accepted integration | `cd7fb39a0b7859f2cec91b94770e240ab62e0b75` | `4c594155cf9404def9bb32896c711985f3abccb8` | Merge parents: `a8a2047…`, `2df0f73…` |
| Original local inspection commit | `fde74a95275c2b82cd31c5f5006e22ee20087ec5` | `648034c8741422ce2e5ce7f55a48bbf894379944` | Preserved before rebase; parent `a8a2047…` |
| Rebased inspection commit | `1fcda6490d46dbb8e487483f00bcd2fad06c5917` | `1b7f34ca455cf705fdf3c5806ac79be65e7d0439` | Unpublished; parent `cd7fb39…` |

Live verification found no intervening integration commits. PR #48 remains open
against `main`; issue #49 remains the open release tracker. PR #56 has six
resolved review threads, but all eleven submitted review records are
`COMMENTED`. There is no `APPROVED` engineering or domain review in the GitHub
record. Thread resolution and green CI are not retroactive approval under
`CONTRIBUTING.md`.

## Evidence preservation and runner integrity

The historical package contains 49 files: 47 synthetic review submissions,
one report, and one runner. Before its local commit:

- all JSON parsed, all 47 synthetic `claim_id` values were unique, and every
  full case digest matched the prefix recorded in the historical report;
- staged whitespace was clean and no unrelated file was included;
- privacy scanning found no real name, national identifier, telephone number,
  address, plate, policy number, image, or unredacted claim document;
- the cases use synthetic reviewer, insurer, policy, document, and amount data;
- reference expectations remain the pre-execution arithmetic and authority
  analysis in the historical report, not copied model output; and
- the runner has no network or remote-action path. Its only write is the
  explicitly requested `--output` file.

The runner now replaces inherited `PYTHONPATH` with the selected worktree's
`src` directory, disables user-site imports, verifies
`iran_auto_claim.__file__` is below that directory, and records the resolved
import path. With `--internal`, the checked-input scope also includes
`tests/admission_shim.py`; a clean isolated worker records and verifies the
shim, engine-helper, authorization-helper, knowledge, and package origins. The
worker and parent identities are compared, and the parent rechecks the selected
revision, tree, and cleanliness after collection. This prevents a competing
checkout or uncommitted internal shim from silently changing the evidence.

The bounded override investigation uses the same isolation primitives. It
removes cached `iran_auto_claim` modules, selects `<root>/src`, and fails closed
unless the implementation, knowledge, Review, and authorization helper origins
all belong to the selected `--root`.

## Reproduction commands and current results

All commands used Python 3.11.15. The accepted integration ran in a detached,
clean worktree at `cd7fb39…`; the refreshed evidence resolved imports under
`/tmp/body-model-review-base-cd7fb39/src/iran_auto_claim/` and the internal shim
at `/tmp/body-model-review-base-cd7fb39/tests/admission_shim.py`.

```bash
python scripts/run_case_based_inspection.py \
  --root /tmp/body-model-review-base-cd7fb39 \
  --cases /tmp/body-model-pr57-comparator/cases \
  --internal \
  --output docs/case-inspection-current-cd7fb39.json
# exit 0: 47 supported cases, 14 INTERNAL_TEST_DIRECT probes

python scripts/investigate_total_loss_override.py \
  --root /tmp/body-model-review-base-cd7fb39 \
  --cases /tmp/body-model-pr57-comparator/cases \
  --output docs/override-investigation-cd7fb39.json
# exit 0: 9 direct variants, 3 supported-Review controls
```

The repository gate at the exact integration revision passed:

| Gate | Fresh result |
|---|---|
| Interpreter | Python 3.11.15 |
| Compile | pass |
| Knowledge validation | pass; 22 body-authority and 48 source-metadata findings remain |
| Fixtures | 50/50 |
| Pytest | 621 passed, 4 xfailed |
| Mutation gate | 29/29 killed |
| Generated Review docs | current |
| Bilingual FAQ | current |
| Issue manifest | valid dry run: 8 milestones, 11 labels, 29 issues |

The current 47 supported rows contain 21 `COMPUTE`, 14
`INSUFFICIENT_INFORMATION`, eight `SCENARIO_SET`, and four input-contract
refusals. Twenty rows contain one payable and one contains payable scenarios.
Review exits are 43 zero / four nonzero; `calc` exits are 29 zero / eighteen
nonzero. The 14 internal probes contain eight settled controls, five
`CLASSIFICATION_EVIDENCE_REQUIRED`, and one `CLASSIFICATION_CONFLICT`.

The historical `case-comparison-current-cd7fb39.json` joins every observed row and full input
digest to the independently fixed reference summary and its prose locator. It
contains the pre-correction labels 37 matches and ten discrepancies. Those
labels are preserved as a **historical observation**, not a current acceptance
result. The enforceable manifest and corrected derived-verdict policy are in
`CASE_COMPARATOR_V1.md`. The ten historical discrepancies are not all model defects:
the machine-readable disposition separates two confirmed defects (IA-05 and
IA-08), unresolved authority, unsupported scope, incomplete evidence, and one
explicit implementation inference. A `MATCH` likewise does not authenticate
the legal source supporting the reference.

The current report is field-for-field unchanged from the historical `6f655f1…`
report for all comparison fields and all 14 internal rows. This is expected:
the accepted integration tree equals the final PR #56 head tree. Relative to
`a8a2047…`, the same seven supported cases and fourteen internal rows retain the
historically documented IA-03/IA-04 changes; the original report remains the
controlling explanation of those differences.

## Residual override investigation

The suspected final-branch risk is **confirmed at the internal calculation
boundary**, but its precise trigger is narrower than “missing rescue” alone.
The full machine record is `override-investigation-cd7fb39.json`.

All direct variants start with evidence-derived `THEFT`, a documented override
selecting `TOTAL_LOSS`, market and insured value 10,000 unless removed, a
versioned absolute franchise of 1,000, retained salvage explicitly evidenced as
zero, and otherwise complete eligibility facts.

| Variant | Observed | Assessment |
|---|---|---|
| Missing repair, explicit classification rescue zero | `AUTHORIZED_OVERRIDE`; **9,000 payable** | Confirmed defect: threshold-required repair evidence is absent |
| Missing repair, actual rescue 200 | `AUTHORIZED_OVERRIDE`; **9,200 payable** | Confirmed defect: actual rescue does not create repair evidence |
| Missing repair and rescue | `AUTHORIZED_OVERRIDE`; **9,000 payable** | Confirmed defect: the missing-rescue gate is conditioned on repair being present |
| Repair present, rescue omitted | `CLASSIFICATION_EVIDENCE_REQUIRED`; no payable | Correct containment |
| Missing repair, conflicting rescue operands | `CLASSIFICATION_EVIDENCE_REQUIRED`; no payable | Correct containment |
| Missing market | structured `INPUT_ERROR`; no payable | Contained at settlement boundary, though classification first says override |
| Missing repair and market | structured `INPUT_ERROR`; no payable | Contained by missing market, not by repair completeness |
| Complete override | `AUTHORIZED_OVERRIDE`; 9,000 payable | Valid control; override path remains available |
| Ordinary theft without override | `PENDING_60_DAY_CRITERION`; no payable | Valid control; threshold evidence is not imposed on genuine theft |

Cause: `reconcile_classification()` only calls its missing repair/market gap for
declared total loss when the preliminary branch is `PARTIAL_DAMAGE`. Theft is
selected before the threshold. The unresolved-rescue gate's preliminary-zero
clause also requires both repair and market to exist. When repair is absent,
neither predicate reports a gap, the override selects total loss, and
`calculate_total_loss()` treats an indeterminate threshold as overrideable
before settlement.

The supported Review interface has no field that mints
`classification.override`; it therefore cannot reproduce the override itself.
Supported controls show that ordinary theft may correctly authorize without a
repair assessment or rescue amount, while missing market value remains
`INSUFFICIENT_INFORMATION`. This distinction must be preserved: the fix belongs
to an override-selected threshold branch, not to theft generally.

Recommended separate remediation: add a final-candidate operand-completeness
gate before honoring a threshold-branch override. A total-loss candidate must
have repair/replacement assessment, event-date market value, and resolved
classification rescue. The regression must cover the three payable variants
above, missing market, conflicting rescue, a complete override, and ordinary
theft. No runtime change is made by this inspection branch.

## Authority and governance state

Fresh validation preserves 22 body-authority and 48 source-metadata findings.
Every one of the sixteen registered sources is missing a content hash, complete
effective interval, and revalidation date (three findings each). In addition,
the executable body chain still reports primary mirrors, missing reviewers,
and declared/composed branch mismatches.

- No legal source is fully authenticated under the repository's integrity and
  effective-date contract. The Central Insurance compilation is recorded as a
  prior retrieval, not independently authenticated here.
- Regulation 53 mirrors and the Iran Insurance-hosted general conditions are
  secondary access paths, not authenticated official originals with amendment
  history.
- The circular and other items classed `PRIMARY` still lack hashes, complete
  applicability intervals, locators/revalidation, or human review as reported.
- Insurer endorsement and franchise pages are not an issued, versioned policy
  artifact applicable to these synthetic cases.
- Insurer procedure pages and educational sources remain practice or secondary
  evidence and cannot activate a monetary rule.

These limits leave IA-05/IA-14 disposition evidence and IA-08 contractual
authority subject to domain review. The merged state must not be represented as
satisfying the absent engineering/domain approvals. PR #48 remains unmerged and
release issue #49 remains controlling.

## Disposition

The reconciled inspection branch is technically reproducible and suitable for
a separate documentation/inspection PR after its second local commit, but it is
not a release approval. Publication should disclose the confirmed residual
override defect, preserve the four strict expected failures, request independent
engineering and domain review, and keep release **BLOCKED**.
