# Black-Box Test Report

## Objective and scope
Record executable black-box evidence and distinguish it from proposed partitions and boundaries.

## Executed tests

| ID | Technique/scenario | Expected | Actual | Status |
|---|---|---|---|---|
| BB-FE-001 | Valid status input equivalence | Known status maps correctly | Passed | PASS |
| BB-FE-002 | Invalid/missing status equivalence | Unknown status remains explicit | Passed | PASS |

## Proposed but not executed

The following remain NOT RUN: valid/invalid registration credentials, amount boundaries (zero/negative/precision), missing/oversized receipts, duplicate categories/budgets, CSV malformed rows, export failures, permission failures, session expiry, and protected-route authentication failures. These are proposed scenarios, not results.

## Exact command

```powershell
npm.cmd test --prefix frontend
```

## Limitation

Backend, API, and browser black-box checks require unavailable Python/Docker infrastructure.
