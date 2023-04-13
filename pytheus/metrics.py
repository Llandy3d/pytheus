import functools
import itertools
import re
import time
from collections.abc import Generator
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Callable, Iterable, Sequence

from pytheus.backends import get_backend
from pytheus.exceptions import (
    BucketException,
    LabelValidationException,
    UnobservableMetricException,
)
from pytheus.registry import REGISTRY, Collector, Registry
from pytheus.utils import InfFloat, MetricType

Labels = dict[str, str]


metric_name_re = re.compile(r"[a-zA-Z_:][a-zA-Z0-9_:]*")
label_name_re = re.compile(r"[a-zA-Z_][a-zA-Z0-9_]*")


@dataclass
class Sample:
    suffix: str
    labels: dict[str, str] | None
    value: float


class CustomCollector(Collector):
    """
    Inheriting from this protocol is the current way to create a custom collector.
    The property `name` will return the lowercased class name so that it can be
    tracked in a registry.
    Not particularly liking this solution but for now it should suffice due to
    the current structure.
    """

    @property
    def name(self) -> str:
        return str.lower(self.__class__.__name__)

    # overriding the Collector protocol it requires to be writeable so we have this dummy setter
    @name.setter
    def name(self, value: str) -> None:
        pass


class _MetricCollector:
    """
    This handles the core logic for a specific named metric.
    It will do label validation, it will have the metric name and most importantly it will keep
    track of all the Child instances so that when `collect()` is called it will retrieve all
    the correct samples from all the possible observable Childrens.
    _labeled_metrics contains all observable metrics when required_labels is set.
    """

    def __init__(
        self,
        name: str,
        description: str,
        metric: "_Metric",
        required_labels: Sequence[str] | None = None,
        default_labels: Labels | None = None,
        registry: Registry | None = REGISTRY,
    ) -> None:
        if metric_name_re.fullmatch(name) is None:
            raise ValueError(f"Invalid metric name: {name}")

        if required_labels:
            is_histogram = isinstance(metric, Histogram)
            self._validate_required_labels(required_labels, is_histogram)

        self._required_labels = set(required_labels) if required_labels else None

        if default_labels:
            self._validate_labels(default_labels)

        self.name = name
        self.description = description
        self.type_ = metric.type_
        self._default_labels = default_labels
        self._default_labels_count = len(default_labels) if default_labels else 0
        self._metric = metric
        self._labeled_metrics: dict[tuple[str, ...], _Metric] = {}
        self._registry = registry

        if registry:
            registry.register(self)

    def _validate_required_labels(self, labels: Sequence[str], is_histogram: bool = False) -> None:
        """
        Validates label names according to the regex.
        Labels starting with `__` are reserved for internal use by Prometheus.
        """
        for label in labels:
            if label.startswith("__") or label_name_re.fullmatch(label) is None:
                raise LabelValidationException(f"Invalid label name: {label}")
            if is_histogram and label == "le":
                raise LabelValidationException(f"Invalid label name for Histogram: {label}")

    def _validate_labels(self, labels: Labels) -> None:
        """
        Validates labels.
        If no `required_labels` is set raises an error.
        `labels` will be also validated to be a subset of `required_labels`.
        """
        if not self._required_labels:
            raise LabelValidationException("trying to use labels while required_labels is None")

        labels_set = set(labels.keys())
        if not labels_set.issubset(self._required_labels):
            raise LabelValidationException(
                "labels different than required_labels: " f"{labels_set} != {self._required_labels}"
            )

    def collect(self) -> Iterable[Sample]:
        """
        Collects Samples for the metric.
        """
        labeled_metrics: Iterable[Sample]
        if self._required_labels:
            labeled_metrics = (
                sample for metric in self._labeled_metrics.values() for sample in metric.collect()
            )
            if self._default_labels and self._metric._can_observe:
                labeled_metrics = itertools.chain(labeled_metrics, self._metric.collect())
            return labeled_metrics
        else:
            return self._metric.collect()


class _Metric:
    type_: MetricType = MetricType.UNTYPED

    def __init__(
        self,
        name: str,
        description: str,
        required_labels: Sequence[str] | None = None,
        labels: Labels | None = None,
        default_labels: Labels | None = None,
        registry: Registry | None = REGISTRY,
        collector: _MetricCollector | None = None,
    ) -> None:
        self.name = name
        self.description = description
        self._labels = labels
        self._registry = registry
        self._metric_value_backend = None
        self._collector = (
            collector
            if collector
            else _MetricCollector(
                name, description, self, required_labels, default_labels, registry
            )
        )
        self._can_observe = self._check_can_observe()

        if not collector and labels:
            raise LabelValidationException(
                "Setting labels when creating a metric is not allowed. "
                "You might be looking for default_labels."
            )

        if self._can_observe and not isinstance(self, Histogram):
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

    def labels(self, labels_: Labels) -> "_Metric":
        """
        If no labels is passed to the call returns itself.
        If there are already present labels, they will be updated with the passed labels_ and if
        it's not observable will just return the new child instance. Otherwise it will also add
        the instance to the labeled_metrics on the collector.
        """
        # if not labels_ or self._collector._required_labels is None:
        if not labels_:
            return self

        self._collector._validate_labels(labels_)

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

        # __init__ arguments for the child
        child_kwargs = {
            "name": self.name,
            "description": self.description,
            "collector": self._collector,
            "labels": labels_,
            "registry": self._registry,
        }

        # pass down buckets list to the child
        if isinstance(self, Histogram):
            child_kwargs["buckets"] = self._upper_bounds

        assert self._collector._required_labels is not None
        if labels_count != len(self._collector._required_labels):
            # does not add to collector
            return self.__class__(**child_kwargs)  # type: ignore

        # add to collector
        sorted_label_values = tuple(v for _, v in sorted(labels_.items()))
        if sorted_label_values in self._collector._labeled_metrics:
            metric = self._collector._labeled_metrics[sorted_label_values]
        else:
            metric = self.__class__(**child_kwargs)  # type: ignore
            self._collector._labeled_metrics[sorted_label_values] = metric
        return metric

    def collect(self) -> Iterable[Sample]:
        raise NotImplementedError

    def _get_sample(self) -> Sample:
        """Get a Sample for testing. Each metric type will need to define its own."""
        self._raise_if_cannot_observe()
        sample = Sample("", self._labels, 0)
        return self._add_default_labels_to_sample(sample)

    def _add_default_labels_to_sample(self, sample: Sample) -> Sample:
        """Adds default labels if available to a sample."""
        if self._collector._default_labels_count:
            joint_labels = self._collector._default_labels.copy()  # type: ignore
            if sample.labels:
                joint_labels.update(sample.labels)
            sample.labels = joint_labels

        return sample

    def __repr__(self) -> str:
        return f"{self.__class__.__qualname__}({self._collector.name})"


class Counter(_Metric):
    type_: MetricType = MetricType.COUNTER

    def inc(self, value: float = 1.0) -> None:
        """
        Increments the value by the given amount.
        By default it will be 1.
        value must be >= 0.
        """
        self._raise_if_cannot_observe()
        if value < 0:
            raise ValueError(f"Counter increase value ({value}) must be >= 0")

        assert self._metric_value_backend is not None
        self._metric_value_backend.inc(value)

    @contextmanager
    def count_exceptions(
        self, exceptions: type[Exception] | tuple[Exception] | None = None
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

    def __call__(
        self,
        func: Callable | None = None,
        exceptions: type[Exception] | tuple[Exception] | None = None,
    ) -> Callable:
        """
        When called acts as a decorator counting exceptions raised.
        """
        if func is None:
            return functools.partial(self.__call__, exceptions=exceptions)

        @functools.wraps(func)
        def wrapper(*args, **kwargs):  # type: ignore
            with self.count_exceptions(exceptions):
                return func(*args, **kwargs)

        return wrapper

    def collect(self) -> Iterable[Sample]:
        self._raise_if_cannot_observe()
        assert self._metric_value_backend is not None
        sample = Sample("", self._labels, self._metric_value_backend.get())
        return (self._add_default_labels_to_sample(sample),)


class Gauge(_Metric):
    type_: MetricType = MetricType.GAUGE

    def inc(self, value: float = 1.0) -> None:
        """
        Increments the value by the given amount.
        By default it will be 1.
        """
        self._raise_if_cannot_observe()
        assert self._metric_value_backend is not None
        self._metric_value_backend.inc(value)

    def dec(self, value: float = 1.0) -> None:
        """
        Decrements the value by the given amount.
        By default it will be 1.
        """
        self._raise_if_cannot_observe()
        assert self._metric_value_backend is not None
        self._metric_value_backend.dec(value)

    def set(self, value: float) -> None:
        """
        Set the value to the given amount.
        """
        self._raise_if_cannot_observe()
        assert self._metric_value_backend is not None
        self._metric_value_backend.set(value)

    def set_to_current_time(self) -> None:
        """Set the value to the current unix timestamp."""
        self._raise_if_cannot_observe()
        assert self._metric_value_backend is not None
        self._metric_value_backend.set(time.time())

    @contextmanager
    def track_inprogress(self) -> Generator[None, None, None]:
        """
        Will increase the gauge value when entered and decrease it when exited.
        """
        self._raise_if_cannot_observe()
        self.inc()
        yield
        self.dec()

    def __call__(self, func: Callable | None = None, track_inprogress: bool = False) -> Callable:
        """
        When called acts as a decorator tracking the time taken by
        the wrapped function.

        If passing the parameter `track_inprogress` as `True` it will instead increase while the
        function is running and will decrease when it's finished.
        """
        if func is None:
            return functools.partial(self.__call__, track_inprogress=track_inprogress)

        @functools.wraps(func)
        def wrapper(*args, **kwargs):  # type: ignore
            if track_inprogress:
                with self.track_inprogress():
                    return func(*args, **kwargs)
            else:
                with self.time():
                    return func(*args, **kwargs)

        return wrapper

    @contextmanager
    def time(self) -> Generator[None, None, None]:
        """
        Times the duration inside of it and sets the value.
        """
        self._raise_if_cannot_observe()
        start = time.perf_counter()
        yield
        self.set(time.perf_counter() - start)

    def collect(self) -> Iterable[Sample]:
        self._raise_if_cannot_observe()
        assert self._metric_value_backend is not None
        sample = Sample("", self._labels, self._metric_value_backend.get())
        return (self._add_default_labels_to_sample(sample),)


class Histogram(_Metric):
    type_: MetricType = MetricType.HISTOGRAM
    # Default buckets are tailored to broadly measure the response time (in seconds) of a network
    # service. Most likely you will be required to define buckets customized to your use case.
    # Values taken from the golang/rust client.
    DEFAULT_BUCKETS = (0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10)

    def __init__(
        self,
        name: str,
        description: str,
        required_labels: Sequence[str] | None = None,
        labels: Labels | None = None,
        default_labels: Labels | None = None,
        registry: Registry | None = REGISTRY,
        collector: _MetricCollector | None = None,
        buckets: Sequence[float] = DEFAULT_BUCKETS,
    ) -> None:
        super().__init__(
            name,
            description,
            required_labels,
            labels,
            default_labels,
            registry,
            collector,
        )

        # buckets

        # if buckets is None or an empty sequence default buckets will be used
        if not buckets:
            buckets = list(self.DEFAULT_BUCKETS)
        else:
            buckets = list(buckets)

        sorted_buckets = sorted(buckets)
        if buckets != sorted_buckets:
            raise BucketException(
                f"buckets values are not in sorted order. {buckets} != {sorted_buckets}"
            )

        # +Inf is required so we always add it
        last_bucket_value = buckets[-1]
        if isinstance(last_bucket_value, InfFloat):
            pass
        elif last_bucket_value == float("inf"):
            buckets[-1] = InfFloat("inf")
        else:
            buckets.append(InfFloat("inf"))

        self._upper_bounds = buckets

        # create bucket values
        self._buckets = None
        self._sum = None
        self._count = None
        if self._can_observe:
            self._buckets = []

            # this will be added just to the default name on the redis backend but it is
            # fine for now as it's the only one. Might require a more robust way in the future.
            self._sum = get_backend(self, histogram_bucket="sum")
            self._count = get_backend(self, histogram_bucket="count")

            for bucket in self._upper_bounds:
                self._buckets.append(get_backend(self, histogram_bucket=str(bucket)))

    def observe(self, value: float) -> None:
        """
        Observe the given value.
        Value can be negative, in that case the rate function will be less useful so
        it's better to consider using two histograms for positive and negative values.
        """
        self._raise_if_cannot_observe()
        assert self._sum is not None
        self._sum.inc(value)

        for i, bound in enumerate(self._upper_bounds):
            if value <= bound:
                self._buckets[i].inc(1)

        assert self._count is not None
        self._count.inc(1)

    @contextmanager
    def time(self) -> Generator[None, None, None]:
        """
        Times the duration inside of it and sets the value.
        """
        self._raise_if_cannot_observe()
        start = time.perf_counter()
        yield
        self.observe(time.perf_counter() - start)

    def __call__(self, func: Callable) -> Callable:
        """
        When called acts as a decorator tracking the time taken by
        the wrapped function.
        """

        @functools.wraps(func)
        def wrapper(*args, **kwargs):  # type: ignore
            with self.time():
                return func(*args, **kwargs)

        return wrapper

    def collect(self) -> Iterable[Sample]:
        self._raise_if_cannot_observe()
        samples = []
        for i, bound in enumerate(self._upper_bounds):
            bucket_labels = self._labels.copy() if self._labels else {}
            bucket_labels["le"] = str(bound)
            sample = Sample("_bucket", bucket_labels, self._buckets[i].get())
            samples.append(sample)

        assert self._sum is not None
        assert self._count is not None
        samples.append(Sample("_sum", self._labels, self._sum.get()))
        samples.append(Sample("_count", self._labels, self._count.get()))

        return (self._add_default_labels_to_sample(sample) for sample in samples)


# maybe just go with the typing alias
@dataclass
class Label:
    name: str
    value: str
