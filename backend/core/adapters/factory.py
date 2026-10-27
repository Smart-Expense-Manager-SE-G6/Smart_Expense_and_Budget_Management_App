
import os

from core.adapters.email import DjangoEmailAdapter, StubEmailAdapter
from core.adapters.charting import StubChartingAdapter


def get_email_adapter():
    """Use the stub unless real email is explicitly enabled."""
    if os.getenv("ENABLE_REAL_EMAIL", "false").lower() == "true":
        return DjangoEmailAdapter()

    return StubEmailAdapter()


def get_charting_adapter():
    """Return the charting adapter."""
    return StubChartingAdapter()
