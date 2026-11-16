import logging

from core.request_id import get_request_id
from .models import EmailDeliveryFailure

logger = logging.getLogger("monitoring.email")


def _mask_recipient(recipient):
    local, separator, domain = (recipient or "").partition("@")
    if not separator:
        return ""
    return f"{local[:1]}***@{domain}"


def record_email_failure(recipient, subject, reason, request_id=None):
    """Persist a minimal, privacy-conscious record of a failed delivery."""
    masked_recipient = _mask_recipient(recipient)
    safe_subject = (subject or "")[:255]
    safe_reason = reason[:255]
    logger.error(
        "Email delivery failed",
        extra={
            "failure_reason": safe_reason,
            "email_subject": safe_subject,
        },
    )
    try:
        failure = EmailDeliveryFailure.objects.create(
            recipient=masked_recipient,
            subject=safe_subject,
            reason=safe_reason,
            request_id=request_id if request_id is not None else get_request_id(),
        )
    except Exception:
        logger.exception("Could not persist email delivery failure")
        return None
    return failure
