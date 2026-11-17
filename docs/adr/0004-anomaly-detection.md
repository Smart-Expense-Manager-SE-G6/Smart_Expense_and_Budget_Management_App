# ADR-0004: Explainable spending anomaly detection

- **Status:** Accepted
- **Date:** 2026-11-17
- **Decision owners:** Team 6
- **Traceability:** FR17, NFR14, issue #78

## Context

The application should identify unusually large expenses without requiring a trained machine-learning model. The rule must be explainable, deterministic, and safe for a new user with too little history.

## Decision

When an active expense is created, the service examines the user's five most recent earlier, non-deleted expenses in the same category. It computes their exact `Decimal` average. An anomaly alert is created only when:

1. all five historical expenses exist; and
2. the new amount is strictly greater than three times that average.

The alert stores the related expense, category, historical average in its message, and `alert_type="anomaly"`. Re-evaluating the same expense does not create a duplicate alert.

## Consequences

- The rule is deterministic and auditable in `backend/alerts/services.py`.
- New users do not receive anomaly alerts until five comparable transactions exist.
- The query is scoped by owner, category, non-deleted state, date and creation order.
- Threshold alerts remain a separate alert type and retain their conditional uniqueness constraint.
- This is a rule-based signal, not a claim of fraud or financial advice; users decide what action to take.

## Verification

The behavior is covered by `backend/alerts/tests.py` and is traced from `FR17` in `docs/rtm.md`.
