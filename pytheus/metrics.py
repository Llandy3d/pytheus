import re
from collections.abc import Generator
from contextlib import contextmanager
from dataclasses import dataclass
import os
from typing import Optional, Sequence, Iterator

from pytheus.backends import (Backend, BackendConfig)
from pytheus.exceptions import PytheusException


class UnobservableMetricException(PytheusException):
    pass


Labels = dict[str, str]


metric_name_re = re.compile(r'[a-zA-Z_:][a-zA-Z0-9_:]*')
label_name_re = re.compile(r'[a-zA-Z_][a-zA-Z0-9_]*')


@dataclass
class Sample:
    suffix: str
    labels: dict[str, str] | None
    value: float


class MetricCollector:
    """
    #TODO

    _labeled_metrics contains all observable metrics when required_labels is set.
    """

    def __init__(
        self,
        name: str,
        metric_class: type['Metric'],
        required_labels: Sequence[str] | None = None,
    ) -> None:
        if metric_name_re.fullmatch(name) is None:
            raise ValueError(f'Invalid metric name: {name}')

        if required_labels:
            self._validate_labels(required_labels)

        self.name = name
        self._required_labels = set(required_labels) if required_labels else None
        self._metric = metric_class(self)
        self._labeled_metrics: dict[tuple[str, ...], Metric] = {}

        # this will register to the collector

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
        collector: MetricCollector,
        labels: Labels | None = None,
        backend_class: Optional[Backend] = None,
        backend_config: Optional[BackendConfig] = None,
    ) -> None:
        self._collector = collector
        self._labels = labels
        self._can_observe = self._check_can_observe()
        if backend_class is not None and backend_config is not None:
            self._metric_value_backend = backend_class(backend_config)
        else:
            from pytheus.backends import DEFAULT_BACKEND_CLASS, DEFAULT_BACKEND_CONFIG
            self._metric_value_backend = DEFAULT_BACKEND_CLASS(DEFAULT_BACKEND_CONFIG)

    def _check_can_observe(self) -> bool:
        if not self._collector._required_labels:
            return True

        if not self._labels:
            return False

        # TODO: labels will need better validation checks
        if len(self._labels) != len(self._collector._required_labels):
            # TODO: custom exceptions required
            return False

        # TODO: allow partial labels
        return True

    def _raise_if_cannot_observe(self) -> None:
        """Raise if the metric cannot be observed, for example if labels values are missing."""
        if not self._can_observe:
            raise UnobservableMetricException

    # TODO: calling labels again should keep previous labels by default
    # allowing for partial labels
    # TODO: also consider adding default labels directly on the collector as well
    def labels(self, _labels: Labels) -> 'Metric':
        if not _labels or self._collector._required_labels is None:
            return self

        add_to_collector: bool = True

        # TODO: add labels validation
        if len(_labels) != len(self._collector._required_labels):
            add_to_collector = False

        sorted_label_values = tuple(v for _, v in sorted(_labels.items()))
        # get or add to collector
        if add_to_collector:
            if sorted_label_values in self._collector._labeled_metrics:
                metric = self._collector._labeled_metrics[sorted_label_values]
            else:
                metric = self.__class__(self._collector, _labels)
                self._collector._labeled_metrics[sorted_label_values] = metric
        else:
            metric = self.__class__(self._collector, _labels)

        return metric

    def collect(self) -> Sample:
        raise NotImplementedError

    def __repr__(self) -> str:
        return f'{self.__class__.__qualname__}({self._collector.name})'


# TODO: count exception raised
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
        if exceptions is None:
            exceptions = Exception

        try:
            yield
        except exceptions:
            self.inc()
            raise

    def collect(self) -> Sample:
        # TODO: probably need a way to add default metric creation labels
        # ideally on Metric class initialization
        # while being careful of not messing up the tracking logic
        return Sample('_total', self._labels, self._metric_value_backend.get())


# this could be a class method, but might want to avoid it
def create_metric(
    name: str,
    required_labels: Sequence[str] | None = None,
    backend_class: Optional[Backend] = None,
    backend_config: Optional[BackendConfig] = None,
) -> Metric:
    collector = MetricCollector(name, Metric, required_labels)
    return Metric(collector, backend_class=backend_class, backend_config=backend_config)


def create_counter(
    name: str,
    required_labels: Sequence[str] | None = None,
    backend_class: Optional[Backend] = None,
    backend_config: Optional[BackendConfig] = None,
) -> Metric:
    collector = MetricCollector(name, Counter, required_labels)
    return Counter(collector, backend_class=backend_class, backend_config=backend_config)


# maybe just go with the typing alias
@dataclass
class Label:
    name: str
    value: str


# m = MetricCollector('name', ['bbo'])
my_metric = create_metric('name', ['bbo'])
