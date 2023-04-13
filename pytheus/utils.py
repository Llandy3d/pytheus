from enum import Enum


class MetricType(str, Enum):
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    SUMMARY = "summary"
    UNTYPED = "untyped"

    def __str__(self) -> str:
        return self.value


class InfFloat(float):
    """
    Overrides the float __str__ to return +Inf to align with the go/rust clients.
    This is expected to be used only as the upper bound in an Histogram bucket.
    """

    def __str__(self) -> str:
        """Avoiding checks as this is supposed to represent only float('inf')."""
        return "+Inf"
