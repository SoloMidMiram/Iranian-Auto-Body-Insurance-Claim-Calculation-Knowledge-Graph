# G0 independent import integrity

**PASS | 2026-11-22, Asia/Tehran**

The supplied workstation paths were used only to transfer the eight evidence files into an isolated WSL Linux directory. The source checkout and historical virtual environment were not used for execution. The imported bundle supplied all project inputs and code. A new CPython 3.11.16 venv used cached offline dependencies.

`sha256sum -c G0_IMPORT_PACKAGE.zip.sha256` exited 0. ZIP SHA-256 is `1971e62685ff7d2a9332a20421ded20614e9dabdf45ade5f21ff5c3f4765f99a`. Python ZIP verification checked all 19 members against the standalone inventory and verified 18 internal SHA-256 entries. The standalone and enclosed manifests matched byte-for-byte. Both authorized index hashes, all 14 indexed sources, the original D-01 through D-04 editorial lines and all 56 ledger, register, comparison and observation pointers verified. Every case input in the detached checkout matched its indexed SHA-256. The authorized replacement evidence entry point was Source Index v1.0.0. The original reconciliation report remains NOT RECOVERED.

The archive includes `evidence/import.log` and `evidence/outer-sha256.log`. The recovery report, recovery provenance and Git search log were historical context.
