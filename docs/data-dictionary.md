# Physical Schema and Data Dictionary (OI-5)

- **Document Version:** 1.0
- **Date:** 2026-10-26
- **Author / Module Owner:** Shashank A (`PES2UG24CS461`)
- **Reviewers:** Shriram Chandrasekar, Shreya S Mattimadu, Shashwath K R
- **Traceability:** SRS v1.0, SASD v1.0 Section 3.5, 3.6, 4.1 (D1–D8), OI-5, OI-3, OI-7

---

## 1. Architectural & Design Decisions Ground Truth

All models and database tables defined below strictly enforce the design rules from SASD Section 4.1:
1. **D1 (Exact Decimal Representation):** All financial amounts (`amount`, `limit_amount`, etc.) are defined as `DECIMAL(12, 2)` (supporting up to 9,999,999,999.99). **Never use floating point.**
2. **D2 (Explicit Budget Periods):** Every budget row records explicit `start_date` and `end_date` date fields.
3. **D3 (Recurring Rule Materialization):** `RecurringExpenseRule` records the schedule and template. A scheduler job materializes individual `Expense` rows when due.
4. **D4 (Soft Deletion of Expenses):** `Expense` records contain `is_deleted = models.BooleanField(default=False)` and `deleted_at = models.DateTimeField(null=True, blank=True)`. Soft-deleted rows are excluded from user queries, budget utilization, and analytics, but preserved for audit trail and past report integrity.
5. **D5 (De-duplicated Threshold Alerts):** `Alert` records enforce a database unique constraint on `(budget, threshold_percentage, period_start)` so alerts are raised exactly once per budget threshold per period.
6. **D6 (Secure Receipt Storage):** Receipts are stored in a dedicated directory outside the web root (`media/receipts/`), referenced by file path, and served only via authenticated permission-checked endpoints.
7. **D7 (Time Zone Alignment):** Timestamps are stored in UTC (`created_at`, `updated_at`). Budget periods and daily aggregation are evaluated in the user's configured IANA time zone (`User.timezone`, default `Asia/Kolkata`).
8. **D8 (Advisory Category Suggestion):** Category auto-suggestions are advisory; users confirm or override.
9. **SASD 3.5 / R3 (Performance Indexes):** Compound indexes on `(user_id, date)` and `(user_id, category_id)` are applied directly on `expenses` to guarantee sub-3s query execution across 10,000 transactions (NFR1).

---

## 2. Entity-Relationship Overview

```
 +-----------------------------------------------------------------------------------+
 |                                   accounts_user                                   |
 |  id (PK), email (UQ), password, timezone, is_active, is_staff, created_at, ...    |
 +-----------------------------------------------------------------------------------+
       ^          ^                      ^                   ^               ^
       |          |                      |                   |               |
       | 1:N      | 1:N                  | 1:N               | 1:N           | 1:N
       |          |                      |                   |               |
 +-----+--+   +---+--------+      +------+-----+      +------+-----+   +-----+------+
 |category|   |  expense   |      |rec_expense |      |   budget   |   | audit_log  |
 |(cat_*) |   |  (exp_*)   |      |  (rec_*)   |      |  (bdg_*)   |   | (audit_*)  |
 +-----+--+   +---+---+----+      +------+-----+      +------+-----+   +------------+
       ^          |   |                  |                   |
       |          |   | (receipt path)   |                   | 1:N
       +----------+   v                  |                   v
       | 1:N       [media/receipts/]     |            +------+-----+
       |                                 |            |    alert   |
       +---------------------------------+            |   (alt_*)  |
                                                      +------------+
```

---

## 3. Data Dictionary

### 3.1 `accounts_user` (Django App: `accounts`, Table: `accounts_user`)
Implemented in `accounts/models.py`.

| Column Name | PostgreSQL Type | Nullable | Default | Constraints / Description |
|---|---|---|---|---|
| `id` | `BIGSERIAL` | No | Auto | Primary Key |
| `email` | `VARCHAR(254)` | No | - | Unique, user login identifier |
| `password` | `VARCHAR(128)` | No | - | Salted bcrypt hash (`PBKDF2`/`bcrypt`) |
| `timezone` | `VARCHAR(64)` | No | `'Asia/Kolkata'` | Validated IANA time zone (D7) |
| `is_active` | `BOOLEAN` | No | `True` | Account active status |
| `is_staff` | `BOOLEAN` | No | `False` | Staff access flag |
| `is_superuser` | `BOOLEAN` | No | `False` | Superuser flag |
| `date_joined` | `TIMESTAMPTZ` | No | `CURRENT_TIMESTAMP` | Registration date |
| `last_login` | `TIMESTAMPTZ` | Yes | `NULL` | Timestamp of last authentication |

---

### 3.2 `expenses_category` (Django App: `expenses`, Table: `expenses_category`)
Managed by **Shreya S Mattimadu** (FR8, FR9). A nullable `owner_id`
identifies global categories (`NULL`) versus user-owned categories. Default
global categories are seeded by the expenses migration.

| Column Name | PostgreSQL Type | Nullable | Default | Constraints / Description |
|---|---|---|---|---|
| `id` | `BIGSERIAL` | No | Auto | Primary Key |
| `owner_id` | `BIGINT` | Yes | `NULL` | FK -> `accounts_user.id` (ON DELETE CASCADE). `NULL` indicates a global default category. |
| `name` | `VARCHAR(100)` | No | - | Category name (e.g., 'Food & Dining', 'Travel') |
| `parent_id` | `BIGINT` | Yes | `NULL` | FK -> `expenses_category.id` (ON DELETE RESTRICT) for subcategories |
| `is_active` | `BOOLEAN` | No | `True` | Active categories are listed and accepted for expense assignment |
| `created_at` | `TIMESTAMPTZ` | No | `CURRENT_TIMESTAMP` | Record creation timestamp |
| `updated_at` | `TIMESTAMPTZ` | No | `CURRENT_TIMESTAMP` | Last updated timestamp |

**Indexes & Constraints:**
- Case-insensitive global names are unique.
- Case-insensitive custom names are unique per owner.
- Self-parenting is prohibited; API validation prevents deeper circular hierarchies.

---

### 3.3 `expenses_expense` (Django App: `expenses`, Table: `expenses_expense`)
Managed by **Shreya S Mattimadu** (FR4, FR5, D1, D4, D6).

| Column Name | PostgreSQL Type | Nullable | Default | Constraints / Description |
|---|---|---|---|---|
| `id` | `BIGSERIAL` | No | Auto | Primary Key |
| `user_id` | `BIGINT` | No | - | FK -> `accounts_user.id` (ON DELETE CASCADE) |
| `category_id` | `BIGINT` | No | - | FK -> `categories_category.id` (ON DELETE RESTRICT) |
| `amount` | `DECIMAL(12, 2)` | No | - | Exact decimal currency amount; CHECK (`amount > 0`) (D1) |
| `date` | `DATE` | No | - | Expense transaction date (YYYY-MM-DD) |
| `payment_mode` | `VARCHAR(20)` | No | `'cash'` | Choice: `cash`, `debit_card`, `credit_card`, `upi`, `net_banking`, `other` |
| `merchant` | `VARCHAR(255)` | Yes | `''` | Merchant name (used by category auto-suggestion FR9) |
| `notes` | `TEXT` | Yes | `''` | User remarks / notes |
| `receipt` | `VARCHAR(255)` | Yes | `NULL` | File path relative to receipt storage root (outside web root) (D6) |
| `is_deleted` | `BOOLEAN` | No | `False` | Soft deletion flag (D4) |
| `deleted_at` | `TIMESTAMPTZ` | Yes | `NULL` | Timestamp when soft deleted |
| `recurring_rule_id`| `BIGINT` | Yes | `NULL` | FK -> `expenses_recurringrule.id` (ON DELETE SET NULL) if generated by rule (D3) |
| `created_at` | `TIMESTAMPTZ` | No | `CURRENT_TIMESTAMP` | Record creation timestamp |
| `updated_at` | `TIMESTAMPTZ` | No | `CURRENT_TIMESTAMP` | Last updated timestamp |

**Indexes & Performance Optimization (R3, NFR1):**
- Composite Index: `(user_id, date)` — High-speed filtering by date range for 10k transactions.
- Composite Index: `(user_id, category_id)` — High-speed category aggregations.
- Index: `(user_id, is_deleted)` — Excludes soft-deleted transactions efficiently.

---

### 3.4 `expenses_recurringrule` (Django App: `expenses`, Table: `expenses_recurringrule`)
Managed by **Shreya S Mattimadu** (FR6, D3) & **Shashwath K R** (Scheduler).

| Column Name | PostgreSQL Type | Nullable | Default | Constraints / Description |
|---|---|---|---|---|
| `id` | `BIGSERIAL` | No | Auto | Primary Key |
| `user_id` | `BIGINT` | No | - | FK -> `accounts_user.id` (ON DELETE CASCADE) |
| `category_id` | `BIGINT` | No | - | FK -> `categories_category.id` (ON DELETE RESTRICT) |
| `amount` | `DECIMAL(12, 2)` | No | - | Amount for each occurrence (D1) |
| `cadence` | `VARCHAR(20)` | No | `'monthly'` | Frequency: `daily`, `weekly`, `monthly`, `yearly` |
| `start_date` | `DATE` | No | - | Start date of recurrence |
| `end_date` | `DATE` | Yes | `NULL` | Optional end date |
| `next_run_date` | `DATE` | No | - | Next date the scheduler should materialize an `Expense` row |
| `payment_mode` | `VARCHAR(20)` | No | `'other'` | Payment mode |
| `merchant` | `VARCHAR(255)` | Yes | `''` | Merchant name |
| `notes` | `TEXT` | Yes | `''` | Template notes |
| `is_active` | `BOOLEAN` | No | `True` | Active status toggle |
| `created_at` | `TIMESTAMPTZ` | No | `CURRENT_TIMESTAMP` | Creation timestamp |

---

### 3.5 `budgets_budget` (Django App: `budgets`, Table: `budgets_budget`)
Managed by **Shashwath K R** (FR10, FR11, FR12, D2).

| Column Name | PostgreSQL Type | Nullable | Default | Constraints / Description |
|---|---|---|---|---|
| `id` | `BIGSERIAL` | No | Auto | Primary Key |
| `user_id` | `BIGINT` | No | - | FK -> `accounts_user.id` (ON DELETE CASCADE) |
| `category_id` | `BIGINT` | Yes | `NULL` | FK -> `categories_category.id` (ON DELETE CASCADE). `NULL` = Overall total budget |
| `limit_amount` | `DECIMAL(12, 2)` | No | - | Spending limit; CHECK (`limit_amount > 0`) (D1) |
| `period` | `VARCHAR(20)` | No | `'monthly'` | Period type: `weekly`, `monthly` |
| `start_date` | `DATE` | No | - | Explicit period start date (D2) |
| `end_date` | `DATE` | No | - | Explicit period end date (D2) |
| `rollover_enabled`| `BOOLEAN` | No | `False` | FR12: Whether unspent balance rolls over to next period |
| `created_at` | `TIMESTAMPTZ` | No | `CURRENT_TIMESTAMP` | Creation timestamp |
| `updated_at` | `TIMESTAMPTZ` | No | `CURRENT_TIMESTAMP` | Last updated timestamp |

**Constraints:**
- CHECK (`start_date <= end_date`)
- Composite Index: `(user_id, start_date, end_date)`
- Unique Constraint: `UNIQUE (user_id, category_id, start_date, end_date)` to prevent duplicate budgets for the same category and period.

---

### 3.6 `alerts_alert` (Django App: `alerts`, Table: `alerts_alert`)
Managed by **Shashwath K R** (FR16, FR17, FR18, D5).

| Column Name | PostgreSQL Type | Nullable | Default | Constraints / Description |
|---|---|---|---|---|
| `id` | `BIGSERIAL` | No | Auto | Primary Key |
| `user_id` | `BIGINT` | No | - | FK -> `accounts_user.id` (ON DELETE CASCADE) |
| `budget_id` | `BIGINT` | Yes | `NULL` | FK -> `budgets_budget.id` (ON DELETE CASCADE) |
| `threshold_percentage`| `INTEGER` | Yes | `NULL` | Threshold reached: 80 or 100 (FR16) |
| `period_start` | `DATE` | Yes | `NULL` | Period start date for the budget |
| `alert_type` | `VARCHAR(20)` | No | `'threshold'`| Type: `threshold` (FR16), `anomaly` (FR17) |
| `title` | `VARCHAR(255)` | No | - | Alert title (e.g., 'Budget reached 80%') |
| `message` | `TEXT` | No | - | Notification body text |
| `is_read` | `BOOLEAN` | No | `False` | In-app read status |
| `email_sent` | `BOOLEAN` | No | `False` | FR18: Delivery status via email adapter |
| `created_at` | `TIMESTAMPTZ` | No | `CURRENT_TIMESTAMP` | Alert timestamp |

**Indexes & Constraints (D5, R2):**
- Unique Constraint: `UNIQUE (budget_id, threshold_percentage, period_start)` prevents duplicate alerts when transactions update or are recalculated.
- Index: `(user_id, is_read, created_at)` for fast unread count queries on the dashboard.

---

### 3.7 `audit_auditlog` (Django App: `audit`, Table: `audit_auditlog`)
Implemented by **Shriram Chandrasekar** (FR21).

| Column Name | PostgreSQL Type | Nullable | Default | Constraints / Description |
|---|---|---|---|---|
| `id` | `BIGSERIAL` | No | Auto | Primary Key |
| `actor_id` | `BIGINT` | Yes | `NULL` | FK -> `accounts_user.id` (ON DELETE SET NULL) |
| `action` | `VARCHAR(10)` | No | - | Choice: `create`, `update`, `delete` |
| `entity_type` | `VARCHAR(100)` | No | - | Model label (e.g. `'expenses.expense'`, `'budgets.budget'`) |
| `entity_id` | `VARCHAR(64)` | No | - | Primary key of entity as string |
| `before` | `JSONB` | Yes | `NULL` | Snapshot of fields before change (exact decimals encoded as strings) |
| `after` | `JSONB` | Yes | `NULL` | Snapshot of fields after change |
| `request_id` | `VARCHAR(64)` | Yes | `''` | Request trace ID (NFR12) |
| `created_at` | `TIMESTAMPTZ` | No | `CURRENT_TIMESTAMP` | Immutable timestamp |

---

## 4. Migration & App Dependency Sequence

1. `accounts` (Base User) — *Already implemented*
2. `audit` (Audit Logging) — *Already implemented*
3. `categories` (Category Model & initial migration)
4. `expenses` (Expense Model & RecurringRule Model referencing User and Category)
5. `budgets` (Budget Model referencing User and Category)
6. `alerts` (Alert Model referencing User and Budget)

This guarantees foreign keys resolve cleanly and without circular migration dependencies.
