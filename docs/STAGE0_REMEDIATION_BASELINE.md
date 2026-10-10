# Stage 0 remediation baseline

Baseline date: 2026-10-09

Python 3.11 reproduction: 2026-10-10

Release verdict: **BLOCK**

Scope: reproducibility, test integrity, and counterexample registration only. No
payable, eligibility, operator, or authority semantics are changed here.

## Pinned inputs

| Item | Identifier |
|---|---|
| Intended integration branch | `fix/body-runtime-blockers` |
| GitHub integration head / PR parent | `a159aaedaae8a0f8142f3c45675e8b11a9cd0fd8` |
| Reported local equivalent revision | `2c2bc24a269384056ce7a6f275c77ca38bb38cf7` |
| Tree shared by both revisions | `0512a3e4c96ebd30f1ac271a3a3c883042d3ac5d` |
| Required audit path | `tests/independent-body-model-audit-a159aaed.md` |
| Audit SHA-256 | `93d695d6670ee368532d23c6d49c9e44d45f14ffd9f47ce90c69a1efeee92c1f` |
| Audit Git blob | `de721fed602a9bd657191ada8b29491ffdeccc6d` |
| GitHub audit-only commit | `c8e99a41cdee4d823f4f725ae30dbfdcecb3ebfa` |
| Local audit-only commit | `d5db1b8427423515bd54db385c7188a0ab7c775e` |
| Audit head reproduced before this documentation update | `730d5e0736266836e6abde9154d310f94bc8098b` |
| Audit-head parent | `c8e99a41cdee4d823f4f725ae30dbfdcecb3ebfa` |

The local and GitHub integration revisions have independent commit identities but
the same complete tree. The Stage 0 GitHub branch was therefore created directly
from the verified GitHub integration head; no shared history was rewritten.

At the time of preparation, GitHub compared `fix/body-runtime-blockers` with
`main` as `diverged`: the integration branch was seven commits ahead and one
commit behind, with merge base
`7b23f639c5ffee3c18bb84cc77cfdeee89f29c9f` and current `main` head
`37b1765af89121bf04ef590f729f1cd861e3c254`. This PR deliberately targets the
requested integration branch and does not merge or rebase `main`.

Accepting this audit PR only pins Stage 0 evidence on
`fix/body-runtime-blockers`. It does **not** merge PR #48 into `main`, approve
PR #48's runtime changes, or change the release verdict. The runtime branch
remains subject to the counterexamples recorded below.

## Isolated environment

Reproduction was performed from the actual remote audit head in an isolated
worktree. The original dirty worktree and its unrelated changes were not edited.
The virtual environment, package installation, and every Python validation
command used CPython 3.11 exclusively. Dependencies were installed with that
interpreter's bound pip:

```bash
/usr/bin/python3.11 -m venv /tmp/body-model-stage0-py311
/tmp/body-model-stage0-py311/bin/python -m pip install -e '.[test]'
```

Resolved versions:

| Component | Version |
|---|---|
| Python | 3.11.15 |
| pip | 24.0 |
| iran-auto-claim | 1.0.0, editable checkout |
| pytest | 9.1.1 |
| iniconfig | 2.3.1 |
| packaging | 26.3 |
| pluggy | 1.6.0 |
| Pygments | 2.21.0 |

## Commands and evidence

The independent assertion command extracts the unchanged assertion block from
the pinned audit and executes it against the checkout named by its first
argument.

```bash
/tmp/body-model-stage0-py311/bin/python -m compileall -q claim.py src scripts
/tmp/body-model-stage0-py311/bin/python claim.py validate
/tmp/body-model-stage0-py311/bin/python claim.py fixtures
/tmp/body-model-stage0-py311/bin/python -m pytest -p no:cacheprovider -rxX
# Diagnostic probe: expected exit 1 with 2 controls passing and the 11 named counterexamples failing.
/tmp/body-model-stage0-py311/bin/python -m pytest tests/test_stage0_counterexamples.py --runxfail -q
/tmp/body-model-stage0-py311/bin/python -c "from pathlib import Path; text=Path('tests/independent-body-model-audit-a159aaed.md').read_text(encoding='utf-8'); section=text.split('### Independent invariant assertions',1)[1]; fence=chr(96)*3; source=section.split(fence+'python',1)[1].split(fence,1)[0]; exec(compile(source,'independent-invariant-assertions','exec'))" /tmp/body-model-stage0-311
/tmp/body-model-stage0-py311/bin/python scripts/run_mutation_gate.py --check-report
/tmp/body-model-stage0-py311/bin/python scripts/sync_review_docs.py
/tmp/body-model-stage0-py311/bin/python scripts/sync_customer_faq.py
/tmp/body-model-stage0-py311/bin/python scripts/sync_github_issues.py --repo SoloMidMiram/Iranian-Auto-Body-Insurance-Claim-Calculation-Knowledge-Graph
```

| Check | Previously recorded parent result | Python 3.11 audit-head result |
|---|---|---|
| Compile | Passed | Passed |
| Knowledge validation | Passed with 22 body-authority and 48 source-metadata findings | Passed with the same findings |
| Fixture runner | 50/50 passed | 50/50 passed |
| Pytest | 507 passed | 515 passed, 11 expected-failed, 0 failed, 0 skipped; 526 collected |
| Expected-failure probe | Not applicable | With xfail disabled: 2 controls passed and exactly the 11 registered counterexamples failed; no counterexample passed unexpectedly |
| Independent invariants | 51/51 passed | 51/51 passed |
| Curated mutation gate | Report current, 24/24 mutants killed | Report current, 24/24 mutants killed |
| Review-document sync | Current | Current, including the shipped test reference |
| Customer-FAQ sync | Current | Current |
| Issue manifest sync | Dry run passed: 8 milestones, 11 labels, 29 issues | Same |
| Clean-checkout integrated gate | Not applicable | Fresh detached checkout and fresh Python 3.11 virtual environment passed every command above; JSON parsing and `git diff --check` also passed |

The parent-side `507 passed` result is preserved as recorded evidence and was
not substituted for the audit-head reproduction. The audit head itself is now
reproduced under Python 3.11.15 with the exact result above. Direct shell
fetch/push remains unavailable because the checkout has no HTTPS Git credential;
publishing this update requires the repository's authenticated GitHub path.

## Collection integrity

The pre-edit AST scan found exactly two duplicate definitions in
`tests/test_provenance.py`: `_required_evidence` and
`test_evidence_confidence_counts_boolean_values_not_key_presence`, each at lines
51 and 90/103 respectively. Both formerly shadowed copies now have unique names,
so all eight parametrized instances collect. A repository-wide AST regression
test rejects duplicate function, async-function, or class names within each
Python test namespace.

The stale generated blocks in `tests/BODY_CASE_REVIEW_MODEL.md` now match the
canonical document, and a regression check compares every shipped generated
block, including promotion rules.

## Strict expected-failure inventory

| Finding | Collected counterexamples | Required future invariant |
|---|---:|---|
| IA-01 | 1 | Positive prior compensation cannot coexist with one payable |
| IA-02 | 1 | Asserted-only causation cannot authorize payment |
| IA-03 | 1 | Repair-only work receives no replacement-part depreciation |
| IA-04 | 1 | The bound rescue operand participates in total-loss classification |
| IA-05 | 1 | Incomplete title transfer cannot use the insurer-title settlement route |
| IA-07 | 2 | Invalid dates and production-after-event chronology cannot pay |
| IA-08 | 1 | An unversioned manual cannot establish a monetary franchise |
| IA-15 | 1 | Unequal monetary aliases receive structured rejection |
| IA-14 | 2 | Missing disposition or retained-but-unvalued salvage cannot pay through the internal boundary |

All 11 markers use `xfail(strict=True)`. No marker unexpectedly passed in the
Python 3.11 reproduction. A separate `--runxfail` probe confirmed each marker
still maps to its named unresolved behavior rather than an unrelated collection
or setup failure. A repaired invariant therefore becomes an XPASS failure until
its remediation PR removes the marker and records the before/after evidence.
The controls pin the supported T1 Review result at
1,657,000,000 IRR and a complete internal retained-salvage total-loss result at
1,600 IRR.

Deferred registration is explicit: IA-06's substantive theft-clock switch;
IA-09's franchise/salvage authority choice; IA-10's notice and subrogation
adjudication; IA-11 graph execution contract; IA-12 dependency provenance;
IA-13 resolution-artifact activation; and IA-14 token-only glass and complete
issuer-isolation cases remain for their bounded roadmap PRs. Partial work on
IA-06 or IA-13 is not closure.

## Remaining prerequisites

- The authenticated GitHub path must publish this Python 3.11 evidence update
  and confirm the PR gate on the resulting head.
- The integration branch's one-commit divergence behind `main` must be handled by
  the branch owner in a separately authorized synchronization; Stage 0 does not
  choose or perform that history operation.
- Authority-dependent questions and artifacts listed in the audit remain open;
  none is activated by this baseline.
- Release stays **BLOCK**. The next bounded engineering task is PR-01, canonical
  dates and values for IA-07 and IA-15.
