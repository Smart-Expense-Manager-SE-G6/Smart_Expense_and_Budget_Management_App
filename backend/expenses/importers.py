import csv
import io
from datetime import datetime
from decimal import Decimal, InvalidOperation

from django.db import transaction

from audit.models import AuditLog
from audit.services import log_change
from .models import Category, Expense

MAX_BYTES = 5 * 1024 * 1024
MAX_ROWS = 1000
REQUIRED = {"date", "amount"}


def import_expenses(upload, user, dry_run=False):
    if upload.size > MAX_BYTES:
        raise ValueError("file_too_large:File must not exceed 5 MB.")
    try:
        text = upload.read().decode("utf-8-sig")
    except UnicodeDecodeError:
        raise ValueError("invalid_file:File must be UTF-8 CSV.")
    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        raise ValueError("invalid_file:CSV must contain a header row.")
    reader.fieldnames = [h.strip().lower() for h in reader.fieldnames]
    if not REQUIRED.issubset(reader.fieldnames):
        raise ValueError("missing_columns:CSV must contain date and amount columns.")
    rows = list(reader)
    if len(rows) > MAX_ROWS:
        raise ValueError("too_many_rows:CSV cannot contain more than 1,000 data rows.")
    categories = {c.name.lower(): c for c in Category.objects.filter(is_active=True).filter(owner__isnull=True) | Category.objects.filter(is_active=True, owner=user)}
    errors, valid = [], []
    for number, row in enumerate(rows, 2):
        def error(field, code, message):
            errors.append({"row_number": number, "field": field, "error_code": code, "message": message})
        raw_date = (row.get("date") or "").strip()
        parsed_date = None
        if not raw_date:
            error("date", "MISSING_FIELD", "Date is required.")
        for fmt in ("%Y-%m-%d", "%d/%m/%Y"):
            try:
                parsed_date = datetime.strptime(raw_date, fmt).date(); break
            except ValueError:
                pass
        if parsed_date is None: error("date", "INVALID_DATE", "Date must use YYYY-MM-DD or DD/MM/YYYY.")
        raw_amount = (row.get("amount") or "").strip()
        if not raw_amount:
            error("amount", "MISSING_FIELD", "Amount is required.")
        try:
            if "," in raw_amount: raise InvalidOperation
            amount = Decimal(raw_amount)
            if amount <= 0 or amount.as_tuple().exponent < -2: raise InvalidOperation
        except (InvalidOperation, ValueError):
            amount = None; error("amount", "INVALID_AMOUNT", "Amount must be a positive decimal with at most two decimal places.")
        for field in ("merchant", "notes"):
            if len((row.get(field) or "").strip()) > 255: error(field, "FIELD_TOO_LONG", f"{field} must not exceed 255 characters.")
        payment = (row.get("payment_mode") or "other").strip().lower() or "other"
        if len(payment) > 32: error("payment_mode", "INVALID_PAYMENT_MODE", "Payment mode is invalid.")
        category = categories.get((row.get("category") or "").strip().lower()) if row.get("category") else None
        if row.get("category") and category is None: error("category", "INVALID_CATEGORY", "Category is invalid or inaccessible.")
        if not any(e["row_number"] == number for e in errors):
            valid.append((parsed_date, amount, category, payment, row))
    if not dry_run:
        with transaction.atomic():
            for parsed_date, amount, category, payment, row in valid:
                expense = Expense.objects.create(owner=user, date=parsed_date, amount=amount, category=category, payment_method=payment, merchant=(row.get("merchant") or "").strip(), notes=(row.get("notes") or "").strip(), description=(row.get("notes") or "").strip())
                log_change(user, AuditLog.Action.CREATE, expense)
    rejected_rows = {error["row_number"] for error in errors}
    return {"total_rows": len(rows), "accepted_count": len(valid), "rejected_count": len(rejected_rows), "errors": errors}
