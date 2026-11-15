"""
The user's control over their own data (FR2 "manage account settings", NFR14).

- export_zip(user): everything the app stores about the user, as one ZIP.
- delete_account(user): remove the user and everything they own.
"""

import csv
import io
import json
import zipfile

from django.core.serializers.json import DjangoJSONEncoder
from django.db import transaction
from django.utils import timezone

from alerts.models import Alert
from audit.models import AuditLog
from audit.views import AuditEntrySerializer, visible_to
from budgets.models import Budget, BudgetMember
from core.request_id import get_request_id
from expenses.models import Category, Expense, RecurringRule

from .serializers import UserSerializer

EXPENSE_COLUMNS = [
    "id", "date", "amount", "category", "payment_method", "merchant", "notes", "description",
    "recurring_rule_id", "has_receipt", "is_deleted", "created_at", "updated_at",
]

README = """Smart Expense: your data export
Created {created} for {email}.

profile.json          your profile and settings
expenses.csv          every expense, including deleted ones (is_deleted = True)
categories.json       categories you created
recurring_rules.json  your recurring expense rules
budgets.json          budgets you own, and budgets shared with you (with your role)
alerts.json           every alert you have received
history.json          the audit trail of changes to your records
receipts/             the receipt files you uploaded, named <expense id>_<file name>
"""


def _json(data):
    return json.dumps(data, cls=DjangoJSONEncoder, indent=2, ensure_ascii=False)


def _rows(queryset, fields):
    return [{field: getattr(obj, field) for field in fields} for obj in queryset]


def _expenses_csv(user):
    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow(EXPENSE_COLUMNS)
    for e in Expense.objects.filter(owner=user).select_related("category").order_by("date", "id"):
        writer.writerow([
            e.id, e.date.isoformat(), str(e.amount), e.category.name if e.category else "", e.payment_method,
            e.merchant, e.notes, e.description, e.recurring_rule_id or "", bool(e.receipt), e.is_deleted,
            e.created_at.isoformat(), e.updated_at.isoformat(),
        ])
    return out.getvalue()


def _budgets(user):
    owned = _rows(Budget.objects.filter(user=user).select_related("category").order_by("start_date", "id"),
                  ["id", "name", "category_id", "limit_amount", "base_limit_amount", "period", "start_date",
                   "end_date", "rollover_mode", "created_at"])
    for budget in owned:
        budget["role"] = "owner"
        budget["members"] = list(
            BudgetMember.objects.filter(budget_id=budget["id"]).values("user__email", "role", "created_at")
        )
    shared = [
        {"id": m.budget_id, "name": m.budget.name, "owner_email": m.budget.user.email, "role": m.role,
         "joined": m.created_at}
        for m in BudgetMember.objects.filter(user=user).select_related("budget__user")
    ]
    return {"owned": owned, "shared_with_me": shared}


def export_zip(user):
    """Return (filename, bytes) of a ZIP with all of the user's data."""
    buffer = io.BytesIO()
    created = timezone.now()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("README.txt", README.format(created=created.isoformat(timespec="seconds"), email=user.email))
        archive.writestr("profile.json", _json(UserSerializer(user).data))
        archive.writestr("expenses.csv", _expenses_csv(user))
        archive.writestr("categories.json", _json(_rows(
            Category.objects.filter(owner=user).order_by("id"), ["id", "name", "parent_id", "is_active", "created_at"])))
        archive.writestr("recurring_rules.json", _json(_rows(
            RecurringRule.objects.filter(owner=user).order_by("id"),
            ["id", "amount", "category_id", "payment_method", "merchant", "notes", "frequency", "start_date",
             "end_date", "is_active", "created_at"])))
        archive.writestr("budgets.json", _json(_budgets(user)))
        archive.writestr("alerts.json", _json(_rows(
            Alert.objects.filter(user=user).order_by("created_at"),
            ["id", "alert_type", "budget_id", "threshold_percentage", "title", "message", "is_read", "created_at"])))
        history = AuditLog.objects.filter(visible_to(user)).select_related("actor").order_by("created_at", "id")
        archive.writestr("history.json", _json(AuditEntrySerializer(history, many=True).data))
        for expense in Expense.objects.filter(owner=user).exclude(receipt="").exclude(receipt__isnull=True):
            try:
                with expense.receipt.open("rb") as handle:
                    name = expense.receipt.name.rsplit("/", 1)[-1]
                    archive.writestr(f"receipts/{expense.id}_{name}", handle.read())
            except FileNotFoundError:
                continue  # the row points at a file that is gone; nothing to export
    filename = f"smart-expense-data-{created:%Y%m%d}.zip"
    return filename, buffer.getvalue()


def delete_account(user):
    """
    Delete the user and everything they own, in one transaction.

    Cascades remove their expenses, categories, recurring rules, budgets (with
    those budgets' memberships), memberships in other people's budgets and
    alerts. Their own audit history goes too, since the records it describes
    no longer exist; one anonymous entry records that an account was deleted.
    Receipt files are removed from storage after the transaction commits.
    """
    receipts = [
        expense.receipt.name for expense in Expense.objects.filter(owner=user).exclude(receipt="").exclude(receipt__isnull=True)
    ]
    storage = Expense._meta.get_field("receipt").storage
    user_id = user.pk
    with transaction.atomic():
        AuditLog.objects.filter(visible_to(user)).delete()
        user.delete()
        AuditLog.objects.create(
            actor=None, action=AuditLog.Action.DELETE, entity_type="accounts.user", entity_id=str(user_id),
            before=None, after=None, request_id=get_request_id(),
        )

        def remove_files():
            for name in receipts:
                storage.delete(name)

        transaction.on_commit(remove_files)
