\# ADR-0002: Policy snapshot is immutable at FNOL



\*\*Status:\*\* Accepted



\## Context



Policy terms can be amended after a loss is reported.



Claims must be adjudicated against the policy terms that were in force when the loss was reported.



\## Decision



At FNOL, create an immutable `policy\_snapshots` record containing:



\- Policy version

\- Coverage limits

\- Deductibles

\- Waiting periods

\- Exclusions



All downstream agents read the snapshot, never the live policy.



\## Consequences



\- Historical claims remain reproducible.

\- Mid-claim policy changes cannot affect an existing claim.

\- Snapshot creation is a mandatory FNOL transaction.

