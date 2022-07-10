from dataclasses import dataclass
from typing import Sequence


Labels = dict[str, str]


class MetricCollector:

    def __init__(self, name: str, required_labels: Sequence[str] | None = None) -> None:
        self.name = name
        self._required_labels = set(required_labels) if required_labels else None
        # TODO: pass metric class
        self._metric = Metric(self)
        self._labeled_metrics: dict[tuple[str, str], Metric] = {}

        # this will register to the collector


# class or function based creation ?
class Metric:

    def __init__(
        self,
        collector: MetricCollector,
        labels: Labels | None = None,
    ) -> None:
        self._collector = collector
        self._labels = labels
        self._can_observe = False  # depending on labels, etc..


# this could be a class method, but might want to avoid it
def create_metric(name: str, required_labels: Sequence[str] | None = None) -> Metric:
    collector = MetricCollector(name, required_labels)
    return Metric(collector)


@dataclass
class Sample:
    name: str
    labels: dict[str, str]
    value: float


# maybe just go with the typing alias
@dataclass
class Label:
    name: str
    value: str


# m = MetricCollector('name', ['bbo'])
my_metric = create_metric('name', ['bbo'])
