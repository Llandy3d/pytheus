from dataclasses import dataclass
from typing import Sequence


class MetricCollector:

    def __init__(self, name: str, required_labels: Sequence[str] | None) -> None:
        self.name = name
        self._required_labels = set(required_labels) if required_labels else None
        self._metric = Metric(self)
        self._labeled_metrics: dict[tuple[str, str], Metric] = {}


class Metric:

    def __init__(self, collector: MetricCollector) -> None:
        self._collector = collector


@dataclass
class Sample:
    name: str
    labels: dict[str, str]
    value: float


@dataclass
class Label:
    name: str
    value: str


m = MetricCollector('name', ['bbo'])
