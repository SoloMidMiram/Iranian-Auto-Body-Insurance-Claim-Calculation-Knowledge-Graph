# G0 Git ancestry and candidate identity

| Role | Commit | Tree | Sole parent |
| --- | --- | --- | --- |
| Strategy B runtime executed for this review | `1b41798f5725aa3d9bf8fce8cc8063a2baa45ea6` | `d511963f90a18d695af2daf15e1f9014fe2759fe` | `30df73b3c8e74c956118867789619999d30083d9` |
| Persian tutorial documentation child | `a1a03d900df968da29d3a42255c8741613aaacb0` | `6f3d89dba0b9c9b42df1208c4999aff04db978c6` | `1b41798f5725aa3d9bf8fce8cc8063a2baa45ea6` |

`git init`, `git bundle verify`, `git bundle list-heads`, `git fetch --no-tags`, `git fsck --full --strict`, `git show -s --format=%H %T %P`, `git merge-base --is-ancestor`, `git diff --check` and detached checkout all exited 0. The bundle advertises the single ref `refs/heads/codex/rc1-persian-tutorial`. The child changes 49 paths under `docs/`, listed in `evidence/candidate-diff.tsv`. All fresh behavioral execution ran at the Strategy B runtime commit. The detached checkout had no tracked changes after execution. No hosted CI was checked.
