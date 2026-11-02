# Validation report

Executed revision: 249cc6918f01548484175d5853f0aa153f4ab851. Python 3.11.4.
Outputs are retained in the fresh local directory; exact command metadata and hashes are in validation-summary.json.
Comparator failures remain failures; successful execution checks cannot grant independent acceptance.

| Command | Exit | Output SHA-256 |
|---|---|---|
| python -m compileall -q claim.py src scripts | 0 | e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855 |
| python claim.py validate | 0 | 226bc0f321c0bf7a5921bee25189a9ea7b0dcaa82816f00909a0207814aec5ec |
| python claim.py fixtures | 0 | c430f13c9462653d8e7c255a5a62d3b88301013e1f328c44eeb89ac5c7c4a2e1 |
| python -m pytest -o addopts= -q -ra --basetemp .runtime/rc1-final-pathfix/pytest | 0 | a366928037c1c92d9d16091063603347a111f49419ff688bb13221f21db06a33 |
| python -m pytest -o addopts= -q -ra --runxfail tests/test_stage0_counterexamples.py | 0 | e462e15257a235e68b6a04f5cd1fdfbef88b6a743e89d980355576b5fec651f4 |
| python -m pytest -o addopts= -q tests/test_properties.py tests/test_plans.py tests/test_guard_paths.py | 0 | d0115429a6d472e3fa6320ce026cd9324ad2c9868d15599acd41d21ae0613712 |
| python scripts/run_mutation_gate.py --check-report | 0 | c4483af30af1b9b1d29698a396365cc2cec14bfc678969b136ef2adde6c232db |
| python scripts/sync_review_docs.py | 0 | b404cee9c080168fd3bca01afc62e58158fb0f52d796cf67689e80193dfb11a7 |
| python scripts/sync_customer_faq.py | 0 | 7629522f07d381e0fed379128b63651796dc39e7469bf33ff689300b93205f72 |
| python scripts/sync_github_issues.py --repo SoloMidMiram/Iranian-Auto-Body-Insurance-Claim-Calculation-Knowledge-Graph | 0 | f657c186e5d0e0076db16c5f0fca0a0c369c8aa1500d5437d2fda38a3382692a |
| python scripts/run_case_based_inspection.py --root . --cases cases --internal --output .runtime/rc1-final-pathfix/original-observation.json | 0 | 5427d8d10c01dd220c9d168b846cec5c145325d19ae707fc24a508b3e428d14a |
| python scripts/build_case_comparison.py .runtime/rc1-final-pathfix/original-observation.json .runtime/rc1-final-pathfix/original-comparison.json --model-root . --cases cases --manifest docs/case-reference-manifest-v1.json | 1 | 6085f7470d3e54a4ef16f4cb599f3d5ba2747764d8a48d9a614032848fcfb6ab |
| python scripts/run_case_based_inspection.py --root . --cases docs/reconciliation-evidence/synthetic-v1 --output .runtime/rc1-final-pathfix/synthetic-observation.json | 0 | 28d487225c5a3312bd1f2d099d6b631c0da80f6a29c0ba39356970a25422fa53 |
| python scripts/build_case_comparison.py .runtime/rc1-final-pathfix/synthetic-observation.json .runtime/rc1-final-pathfix/synthetic-comparison.json --model-root . --cases docs/reconciliation-evidence/synthetic-v1 --manifest docs/reconciliation-evidence/synthetic-reference-v1.json | 1 | 28ce77dfb641807d7f1738e88c51527c7f66ce365071f8ebe905629cecf84c8c |
| python scripts/run_integration_rc1_audit.py --output .runtime/rc1-final-pathfix/s03-s10 --original-comparison .runtime/rc1-final-pathfix/original-comparison.json --synthetic-comparison .runtime/rc1-final-pathfix/synthetic-comparison.json | 0 | 8c5d5d43b89daa45a05e0e96ba02300ac1b985e7092965d941c8fb4094dbfd39 |

Full pytest summary:
........................................................................ [ 93%]
.....................................................                    [100%]
=========================== short test summary info ===========================
SKIPPED [1] tests\test_inspection_byte_integrity.py:125: Host does not permit creation of symlinks: [WinError 1314] A required privilege is not held by the client: 'F:\\Git\\body model\\.qwen\\worktrees\\rc1-followup\\.runtime\\rc1-final-pathfix\\pytest\\test_reject_in_root_symlink_su0\\repo\\original.py' -> 'F:\\Git\\body model\\.qwen\\worktrees\\rc1-followup\\.runtime\\rc1-final-pathfix\\pytest\\test_reject_in_root_symlink_su0\\repo\\src\\model.py'
772 passed, 1 skipped in 206.77s (0:03:26)
