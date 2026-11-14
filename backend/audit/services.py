"""
Audit write helpers (FR21). Every business write must be atomic with its
audit entry: either both are saved or neither is.

Usage in a view or service:

    from audit.services import audited

    with audited(request.user, expense):
        expense.amount = new_amount
        expense.save()

New object (no primary key yet) -> logged as "create".
Existing object -> logged as "update" (soft delete is an update too, per D4).
Hard delete -> pass action=AuditLog.Action.DELETE and delete inside the block.

DRF ViewSets can use AuditedModelViewSetMixin from audit.mixins instead.
"""

from contextlib import contextmanager

from django.db import connection, models, transaction

from core.request_id import get_request_id

from .models import AuditLog

# Never written to the audit trail.
EXCLUDED_FIELDS = {"password"}


def snapshot(instance):
    """Current field values of a model instance, keyed by column attribute name."""
    values = {}
    for field in instance._meta.concrete_fields:
        if field.attname in EXCLUDED_FIELDS:
            continue
        value = getattr(instance, field.attname)
        if isinstance(field, models.FileField):
            value = value.name if value else None
        values[field.attname] = value
    return values


def log_change(actor, action, instance, before=None, entity_id=None):
    """
    Write one audit row. Must run inside the transaction that made the change;
    use audited() rather than calling this directly where possible.
    """
    if not connection.in_atomic_block:
        raise RuntimeError("log_change() must be called inside transaction.atomic()")
    return AuditLog.objects.create(
        actor=actor if actor is not None and actor.is_authenticated else None,
        action=action,
        entity_type=instance._meta.label_lower,
        entity_id=str(entity_id if entity_id is not None else instance.pk),
        before=before,
        after=None if action == AuditLog.Action.DELETE else snapshot(instance),
        request_id=get_request_id(),
    )


@contextmanager
def audited(actor, instance, action=None):
    """Run a change to `instance` and its audit entry in one transaction."""
    with transaction.atomic():
        is_new = instance.pk is None
        before = None if is_new else snapshot(instance)
        entity_id = instance.pk
        yield instance
        if action is None:
            action = AuditLog.Action.CREATE if is_new else AuditLog.Action.UPDATE
        # After a hard delete Django clears instance.pk, so keep the original id.
        log_change(actor, action, instance, before, entity_id=instance.pk or entity_id)
