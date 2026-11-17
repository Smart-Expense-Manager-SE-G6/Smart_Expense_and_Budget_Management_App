import logging

from django.conf import settings
from django.db import connection
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response

from .metrics import get_metrics
from .models import EmailDeliveryFailure
from .status_files import read_job_status

logger = logging.getLogger("monitoring.dashboard")


@api_view(["GET"])
@permission_classes([IsAdminUser])
def dashboard(request):
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        database_status = "healthy"
    except Exception:
        database_status = "unhealthy"
        logger.exception("Database health check failed")

    failures = (
        EmailDeliveryFailure.objects.order_by("-created_at")[:10]
        if database_status == "healthy"
        else []
    )
    return Response(
        {
            "checked_at": timezone.now().isoformat(),
            "backend": {"status": "healthy"},
            "database": {"status": database_status},
            "budget_scheduler": read_job_status(
                "budget-scheduler",
                settings.MONITORING_SCHEDULER_MAX_AGE_SECONDS,
            ),
            "backup": read_job_status(
                "backup",
                settings.MONITORING_BACKUP_MAX_AGE_SECONDS,
            ),
            "email": {
                "latest_failures": [
                    {
                        "created_at": failure.created_at.isoformat(),
                        "recipient": failure.recipient,
                        "subject": failure.subject,
                        "reason": failure.reason,
                        "request_id": failure.request_id,
                    }
                    for failure in failures
                ]
            },
            "errors": get_metrics(),
        }
    )
