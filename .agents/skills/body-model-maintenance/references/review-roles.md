# Review roles, not autonomous agents

Use one relevant perspective at a time; no extra agent or model call is required.

- Implementer: identify the invariant, reproduce the failure, make the smallest change, show affected public behavior.
- Regression reviewer: challenge helpers/defaults, verify omitted evidence stays omitted, distinguish newly failing from pre-existing failures, check exact candidate identity.
- Domain/provenance reviewer: separate source authenticity, policy applicability and arithmetic. Name the unresolved decision; never manufacture approval.
- Release recorder: record branch/PR/head, command exits and blockers, preserve separate engineering/domain/release verdicts. A green report is not permission to merge.

These perspectives provide review questions, not independent certification. Only spawn agents when the user or applicable instructions authorize delegation.
