# ADR 0002: Report and Chart Date Range Cap (resolves OI-3)

- **Status:** Accepted
- **Date:** 2026-10-26
- **Owner:** Shashank A
- **Requirements:** OI-3, FR19, FR20, NFR1, NFR2, R3

## Context

SASD Section 4.6 (OI-3) and Table 5 (Risk R3) identify that unbounded date ranges for custom reports and analytics charts could trigger full-table sequential scans over the transaction store. NFR1 mandates sub-3s response times on up to 10,000 transactions, and NFR2 mandates report generation within 5 seconds for a 1-year data range. 

Without an enforced upper bound, queries across multi-year ranges would cause PostgreSQL memory spikes, CPU exhaustion, and potential Denial of Service (DoS) conditions.

## Options Considered

1. **No Range Limit (Unbounded):** Rely purely on database indexes and background workers.
   - *Rejected:* Breaches NFR2; leaves the API vulnerable to resource exhaustion.
2. **Soft Limit with Asynchronous Processing:** If range > 90 days, convert to a background task.
   - *Rejected for v1.0:* Adds unnecessary queue/worker complexity (Celery/Redis) not needed for personal expense tracking.
3. **Hard Cap of 366 Days (1 Calendar Year) with HTTP 400 Validation (Chosen):**
   - Strictly enforces that no single custom query or export exceeds 366 days.

## Decision

Enforce a **maximum date range cap of 366 days (1 calendar year)** across all report and analytics endpoints:

1. **Validation Logic:**
   - `start_date` and `end_date` are required query parameters in ISO 8601 (`YYYY-MM-DD`).
   - Must satisfy: `start_date <= end_date` and `(end_date - start_date).days <= 366`.
2. **Standard Error Envelope (SASD 4.4):**
   When the cap is exceeded, the API returns HTTP 400:
   ```json
   {
     "error": {
       "code": "DATE_RANGE_EXCEEDED",
       "message": "Report date range cannot exceed 366 days (1 year). Please select a narrower date range.",
       "field": "date_range",
       "request_id": "<request_id>"
     }
   }
   ```
3. **UI Behavior:**
   - Date pickers default to presets: "This Month", "Last Month", "Last 3 Months", "Last 6 Months", "Last 1 Year".
   - The UI disables selection of dates beyond 366 days from the chosen `start_date`.

## Consequences

- Guarantees NFR2 (report generation under 5s) and bounds query execution time over composite indexes `(user_id, date)`.
- Users who need multi-year trends must use the year-over-year comparison endpoint (`/api/v1/analytics/comparison`), which queries pre-aggregated monthly buckets rather than raw transactions.
