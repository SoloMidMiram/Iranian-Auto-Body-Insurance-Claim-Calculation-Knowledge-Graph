# Eleven-case disposition

All dispositions are author engineering findings, with human review PENDING. CASE_DISPOSITIONS.json binds exact inputs, revision, expected/actual decisions, authorization, parameters, traces, guards, amounts and residual assertions. Frozen original and synthetic reference expectations remain unchanged.

| Case | Disposition | Correction, containment or scope implication |
|---|---|---|
| C104 | CONTRACT_AUTHORITY_PENDING | Date binding works; governing clock anchor is not authenticated. Whole-theft certification blocked |
| C35 | ENGINEERING_DEFECT_CONFIRMED | Itemised category predicates now bind new price/interaction; inline per-item prices are not required twice |
| C48 | ENGINEERING_DEFECT_CONFIRMED | Selected assessor intent survives emission; missing amount blocks both boundaries rather than falling back to per-part computation |
| C61 | INTERFACE_CONTRACT_MISMATCH | Incomplete title transfer blocks payment. Frozen uncertainty name differs from current blocking condition |
| C64 | CONTRACT_AUTHORITY_PENDING | Explicit synthetic SETTLEMENT_BASE is not a real contract/circular approval. Pre-salvage contractual scope blocked |
| C66 | CORRECT_FAIL_CLOSED_BEHAVIOR | Unknown salvage disposition refuses a grant. Frozen empty-scenario grant requires reference review |
| C67 | CORRECT_FAIL_CLOSED_BEHAVIOR | NOT_APPLICABLE is not an evidenced physical ownership route. No money; label mapping pending |
| C72 | CORRECT_FAIL_CLOSED_BEHAVIOR | Unsupported token cannot select one amount; both scenarios retained. Frozen no-grant interface needs review |
| C97 | ENGINEERING_DEFECT_CONFIRMED | Unadjudicated notice now blocks Review/direct calculation; not universal exclusion or zero |
| C98 | ENGINEERING_DEFECT_CONFIRMED | Unadjudicated recovery impairment now blocks Review/direct calculation; mere evidence tokens do not resolve predicates |
| C99 | OUT_OF_RELEASE_SCOPE | Third-party split interface lacks the expected branch. No body payable; body precedence controls remain tested |

Financial regressions first failed on exact parent 3c26b9b: final test_rc1_residuals.py produced six failures and five passes in a disposable parent worktree. Parent output is retained locally and its proof summary is linked by validation metadata. Provenance tests separately reproduced seventeen parent failures before correction. Corrections: 3c26b9b (byte integrity), 9d59ca8 (complete stale-model fixture), 50d6a49 (assessment/eligibility gates), 6d09d8d (inline-price regression and audit harness).

The first corrected synthetic run at 50d6a49 exposed additional C31–C34 overblocking. It was repaired, with four explicit controls, rather than changing inputs or counting stronger refusal as automatically acceptable. Later comparison failures that only reflect uncertainty/condition representation remain failures pending an independent interface/reference decision. No expected amount is derived from model output. Actual source, law and contract disputes remain separate from reproducible engineering defects.
