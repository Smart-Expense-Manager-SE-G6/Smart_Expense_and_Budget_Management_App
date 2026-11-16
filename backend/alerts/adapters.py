
import logging

from core.adapters.email import EmailResult
from core.adapters.factory import get_email_adapter


logger = logging.getLogger(__name__)


def send_alert_email(alert):
    """Deliver an alert email through the configured email adapter."""
    try:
        email_adapter = get_email_adapter()
        result = email_adapter.send_email(
            recipient=alert.user.email,
            subject=alert.title,
            message=alert.message,
        )
    except Exception as error:
        logger.exception("Alert email delivery failed for alert %s", alert.pk)
        alert.email_sent = False
        alert.email_error = str(error) or error.__class__.__name__
        alert.save(update_fields=["email_sent", "email_error"])
        return EmailResult(success=False, message=alert.email_error)

    alert.email_sent = result.success
    alert.email_error = "" if result.success else result.message
    alert.save(update_fields=["email_sent", "email_error"])
    if not result.success:
        logger.error("Alert email delivery failed for alert %s: %s", alert.pk, result.message)
    return result
