
from dataclasses import dataclass
from typing import Protocol

from django.conf import settings
from django.core.mail import send_mail


@dataclass
class EmailResult:
    success: bool
    message: str


class EmailAdapter(Protocol):
    """Interface for sending email notifications."""

    def send_email(
        self,
        recipient: str,
        subject: str,
        message: str,
    ) -> EmailResult:
        ...


class StubEmailAdapter:
    """Safe implementation that never sends real email."""

    def send_email(
        self,
        recipient: str,
        subject: str,
        message: str,
    ) -> EmailResult:
        return EmailResult(
            success=True,
            message="Email accepted by the stub; nothing was sent.",
        )


class DjangoEmailAdapter:
    """Email implementation using Django's configured email backend."""

    def send_email(
        self,
        recipient: str,
        subject: str,
        message: str,
    ) -> EmailResult:
        if not recipient.strip():
            return EmailResult(False, "Recipient email is required.")

        try:
            sent = send_mail(
                subject=subject,
                message=message,
                from_email=getattr(settings, "DEFAULT_FROM_EMAIL", None),
                recipient_list=[recipient],
                fail_silently=False,
            )
        except Exception:
            return EmailResult(False, "Email delivery failed.")

        if sent == 1:
            return EmailResult(True, "Email sent successfully.")

        return EmailResult(False, "Email was not sent.")
