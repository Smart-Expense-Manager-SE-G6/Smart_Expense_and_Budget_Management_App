
from typing import Any, Protocol


class ChartingAdapter(Protocol):
    """Interface for generating chart data."""

    def create_chart(
        self,
        title: str,
        labels: list[str],
        values: list[float],
    ) -> dict[str, Any]:
        ...


class StubChartingAdapter:
    """Safe charting implementation for development and testing."""

    def create_chart(
        self,
        title: str,
        labels: list[str],
        values: list[float],
    ) -> dict[str, Any]:
        if len(labels) != len(values):
            raise ValueError("Labels and values must have equal lengths.")

        return {
            "title": title,
            "labels": labels,
            "values": values,
            "type": "bar",
        }
