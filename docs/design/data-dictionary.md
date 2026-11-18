# Physical Schema and Data Dictionary

- **Document version:** 1.1 (release reconciliation)
- **Date:** 2026-11-17
- **Source of truth:** Django models and migrations in `backend/*/models.py` and `backend/*/migrations/`
- **Currency:** `DecimalField(max_digits=12, decimal_places=2)`; values are never stored as floating point.

## Accounts — `accounts_user`

Model: `backend/accounts/models.py` (`User`, custom email login).

| Column | Type | Null/default | Meaning |
|---|---|---|---|
| `id` | bigint | no / auto | Primary key |
| `email` | varchar(254) | no / unique | Normalized lowercase login identifier |
| `password` | varchar(128) | no | Django password hash |
| `first_name`, `last_name` | varchar(150) | no / empty | Profile names |
| `timezone` | varchar(64) | no / `Asia/Kolkata` | Validated IANA timezone |
| `email_alerts` | boolean | no / true | Alert-email consent |
| `is_active`, `is_staff`, `is_superuser` | boolean | no / false | Django account flags |
| `date_joined`, `last_login` | timestamptz | no / nullable | Account/authentication timestamps |

## Expenses

### `expenses_category`

Model: `backend/expenses/models.py` (`Category`). `owner_id = NULL` means global; otherwise the category is user-owned.

| Column | Type | Null/default | Meaning |
|---|---|---|---|
| `id` | bigint | no / auto | Primary key |
| `name` | varchar(100) | no | Category name |
| `owner_id` | bigint FK | yes / null | Owner; cascade delete |
| `parent_id` | bigint FK | yes / null | Optional parent; protected delete |
| `is_active` | boolean | no / true | Whether selectable |
| `created_at`, `updated_at` | timestamptz | no / auto | Audit timestamps |

Case-insensitive uniqueness is enforced globally and per owner; self-parenting and deeper cycles are blocked.

### `expenses_expense`

Model: `backend/expenses/models.py` (`Expense`).

| Column | Type | Null/default | Meaning |
|---|---|---|---|
| `id` | bigint | no / auto | Primary key |
| `owner_id` | bigint FK | no | User who owns the expense |
| `recurring_rule_id` | bigint FK | yes / null | Source rule; set null on deletion |
| `category_id` | bigint FK | yes / null | Category; protected delete |
| `amount` | numeric(12,2) | no | Positive expense amount |
| `description`, `merchant`, `notes` | varchar(255) | no / empty | Transaction details |
| `date` | date | no | Transaction date |
| `payment_method` | varchar(32) | no / empty | Payment method |
| `receipt` | varchar(255) | yes / null | Private receipt path |
| `is_deleted` | boolean | no / false | Soft-delete marker |
| `created_at`, `updated_at` | timestamptz | no / auto | Audit timestamps |

Index: `(owner_id, is_deleted, date)`. Recurring-generated expenses are unique per `(recurring_rule_id, date)`.

### `expenses_recurringrule`

Model: `backend/expenses/models.py` (`RecurringRule`).

| Column | Type | Null/default | Meaning |
|---|---|---|---|
| `id` | bigint | no / auto | Primary key |
| `owner_id`, `category_id` | bigint FK | owner no; category yes | User and optional category |
| `amount` | numeric(12,2) | no | Positive amount template |
| `payment_method`, `merchant`, `notes` | varchar | no / empty | Template details |
| `frequency` | varchar(10) | no | `daily`, `weekly`, `monthly`, or `yearly` |
| `start_date`, `end_date` | date | start no; end yes | Schedule bounds |
| `is_active` | boolean | no / true | Scheduler toggle |
| `created_at`, `updated_at` | timestamptz | no / auto | Audit timestamps |

## Budgets and sharing

### `budgets_budget`

Model: `backend/budgets/models.py` (`Budget`). Columns are `user_id`, optional `category_id`, `name`, `limit_amount`, nullable `base_limit_amount`, `period` (`weekly`/`monthly`), `start_date`, `end_date`, `rollover_mode` (`reset`/`rollover`), `created_at`, and `updated_at`. Constraints require a positive limit, `start_date <= end_date`, and uniqueness of `(user_id, category_id, start_date, end_date)`.

### `budgets_budgetmember`

Model: `backend/budgets/models.py` (`BudgetMember`). Columns are `budget_id`, `user_id`, `role` (`admin`/`member`), `created_at`, and `updated_at`. The owner is implicitly an admin; `(budget_id, user_id)` is unique.

## Alerts and audit

### `alerts_alert`

Model: `backend/alerts/models.py` (`Alert`). Columns are `user_id`, nullable `budget_id` and `expense_id`, nullable `threshold_percentage` and `period_start`, `alert_type` (`threshold`/`anomaly`), `title`, `message`, `is_read`, `email_sent`, `email_error`, and `created_at`. Threshold alerts have a conditional unique constraint on `(budget_id, threshold_percentage, period_start)`.

### `audit_auditlog`

Model: `backend/audit/models.py` (`AuditLog`). Columns are nullable `actor_id`, `action` (`create`/`update`/`delete`), `entity_type`, `entity_id`, nullable JSONB `before` and `after`, nullable `request_id`, and `created_at`.

## Release reconciliation notes

- The application field is `payment_method`, not `payment_mode`.
- Expense soft deletion uses `is_deleted`; there is no `deleted_at` column.
- The application table is `expenses_category`, not `categories_category`.
- `BudgetMember`, `merchant`, `notes`, `RecurringRule`, `base_limit_amount`, `rollover_mode`, and alert email state are part of the final model.
