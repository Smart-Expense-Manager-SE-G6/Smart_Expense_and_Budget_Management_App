# Smart Expense and Budget Management — User Guide

## Getting started

1. Start the stack with `docker compose up --build` or follow [`docs/operations/deployment.md`](../operations/deployment.md) for the production-like demo.
2. Open the web application and choose **Create account**.
3. Enter first name, last name, email and password. Registration signs the user in and opens the dashboard.

## Dashboard and analytics

The dashboard summarizes current-period spend, average expense, category breakdown, trend, forecast, recent expenses and budget utilization. Use the navigation links to open Expenses, Budgets, Reports, Alerts, Categories and Profile.

## Expenses

Choose **Add expense**, enter the amount and date, and optionally add description, merchant, notes, payment method, category and a receipt. Expenses can be edited or soft-deleted; history is available from the expense action menu. Category suggestions are advisory and can be accepted or overridden.

For bulk entry, open **Import**, upload a CSV matching `frontend/public/expense-import-template.csv`, review the preview errors, then import only the valid rows. Recurring rules are managed under **Recurring** and materialized by the scheduler.

## Budgets, sharing and alerts

Create a weekly or monthly budget with a positive limit and optional category. Choose reset or rollover behavior. Owners can share a budget with another registered email and assign member/admin access. Budget alerts are raised at 80% and 100%; anomaly alerts explain when a new same-category expense is more than three times the average of the previous five.

## Reports and exports

Open **Reports**, select a date range up to 366 days, and choose PDF or Excel export. The API contract and endpoint descriptions are available at `/api/v1/schema/docs/` when the stack is running.

## Account and privacy

Profile settings update name, timezone and alert-email consent. Account settings provide data export and deletion controls. The application uses an HttpOnly server-side session cookie and CSRF protection; never share the session cookie.

## Screenshots

Screenshots must be captured from the running release stack so they reflect the current build. The Docker daemon was unavailable during this documentation pass, so no screenshot is claimed as captured. To complete the release artifact:

```powershell
docker compose up -d --build
# capture the dashboard, expense form/import preview, budgets/sharing, alerts and reports screens
# save them as docs/user/screenshots/dashboard.png, expenses.png, budgets.png, alerts.png, reports.png
docker compose down
```

The screenshot checklist is intentionally explicit rather than embedding images from a different build.
