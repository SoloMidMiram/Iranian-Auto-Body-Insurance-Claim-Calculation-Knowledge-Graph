# Reusable tool calls and interpretation

Use functions, not repeated investigative prompts. These tools do not authorize financial decisions or remote writes.

| Question | Call | Interpretation / next action |
|---|---|---|
| Where am I? | `python scripts/project_context.py brief` | Dirty count is inventory, not ownership. HEAD identifies committed base, not uncommitted candidate. |
| Where is a rule used? | `python scripts/project_context.py find PS_RESCUE_THRESHOLD --limit 10` | Literal references, not complete semantic coverage. Narrow the keyword if truncated; no match is not proof of unused code. |
| What can I commit? | `python scripts/agent_workflow.py changes` | Separate staged, unstaged and untracked paths. Inspect diffs and select an explicit allowlist; never auto-stage the list. |
| What failed? | `python scripts/agent_workflow.py regress path/to/current.xml --baseline path/to/baseline.xml` | Compares JUnit outcomes by test identity. Newly failing does not establish root cause; inspect the linked log. Missing tests are reported, never treated as passing. |
| Is context maintained? | `python scripts/project_context.py check` | Bookkeeping only. Checks revision references, dates and links; does not fetch PRs or rerun tests. |
| Is public admission correct? | `python scripts/replay_body_tutorial.py` when present | Public blocked outcomes can be correct. Arithmetic-only INTERNAL_TEST_DIRECT evidence cannot replace public authorization. |

For regression collection run `python -m pytest --junitxml=<artifact-path>`; preserve the exit code and full log. The compact report limits displayed failures, not total counts. No automatic retries, fixture rewrites, guessed zeros or expected-value updates.

Read the helper implementation only to modify/debug it. For independent reads use a batched tool call; keep mutations and checks sequential. Capture verbose tool outputs in local artifacts; return paths and concise facts. Do not send whole PR bodies or unrelated logs back into the model when metadata fields suffice.

Remote publication: verify the PR head; compare every upload path against the remote tree. Construct a child of the current remote commit, preserve the base tree, and update the branch with an expected-head lease and no force. A changed lease requires reinspection, not retrying blindly. Upload only user-authorized files. PR description drafts are local until the user asks to publish the text.
