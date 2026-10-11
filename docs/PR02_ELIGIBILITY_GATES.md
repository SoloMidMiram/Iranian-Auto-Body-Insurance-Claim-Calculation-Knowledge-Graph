# PR-02 eligibility admission gates

Release verdict: **BLOCKED**

Scope: IA-01 prior-compensation containment and IA-02 positive covered-peril
causation only. This PR does not implement a contribution, remainder, recourse,
or allocation formula and does not change the causation predicate for an
exclusion.

## Integration parent and environment

| Item | Verified value |
|---|---|
| Target branch | `fix/body-runtime-blockers` |
| PR-02 branch | `fix/pr02-eligibility-admission` |
| Exact parent | `9859b9c736df98f6a27c69953083b64bbdb1165a` |
| Parent tree | `698016030ab5764538ab1eda56e1bdb60f03ac45` |
| Parent meaning | Merge commit for PR #54 / accepted PR-01 integration head |
| Preparation worktree | `/tmp/body-model-pr02`, clean before preparation |
| Interpreter | CPython 3.11.15 |
| Pip | 24.0, invoked as `/tmp/body-model-pr02-venv311/bin/python -m pip` |

The pre-existing primary worktree was dirty and remains untouched. PR-02 was
created in an isolated worktree from the fetched remote integration head. The
final PR-01 commit `a103bd239502fe580724e156a1c04d09b49d2b39` is the second parent
of the merge and has the same files; PR-02 nevertheless uses the merge commit,
not the earlier reviewed commit, as its parent.

## Exact parent reproduction

Environment creation and installation:

```bash
/usr/bin/python3.11 -m venv /tmp/body-model-pr02-venv311
/tmp/body-model-pr02-venv311/bin/python -m pip install -e '.[test]'
```

Repository gate, all exit `0` at the exact parent:

```bash
/tmp/body-model-pr02-venv311/bin/python -m compileall -q claim.py src scripts
/tmp/body-model-pr02-venv311/bin/python claim.py validate
/tmp/body-model-pr02-venv311/bin/python claim.py fixtures
/tmp/body-model-pr02-venv311/bin/python -m pytest -p no:cacheprovider -rxX
/tmp/body-model-pr02-venv311/bin/python scripts/run_mutation_gate.py --check-report
/tmp/body-model-pr02-venv311/bin/python scripts/sync_review_docs.py
/tmp/body-model-pr02-venv311/bin/python scripts/sync_customer_faq.py
/tmp/body-model-pr02-venv311/bin/python scripts/sync_github_issues.py \
  --repo SoloMidMiram/Iranian-Auto-Body-Insurance-Claim-Calculation-Knowledge-Graph
```

Observed parent result: compilation passed; knowledge validation passed
structurally with the existing 22 body-authority and 48 source-metadata findings;
fixtures passed 50/50; pytest reported **559 passed and 8 expected failures**;
the 24/24 mutation report, generated Review documents, bilingual FAQ, issue
manifest, JSON parsing, and whitespace checks were current.

The selected defect probe was:

```bash
/tmp/body-model-pr02-venv311/bin/python -m pytest \
  tests/test_stage0_counterexamples.py::test_ia01_prior_compensation_blocks_a_single_payable \
  tests/test_stage0_counterexamples.py::test_ia02_asserted_only_causation_blocks_a_single_payable \
  --runxfail -q
```

It exited `1` with exactly two failures. IA-01 returned a single payable of
1,657,000,000 IRR after 1,850,000,000 IRR prior compensation was supplied.
IA-02 returned the same payable when Q-S2-02 was `ASSERTED_ONLY`. Both failures
were the named defect, not collection, schema, or setup errors.

## Implementation-head reproduction

The same Python 3.11 environment ran the complete repository gate after the
bounded changes. Every command exited `0`:

```bash
/tmp/body-model-pr02-venv311/bin/python -m compileall -q claim.py src scripts
/tmp/body-model-pr02-venv311/bin/python claim.py validate
/tmp/body-model-pr02-venv311/bin/python claim.py fixtures
/tmp/body-model-pr02-venv311/bin/python -m pytest
/tmp/body-model-pr02-venv311/bin/python scripts/run_mutation_gate.py --check-report
/tmp/body-model-pr02-venv311/bin/python scripts/sync_review_docs.py
/tmp/body-model-pr02-venv311/bin/python scripts/sync_customer_faq.py
/tmp/body-model-pr02-venv311/bin/python scripts/sync_github_issues.py \
  --repo SoloMidMiram/Iranian-Auto-Body-Insurance-Claim-Calculation-Knowledge-Graph
git diff --check
```

Fresh results: **587 passed, 6 expected failures**, 50/50 fixtures passed, the
checked 24/24 mutation report remained current, generated Review and FAQ files
were current, and the issue manifest remained valid at 8 milestones, 11 labels,
and 29 issues. The two repaired tests also exited `0` when run with `--runxfail`.
The structural validator retained the pre-existing 22 body-authority and 48
source-metadata findings; this PR neither resolves nor suppresses them.

## End-to-end fact trace

| Fact | Questionnaire | Parameter slot | Normalized case | Authorization | Parent engine behavior |
|---|---|---|---|---|---|
| Positive covered-peril causation | Q-S2-02 | `PS_CAUSATION_ESTABLISHED` | `coverage_gate.causal_relationship_established` | Included in the immutable claim snapshot only when `ESTABLISHED` | Ignored as a positive admission predicate |
| Other policy covering the same vehicle/risk | Q-S6-05 | `PS_MULTIPLE_POLICIES.state` | `policy.multiple_insurance.state` | Included in the immutable claim snapshot | Ignored by body settlement |
| Compensation already received for the same damage, from any source | Q-S9-03 | `PS_MULTIPLE_POLICIES.prior_compensation` | `policy.multiple_insurance.prior_compensation` | Included in the immutable claim snapshot | Ignored by body settlement |

`prior_compensation` is broader than another-policy payment because Q-S9-03
explicitly asks about compensation from **any source**. A responsible-third-party
payment may therefore coexist with `state=NO`; that combination is not called a
contradiction. It is blocked because the model has no approved remainder,
contribution, or coordination operator for a positive recovery.

The current Article 21 slot description says a body insurer may settle and then
pursue contribution. PR-02 does not turn temporary engine incompleteness into a
legal rule. A `YES_OTHER_POLICIES` or `YES_SAME_INSURER` case is temporarily
blocked and explicitly labeled `MULTIPLE_INSURANCE_CONTRIBUTION_NOT_IMPLEMENTED`
until a reviewed implementation can preserve that settlement/contribution
distinction.

## Admission contracts

### Positive covered-peril causation

| Review fact | Review outcome | Engine-boundary outcome |
|---|---|---|
| `ESTABLISHED` plus required assessment evidence | Continue to the remaining gates | Continue when the canonical boolean is exactly `true` |
| `ESTABLISHED` but required assessment evidence missing | `INSUFFICIENT_INFORMATION`; no authorization | Not applicable to a valid Review authorization |
| `ASSERTED_ONLY` | `INSUFFICIENT_INFORMATION`; no authorization | Missing/false canonical predicate is nonpayable |
| `UNKNOWN` or omitted | `INSUFFICIENT_INFORMATION`; question remains open | Missing canonical predicate is nonpayable |
| `CONTRADICTED` | Preserve the existing `REFUSE` decision | A direct boolean cannot encode why it is false, so the engine only blocks |

This is a new positive-admission guard. `G_NO_ASSUMED_CAUSATION` retains its
existing, narrower meaning: an exclusion whose own predicate requires causation
may fire only when that exclusion causation is established. PR-02 does not reuse
or redefine that guard.

### Prior recovery and multiple insurance

Zero and omission remain distinct.

| Other-policy state | Prior compensation | Outcome |
|---|---:|---|
| `NO` | documented `0` | May continue through the remaining gates |
| `NO` | positive partial or full amount | Block unsupported settlement; do not label the facts contradictory |
| `YES_OTHER_POLICIES` or `YES_SAME_INSURER` | `0` | Temporarily block because contribution handling is not implemented |
| `YES_OTHER_POLICIES` or `YES_SAME_INSURER` | positive | Block positive recovery and record the contribution limitation |
| `UNKNOWN` or omitted | any | `INSUFFICIENT_INFORMATION` / nonpayable at the engine boundary |
| Any state | omitted amount | Missing recovery fact; never normalize omission to zero |

The canonical object must carry both `state` and `prior_compensation`. The schema
will reject a partially populated object. A wholly missing object remains
representable so the engine can fail closed instead of inventing a zero.

The synthetic P01-L50 body fixtures declare their shared positive-control facts
explicitly (`causal_relationship_established=true`, `state=NO`, and
`prior_compensation=0`). These are fixture data only; neither the schema nor the
engine supplies them as defaults.

## Bounded implementation

1. Add typed `Case` accessors that preserve missing versus zero for covered-peril
   causation, other-policy state, and prior compensation.
2. Add a dedicated positive-causation guard and a separate recovery/allocation
   containment guard. Keep `G_NO_ASSUMED_CAUSATION` unchanged.
3. Make Review decision conditions block asserted-only positive causation,
   positive prior compensation, and the temporarily unsupported multiple-policy
   path before authorization.
4. Run the same invariants in the engine before exclusion evaluation so an
   internal authorization cannot expose a payable from missing/unsafe facts.
5. Require both properties when `policy.multiple_insurance` is present and add
   descriptions that preserve the two facts' different scopes.
6. Add Review and internal-boundary matrices, retain valid zero/established
   controls, and remove only the IA-01 and IA-02 strict-xfail markers.
7. Update generated Review references and the bilingual customer FAQ to explain
   that asserted causation is insufficient and positive recovery blocks only
   because allocation is not implemented.

No contribution amount, proportional share, unrecovered-loss formula, automatic
denial, or new payment authority is introduced.

## Acceptance matrix

- Both repaired Stage 0 counterexamples pass normally.
- Review-blocked cases issue no `CalculationAuthorization` and calculate no
  payable.
- Internal test authorizations with missing/false causation, missing/unknown
  recovery facts, positive compensation, or multiple-policy state return a
  specific nonpayable guard result.
- Established causation plus `state=NO` and explicit zero recovery preserves the
  supported T1 payable.
- Exclusion-causation regressions and `G_NO_ASSUMED_CAUSATION` remain unchanged.
- Six strict expected failures remain: IA-03, IA-04, IA-05, IA-08, and the two
  IA-14 cases.
- The complete Python 3.11 repository gate passes from the implementation head.

Historical counts in `STAGE0_REMEDIATION_BASELINE.md` remain unchanged. Release
stays **BLOCKED** after PR-02.
