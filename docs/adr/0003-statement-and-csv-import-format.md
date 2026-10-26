# ADR 0003: Statement and CSV Import Format (resolves OI-7)

- **Status:** Accepted
- **Date:** 2026-10-26
- **Owner:** Shashank A
- **Requirements:** OI-7, FR7, FR9, NFR6, SASD 4.3

## Context

FR7 requires bulk import of expenses via CSV or standard statement upload without live bank account connectivity. SASD 4.6 (OI-7) leaves open the accepted column layout, accepted file types, validation constraints, and row-level error reporting structure. Shreya requires a concrete specification to implement the import job and parser for Issue #7.

## Decision

1. **File Format & Limits:**
   - Format: Standard CSV (`text/csv`, `.csv`) encoded in UTF-8.
   - Max file size: 5 MB (NFR6 DoS protection).
   - Max batch size: 1,000 rows per upload.

2. **Column Layout:**
   Case-insensitive header row with the following column names:
   - `date` *(Mandatory)*: `YYYY-MM-DD` or `DD/MM/YYYY`. Converted to ISO 8601 `YYYY-MM-DD`.
   - `amount` *(Mandatory)*: Exact numeric decimal string (e.g., `450.00`). Must be `> 0` (D1).
   - `category` *(Optional)*: Matched against existing user or system categories. Unmatched rows are filed as "Uncategorized" and queued for advisory suggestion (FR9, D8).
   - `merchant` *(Optional)*: Merchant string (up to 255 chars).
   - `payment_mode` *(Optional)*: One of `cash`, `debit_card`, `credit_card`, `upi`, `net_banking`, `other`. Defaults to `other`.
   - `notes` *(Optional)*: Text remarks.

3. **Row-Level Validation & Error Reporting:**
   Individual malformed rows do not reject the entire import job. Valid rows are persisted atomically with audit rows, and malformed rows are returned in the response with 1-indexed row numbers:
   ```json
   {
     "total_rows": 100,
     "accepted_count": 98,
     "rejected_count": 2,
     "errors": [
       {
         "row_number": 14,
         "field": "amount",
         "error_code": "INVALID_AMOUNT",
         "message": "Amount must be a positive decimal number.",
         "raw_value": "-25.00"
       }
     ]
   }
   ```

## Consequences

- Completely decouples the application from complex, volatile third-party bank scrapers.
- Provides immediate, actionable row-by-row feedback to the user on import errors.
- Unblocks Shreya for Expense model and import development.
