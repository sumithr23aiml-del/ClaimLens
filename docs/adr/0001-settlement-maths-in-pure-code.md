\# ADR-0001: Settlement arithmetic is deterministic code, never a model



\*\*Status:\*\* Accepted



\## Context



A predicted settlement amount cannot be explained to a regulator or a customer.



Deductible, depreciation, sub-limits and co-insurance interact in a specific, contractually defined order.



\## Decision



`libs/claim\_domain/settlement.py` implements the calculation as pure functions applied in a fixed, documented order.



Models may extract inputs and flag risk, but may never produce the payable amount.



Each settlement stores its component lines.



\## Consequences



\- Every payment decomposes into named, arguable components.

\- A change in policy wording is a code change with a test, not a retrain.

\- Unusual policy structures need explicit implementation.

\- Straight-through processing is bounded by rule coverage, not model recall.

