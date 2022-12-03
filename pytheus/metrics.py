import re
import itertools
from collections.abc import Generator
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Sequence, Iterator

from pytheus.backends import get_backend
from pytheus.exceptions import UnobservableMetricException, LabelValidationException
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
        metric: '_Metric',
        required_labels: Sequence[str] | None = None,
        default_labels: Labels | None = None,
        registry: Registry = REGISTRY
    ) -> None:
        if metric_name_re.fullmatch(name) is None:
            raise ValueError(f'Invalid metric name: {name}')

        if required_labels:
            self._validate_labels(required_labels)

        self._required_labels = set(required_labels) if required_labels else None

        if default_labels:
            self._validate_default_labels(default_labels)

        self.name = name
        self.description = description
        self._default_labels = default_labels
        self._default_labels_count = len(default_labels) if default_labels else 0
        self._metric = metric
        self._labeled_metrics: dict[tuple[str, ...], _Metric] = {}
        registry.register(self)

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

    def _validate_default_labels(self, labels: Labels):
        """
        Validates default labels.
        If no `required_labels` is set raises an error.
        `default_labels` will be also validated to be a subset of `required_labels`.
        """
        if not self._required_labels:
            raise LabelValidationException('default_labels set while required_labels is None')

        default_labels_set = set(labels.keys())
        if not default_labels_set.issubset(self._required_labels):
            raise LabelValidationException(
                'default_labels different than required_labels: '
                f'{default_labels_set} != {self._required_labels}'
            )

    def collect(self) -> Iterator[Sample]:
        """
        Collects Samples for the metric.
        """
        if self._required_labels:
            labeled_metrics = (metric.collect() for metric in self._labeled_metrics.values())
            if self._default_labels and self._metric._can_observe:
                labeled_metrics = itertools.chain(labeled_metrics, (self._metric.collect(),))
            return labeled_metrics
        else:
            return iter((self._metric.collect(),))


class _Metric:
    def __init__(
        self,
        name: str,
        description: str,
        required_labels: Sequence[str] | None = None,
        labels: Labels | None = None,
        default_labels: Labels | None = None,
        collector: _MetricCollector | None = None,
    ) -> None:
        self._name = name
        self._description = description
        self._labels = labels
        self._metric_value_backend = None
        self._collector = (
            collector
            if collector
            else _MetricCollector(name, description, self, required_labels, default_labels)
        )
        self._can_observe = self._check_can_observe()

        if not collector and labels:
            raise LabelValidationException(
                'Setting labels when creating a metric is not allowed. '
                'You might be looking for default_labels.'
            )

        if self._can_observe:
            self._metric_value_backend = get_backend(self)

    def _check_can_observe(self) -> bool:
        if not self._collector._required_labels:
            return True

        required_labels_count = len(self._collector._required_labels)
        if (
            self._collector._default_labels_count
            and self._collector._default_labels_count == required_labels_count
        ):
            return True

        if not self._labels:
            return False

        if self._collector._default_labels:
            default_labels = self._collector._default_labels.copy()
            default_labels.update(self._labels)
            labels_count = len(default_labels)
        else:
            labels_count = len(self._labels)

        if labels_count != required_labels_count:
            return False

        return True

    def _raise_if_cannot_observe(self) -> None:
        """Raise if the metric cannot be observed, for example if labels values are missing."""
        if not self._can_observe:
            raise UnobservableMetricException

    def labels(self, labels_: Labels) -> '_Metric':
        if not labels_ or self._collector._required_labels is None:
            return self

        if self._labels:
            new_labels = self._labels.copy()
            new_labels.update(labels_)
            labels_ = new_labels

        if self._collector._default_labels:
            default_labels = self._collector._default_labels.copy()
            default_labels.update(labels_)
            labels_count = len(default_labels)
        else:
            labels_count = len(labels_)

        if labels_count != len(self._collector._required_labels):
            # does not add to collector
            return self.__class__(
                self._name,
                self._description,
                collector=self._collector,
                labels=labels_
            )

        # add to collector
        sorted_label_values = tuple(v for _, v in sorted(labels_.items()))
        if sorted_label_values in self._collector._labeled_metrics:
            metric = self._collector._labeled_metrics[sorted_label_values]
        else:
            metric = self.__class__(
                self._name,
                self._description,
                collector=self._collector,
                labels=labels_
            )
            self._collector._labeled_metrics[sorted_label_values] = metric
        return metric

    def collect(self) -> Sample:
        raise NotImplementedError

    def _get_sample(self) -> Sample:
        """Get a Sample for testing. Each metric type will need to define its own."""
        self._raise_if_cannot_observe()
        sample = Sample('', self._labels, 0)
        return self._add_default_labels_to_sample(sample)

    def _add_default_labels_to_sample(self, sample: Sample) -> Sample:
        """Adds default labels if available to a sample."""
        if self._collector._default_labels_count:
            joint_labels = self._collector._default_labels.copy()
            if sample.labels:
                joint_labels.update(sample.labels)
            sample.labels = joint_labels

        return sample

    def __repr__(self) -> str:
        return f'{self.__class__.__qualname__}({self._collector.name})'


class Counter(_Metric):

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
        except exceptions:  # type: ignore
            self.inc()
            raise

    def collect(self) -> Sample:
        self._raise_if_cannot_observe()
        sample = Sample('_total', self._labels, self._metric_value_backend.get())
        return self._add_default_labels_to_sample(sample)


# maybe just go with the typing alias
@dataclass
class Label:
    name: str
    value: str
