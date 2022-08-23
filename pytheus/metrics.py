import re
from collections.abc import Generator
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Sequence, Iterator

from pytheus.backends import get_backend
from pytheus.exceptions import UnobservableMetricException
from pytheus.registry import REGISTRY, Registry


Labels = dict[str, str]


metric_name_re = re.compile(r'[a-zA-Z_:][a-zA-Z0-9_:]*')
label_name_re = re.compile(r'[a-zA-Z_][a-zA-Z0-9_]*')


@dataclass
class Sample:
    suffix: str
    labels: dict[str, str] | None
    value: float


class _MetricCollector:
    """
    #TODO

    _labeled_metrics contains all observable metrics when required_labels is set.
    """

    def __init__(
        self,
        name: str,
        description: str,
        metric_class: type['Metric'],
        required_labels: Sequence[str] | None = None,
        registry: Registry = REGISTRY
    ) -> None:
        if metric_name_re.fullmatch(name) is None:
            raise ValueError(f'Invalid metric name: {name}')

        if required_labels:
            self._validate_labels(required_labels)

        self.name = name
        self.description = description
        self._required_labels = set(required_labels) if required_labels else None
        self._metric = metric_class(self)
        self._labeled_metrics: dict[tuple[str, ...], Metric] = {}
        registry.register(self)

        # this will register to the collector

    @property
    def type_(self) -> str:
        # TODO check maybe a proper MetricTypes should to be defined
        return str.lower(self._metric.__class__.__name__)

    def _validate_labels(self, labels: Sequence[str]):
        """
        Validates label names according to the regex.
        Labels starting with `__` are reserved for internal use by Prometheus.
        """
        for label in labels:
            if label.startswith('__') or label_name_re.fullmatch(label) is None:
                raise ValueError(f'Invalid label name: {label}')

    def collect(self) -> Sequence[Sample] | Iterator[Sample]:
        """
        Collects Samples for the metric.
        If there are no required labels, will return a sequence with a single Sample.
        If there are required labels, it will return an Iterator of all the Samples.
        """
        if self._required_labels:
            labeled_metrics = (metric.collect() for metric in self._labeled_metrics.values())
            return labeled_metrics
        else:
            return (self._metric.collect(),)


# class or function based creation ?
class Metric:
    def __init__(
        self,
        collector: _MetricCollector,
        labels: Labels | None = None,
    ) -> None:
        self._collector = collector
        self._labels = labels
        self._can_observe = self._check_can_observe()
        self._metric_value_backend = None

        if self._can_observe:
            self._metric_value_backend = get_backend(self)

    def _check_can_observe(self) -> bool:
        if not self._collector._required_labels:
            return True

        if not self._labels:
            return False

        # TODO: labels will need better validation checks
        if len(self._labels) != len(self._collector._required_labels):
            # TODO: custom exceptions required
            return False

        return True

    def _raise_if_cannot_observe(self) -> None:
        """Raise if the metric cannot be observed, for example if labels values are missing."""
        if not self._can_observe:
            raise UnobservableMetricException

    # TODO: also consider adding default labels directly on the collector as well
    def labels(self, _labels: Labels) -> 'Metric':
        if not _labels or self._collector._required_labels is None:
            return self

        # TODO: when testing rewrite in a better way
        if self._labels:
            new_labels = self._labels.copy()
            new_labels.update(_labels)
            _labels = new_labels

        # TODO: add labels validation
        if len(_labels) != len(self._collector._required_labels):
            # does not add to collector
            return self.__class__(self._collector, _labels)

        # add to collector
        sorted_label_values = tuple(v for _, v in sorted(_labels.items()))
        if sorted_label_values in self._collector._labeled_metrics:
            metric = self._collector._labeled_metrics[sorted_label_values]
        else:
            metric = self.__class__(self._collector, _labels)
            self._collector._labeled_metrics[sorted_label_values] = metric
        return metric

    def collect(self) -> Sample:
        raise NotImplementedError

    def __repr__(self) -> str:
        return f'{self.__class__.__qualname__}({self._collector.name})'


class Counter(Metric):

    def inc(self, value: float = 1.0) -> None:
        """
        Increments the value by the given amount.
        By default it will be 1.
        value must be >= 0.
        """
        self._raise_if_cannot_observe()
        if value < 0:
            raise ValueError(f'Counter increase value ({value}) must be >= 0')

        self._metric_value_backend.inc(value)

    # TODO: consider adding decorator support
    @contextmanager
    def count_exceptions(
        self,
        exceptions: type[Exception] | tuple[Exception] | None = None
    ) -> Generator[None, None, None]:
        """
        Will count and reraise raised exceptions.
        It is possibly to specify which exceptions to track.
        """
        self._raise_if_cannot_observe()
        if exceptions is None:
            exceptions = Exception

        try:
            yield
        except exceptions:
            self.inc()
            raise

    def collect(self) -> Sample:
        self._raise_if_cannot_observe()
        # TODO: probably need a way to add default metric creation labels
        # ideally on Metric class initialization
        # while being careful of not messing up the tracking logic
        return Sample('_total', self._labels, self._metric_value_backend.get())


# this could be a class method, but might want to avoid it
def create_metric(name: str, description: str, required_labels: Sequence[str] | None = None) -> Metric:
    collector = _MetricCollector(name, description, Metric, required_labels)
    return Metric(collector)


def create_counter(name: str, description: str, required_labels: Sequence[str] | None = None) -> Counter:
    collector = _MetricCollector(name, description, Counter, required_labels)
    return collector._metric


# maybe just go with the typing alias
@dataclass
class Label:
    name: str
    value: str
