
from core.adapters.factory import get_email_adapter


def send_alert_email(alert):
    """Deliver an alert email through the configured email adapter."""
    email_adapter = get_email_adapter()

    return email_adapter.send_email(
        recipient=alert.user.email,
        subject=alert.title,
        message=alert.message,
    )
