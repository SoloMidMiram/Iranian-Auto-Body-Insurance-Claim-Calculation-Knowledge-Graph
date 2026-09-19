# Security and sensitive-data policy

## Supported posture

The repository is intended to remain private during investigation and pilot.
The current engine is decision-support software and is not approved for
unattended claim settlement.

## Reporting

Report security, privacy, source-integrity, or payment-correctness defects
privately to the repository owner. Do not place claimant data or exploit details
in a public issue.

## Sensitive data

Real claim documents and personally identifiable information must not be stored
in this repository, issue bodies, CI logs, or test artifacts. Use synthetic or
approved anonymized cases. Secrets and GitHub tokens must be supplied through a
secret manager or environment variable and never committed.

## High-impact defect handling

A defect that can produce a wrong payable, hide an uncertainty, select the
wrong legal/policy version, or corrupt the audit history is P0. Disable the
affected scope, preserve the calculation snapshot, add a regression case, and
complete a reviewed fix before re-enabling it.
