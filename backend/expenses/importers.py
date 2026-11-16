"""CSV expense import (FR7). File format, limits and error shape follow ADR-0003."""

import csv
import io
from datetime import datetime
from decimal import Decimal, InvalidOperation

from django.db import transaction
from django.db.models import Q

from audit.models import AuditLog
from audit.services import log_change
from .models import Category, Expense

MAX_BYTES = 5 * 1024 * 1024
MAX_ROWS = 1000
REQUIRED = {"date", "amount"}
DATE_FORMATS = ("%Y-%m-%d", "%d/%m/%Y")
PAYMENT_MODES = {"cash", "debit_card", "credit_card", "upi", "net_banking", "other"}
MAX_AMOUNT = Decimal("9999999999.99")  # Expense.amount is max_digits=12, decimal_places=2
TEXT_LIMIT = 255


class ImportFileError(Exception):
    """The file as a whole cannot be imported. No rows are read or saved."""

    def __init__(self, code, message):
        super().__init__(message)
        self.code = code
        self.message = message


def _parse_date(raw):
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(raw, fmt).date()
        except ValueError:
            pass
    return None


def _parse_amount(raw):
    """A positive amount with at most two decimal places, written as plain digits."""
    if not raw or not all(ch.isdigit() or ch == "." for ch in raw):
        return None  # rejects signs, commas, exponents, NaN and Infinity
    try:
        amount = Decimal(raw)
    except InvalidOperation:
        return None
    if amount <= 0 or amount > MAX_AMOUNT or amount.as_tuple().exponent < -2:
        return None
    return amount


def _read_rows(upload):
    if upload.size > MAX_BYTES:
        raise ImportFileError("FILE_TOO_LARGE", "File must not exceed 5 MB.")
    try:
        text = upload.read().decode("utf-8-sig")
    except UnicodeDecodeError:
        raise ImportFileError("INVALID_FILE", "File must be a UTF-8 encoded CSV.")
    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        raise ImportFileError("INVALID_FILE", "CSV must contain a header row.")
    reader.fieldnames = [(h or "").strip().lower() for h in reader.fieldnames]
    if not REQUIRED.issubset(reader.fieldnames):
        raise ImportFileError("MISSING_COLUMNS", "CSV must contain date and amount columns.")
    rows = list(reader)
    if len(rows) > MAX_ROWS:
        raise ImportFileError("TOO_MANY_ROWS", f"CSV cannot contain more than {MAX_ROWS:,} data rows.")
    return rows


def import_expenses(upload, user, dry_run=False):
    """
    Validate every row and save the valid ones in one transaction.

    Row numbers are the line numbers in the file, so the header is line 1 and
    the first data row is line 2. A bad row never stops the good rows.
    """
    rows = _read_rows(upload)
    visible = Category.objects.filter(Q(owner__isnull=True) | Q(owner=user), is_active=True)
    # A user's own category wins over a default category with the same name.
    categories = {c.name.lower(): c for c in visible.order_by("-owner_id")}

    errors, valid = [], []
    for number, row in enumerate(rows, start=2):
        value = {key: (row.get(key) or "").strip() for key in ("date", "amount", "category", "payment_mode", "merchant", "notes")}
        row_errors = []

        def error(field, code, message):
            row_errors.append({"row_number": number, "field": field, "error_code": code,
                               "message": message, "raw_value": value[field]})

        # PostgreSQL cannot store NUL bytes; without this check one such cell
        # would crash the whole import (found by the S3-15 fuzz tests).
        for field, cell in value.items():
            if "\x00" in cell:
                error(field, "INVALID_CHARACTER", "Remove the NUL (0x00) character from this cell.")
                value[field] = cell.replace("\x00", "")

        parsed_date = None
        if not value["date"]:
            error("date", "MISSING_FIELD", "Date is required.")
        else:
            parsed_date = _parse_date(value["date"])
            if parsed_date is None:
                error("date", "INVALID_DATE", "Date must use YYYY-MM-DD or DD/MM/YYYY.")

        amount = None
        if not value["amount"]:
            error("amount", "MISSING_FIELD", "Amount is required.")
        else:
            amount = _parse_amount(value["amount"])
            if amount is None:
                error("amount", "INVALID_AMOUNT",
                      "Amount must be a positive number with at most two decimal places, up to 9,999,999,999.99.")

        payment = value["payment_mode"].lower() or "other"
        if payment not in PAYMENT_MODES:
            error("payment_mode", "INVALID_PAYMENT_MODE",
                  "Payment mode must be one of: " + ", ".join(sorted(PAYMENT_MODES)) + ".")

        for field in ("merchant", "notes"):
            if len(value[field]) > TEXT_LIMIT:
                error(field, "FIELD_TOO_LONG", f"{field.capitalize()} must not exceed {TEXT_LIMIT} characters.")

        # ADR-0003: an unknown category does not reject the row; it is imported uncategorised.
        category = categories.get(value["category"].lower()) if value["category"] else None

        if row_errors:
            errors.extend(row_errors)
        else:
            valid.append((parsed_date, amount, category, payment, value))

    if not dry_run:
        with transaction.atomic():
            for parsed_date, amount, category, payment, value in valid:
                expense = Expense.objects.create(
                    owner=user, date=parsed_date, amount=amount, category=category, payment_method=payment,
                    merchant=value["merchant"], notes=value["notes"], description=value["merchant"] or value["notes"],
                )
                log_change(user, AuditLog.Action.CREATE, expense)

    return {
        "total_rows": len(rows),
        "accepted_count": len(valid),
        "rejected_count": len({e["row_number"] for e in errors}),
        "dry_run": dry_run,
        "errors": errors,
    }
