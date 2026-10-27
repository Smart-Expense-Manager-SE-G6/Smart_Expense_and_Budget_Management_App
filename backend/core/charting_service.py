
from core.adapters.factory import get_charting_adapter


def create_spending_chart(title, labels, values):
    """Create spending chart data through the charting adapter."""
    charting_adapter = get_charting_adapter()
    return charting_adapter.create_chart(
        title=title,
        labels=labels,
        values=values,
    )
