# Decisions on Open Issues: OI-3 and OI-7

- **Author:** Shashank A (`PES2UG24CS461`)
- **Role:** Analytics & Reports Module Owner, QA Lead
- **Date:** 2026-10-26
- **Status:** Approved / Ground Truth Baseline

---

## 1. OI-3: Report and Chart Date Range Cap (NFR2, FR19, FR20)

### Context & Problem Statement
SASD Section 4.6 (OI-3) and Table 5 (Risk R3): Without an enforced upper bound on date ranges for custom reports and analytics charts, queries against unbounded historical ranges could cause database timeouts or memory spikes, breaching NFR2 (report generation within 5 seconds for a 1-year data range) and NFR1.

### Decision
1. **Maximum Range Enforced:** The API and frontend will enforce a **strict 366-day (1 calendar year)** date range limit on all custom report queries (`POST /api/v1/reports`) and analytics date-filter endpoints (`/api/v1/analytics/*`).
2. **Validation Rule:**
   - `start_date <= end_date`
   - `(end_date - start_date).days <= 366`
3. **API Error Response (SASD 4.4 Envelope):**
   If a user requests a range exceeding 366 days, the endpoint immediately returns HTTP 400:
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
4. **UI Behavior:**
   - The date picker component automatically restricts the end date selection once the start date is chosen, preventing the selection of dates beyond 1 year.
   - Presets provided: "This Month", "Last Month", "Last 3 Months", "Last 6 Months", "Last 12 Months / 1 Year".

---

## 2. OI-7: CSV and Bank Statement Import Format (FR7)

### Context & Problem Statement
SASD Section 4.3 & 4.6 (OI-7): Users need to bulk-import expenses via CSV or standard statement uploads without bank direct connectivity. Shreya (Expense module owner) needs the precise column specification, validation rules, and row-level error handling format to implement FR7.

### Decision

### 2.1 File Specification
- **File Type:** Standard CSV (`text/csv`, `.csv`) encoded in UTF-8.
- **Maximum File Size:** 5 MB (NFR6 / DoS mitigation).
- **Maximum Rows per Import:** 1,000 rows per upload batch.

### 2.2 Expected Column Headers (Case-Insensitive)
The CSV file must contain a header row with the following column names:
1. `date` *(Mandatory)*: ISO format `YYYY-MM-DD` or `DD/MM/YYYY`. Converted to `YYYY-MM-DD` internally.
2. `amount` *(Mandatory)*: Numeric decimal string (e.g. `125.50` or `1250`). Must be strictly greater than 0.
3. `category` *(Optional)*: Category name string. If matched with user's categories or default categories, assigns that category. If blank or unmatched, assigns "Uncategorized" and flags for advisory suggestion (FR9).
4. `merchant` *(Optional)*: Merchant / vendor name string (up to 255 chars). Used for rule-based category suggestion.
5. `payment_mode` *(Optional)*: One of `cash`, `debit_card`, `credit_card`, `upi`, `net_banking`, `other`. Defaults to `other` if blank or unrecognized.
6. `notes` *(Optional)*: Text string description / remarks.

#### Sample Valid CSV:
```csv
date,amount,category,merchant,payment_mode,notes
2026-10-15,450.00,Food & Dining,Swiggy,upi,Dinner with friends
2026-10-16,1200.00,Fuel,Shell,credit_card,Petrol
2026-10-17,799.00,Bills,Airtel,net_banking,Broadband bill
```

### 2.3 Row-Level Validation & Error Reporting (SASD 4.3 / 4.4)
The import process is an all-or-partial batch job. Individual bad rows **do not** fail the entire file. The API processes every row and returns summary counts alongside per-row error details:

**Endpoint:** `POST /api/v1/expenses/import`
**Response (HTTP 200 / 202):**
```json
{
  "total_rows": 3,
  "accepted_count": 2,
  "rejected_count": 1,
  "errors": [
    {
      "row_number": 2,
      "field": "amount",
      "error_code": "INVALID_AMOUNT",
      "message": "Amount must be a positive number.",
      "raw_value": "-50.00"
    }
  ]
}
```

This unblocks Shreya for Issue #7 and ensures consistent validation across the entire system.
