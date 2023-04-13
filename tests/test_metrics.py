import time
from unittest import mock

import pytest

from pytheus.exceptions import (
    BucketException,
    LabelValidationException,
    UnobservableMetricException,
)
from pytheus.metrics import Counter, CustomCollector, Gauge, Histogram, _Metric, _MetricCollector
from pytheus.registry import REGISTRY, CollectorRegistry
from pytheus.utils import InfFloat, MetricType


@pytest.fixture
def set_empty_registry():
    """
    As the REGISTRY object is global by default, we might have data from other tests.
    So with this fixture we just set a new empty one.
    """
    REGISTRY.set_registry(CollectorRegistry())


class TestMetricCollector:
    @pytest.mark.parametrize(
        "name",
        [
            "prometheus_notifications_total",
            "process_cpu_seconds_total",
            "http_request_duration_seconds",
            "node_memory_usage_bytes",
            "http_requests_total",
            "foobar_build_info",
            "data_pipeline_last_record_processed_timestamp_seconds",
        ],
    )
    def test_name_with_correct_values(self, name):
        _MetricCollector(name, "desc", _Metric)

    @pytest.mark.parametrize(
        "name",
        [
            "invalid.name",
            "µspecialcharacter",
            "http_req@st_total",
            "http{request}",
        ],
    )
    def test_name_with_incorrect_values(self, name):
        with pytest.raises(ValueError):
            _MetricCollector(name, "desc", _Metric)

    def test_validate_required_labels_with_correct_values(self):
        labels = ["action", "method", "_type"]
        collector = _MetricCollector("name", "desc", _Metric)
        collector._validate_required_labels(labels)

    @pytest.mark.parametrize(
        "label",
        [
            "__private",
            "microµ",
            "@type",
        ],
    )
    def test_validate_required_labels_with_incorrect_values(self, label):
        collector = _MetricCollector("name", "desc", _Metric)
        with pytest.raises(LabelValidationException):
            collector._validate_required_labels([label])

    def test_collect_without_labels(self):
        counter = Counter("name", "desc")
        samples = counter._collector.collect()
        assert len(list(samples)) == 1

    def test_collect_with_labels(self):
        counter = Counter("name", "desc", required_labels=["a", "b"])
        counter_a = counter.labels({"a": "1", "b": "2"})  # noqa: F841
        counter_b = counter.labels({"a": "7", "b": "8"})  # noqa: F841
        counter_c = counter.labels({"a": "6"})  # this should not be creating a sample # noqa: F841
        samples = counter._collector.collect()
        assert len(list(samples)) == 2

    def test_collect_with_default_labels(self):
        counter = Counter("name", "desc", required_labels=["a"], default_labels={"a": 1})
        samples = counter._collector.collect()
        samples = list(samples)
        assert len(samples) == 1
        assert "a" in samples[0].labels
        assert 1 == samples[0].labels["a"]

    def test_collect_with_labels_and_default_labels(self):
        default_labels = {"a": 3}
        counter = Counter("name", "desc", required_labels=["a", "b"], default_labels=default_labels)
        counter_a = counter.labels({"a": "1", "b": "2"})  # noqa: F841
        counter_b = counter.labels({"a": "7", "b": "8"})  # noqa: F841
        counter_c = counter.labels({"a": "6"})  # this should not be creating a sample  # noqa: F841
        counter_d = counter.labels({"b": "5"})  # noqa: F841
        samples = counter._collector.collect()
        samples = list(samples)
        assert len(samples) == 3
        assert samples[0].labels["a"] == "1"
        assert samples[1].labels["a"] == "7"
        assert samples[2].labels["a"] == 3

    def test_collector_created_on_metric_creation(self):
        counter = Counter("name", "desc", required_labels=["a", "b"])
        assert counter._collector.name == "name"
        assert counter._collector.description == "desc"
        assert counter._collector._required_labels == {"a", "b"}

    def test_collector_reused_on_new_metric_instance(self):
        counter = Counter("name", "desc", required_labels=["a", "b"])
        counter_instance = Counter("name", "desc", collector=counter._collector)
        assert counter._collector is counter_instance._collector


class TestMetric:
    def test_create_metric(self):
        metric = _Metric("name", "desc")
        assert metric.name == "name"
        assert metric.description == "desc"
        assert metric.type_ == MetricType.UNTYPED

    def test_create_metric_without_registering_to_default_collector(self, set_empty_registry):
        metric = _Metric("name", "desc", registry=None)
        assert metric._registry is None
        assert metric._collector._registry is None
        assert len(list(REGISTRY.collect())) == 0

    def test_create_metric_with_required_labels(self):
        required_labels = ["bob", "cat"]
        metric = _Metric("name", "desc", required_labels=required_labels)
        assert metric._collector._required_labels == set(required_labels)

    def test_create_metric_raises_with_labels(self):
        # only default labels are allowed to be set on creation
        with pytest.raises(LabelValidationException):
            _Metric("name", "desc", required_labels=["a"], labels={"a": 1})

    def test_check_can_observe_without_required_labels(self):
        metric = _Metric("name", "desc")
        assert metric._check_can_observe() is True

    def test_check_can_observe_with_required_labels_without_labels(self):
        metric = _Metric("name", "desc", required_labels=["bob", "cat"])
        assert metric._check_can_observe() is False

    def test_check_can_observe_with_required_labels_with_partial_labels(self):
        metric = _Metric("name", "desc", required_labels=["bob", "cat"])
        metric = metric.labels({"bob": 2})
        assert metric._check_can_observe() is False

    def test_check_can_observe_with_required_labels_with_labels(self):
        metric = _Metric("name", "desc", required_labels=["bob", "cat"])
        metric = metric.labels({"bob": 1, "cat": 2})
        assert metric._check_can_observe() is True

    def test_raises_if_cannot_be_observed_observable(self):
        metric = _Metric("name", "desc", required_labels=["bob", "cat"])
        metric = metric.labels({"bob": 1, "cat": 2})
        metric._raise_if_cannot_observe()

    def test_raises_if_cannot_be_observed_unobservable(self):
        metric = _Metric("name", "desc", required_labels=["bob", "cat"])
        metric = metric.labels({"bob": 1})
        with pytest.raises(UnobservableMetricException):
            metric._raise_if_cannot_observe()

    def test_check_can_observe_with_default_labels(self):
        metric = _Metric(
            "name",
            "desc",
            required_labels=["bob", "cat"],
            default_labels={"bob": 1, "cat": 2},
        )
        assert metric._check_can_observe() is True

    def test_check_can_observe_with_default_labels_partial_uncomplete(self):
        metric = _Metric("name", "desc", required_labels=["bob", "cat"], default_labels={"bob": 1})
        assert metric._check_can_observe() is False

    def test_check_can_observe_with_default_labels_partial_complete(self):
        metric = _Metric("name", "desc", required_labels=["bob", "cat"], default_labels={"bob": 1})
        metric = metric.labels({"cat": 2})
        assert metric._check_can_observe() is True

    def test_check_can_observe_with_default_labels_partial_overriden_label(self):
        metric = _Metric("name", "desc", required_labels=["bob", "cat"], default_labels={"bob": 1})
        metric = metric.labels({"cat": 2, "bob": 2})
        assert metric._check_can_observe() is True

    # labels

    def test_labels_without_labels_return_itself(self):
        metric = _Metric("name", "desc")
        new = metric.labels({})
        assert new is metric

    def test_labels_without_required_labels_raises(self):
        metric = _Metric("name", "desc")
        with pytest.raises(LabelValidationException):
            metric.labels({"a": 1})

    def test_labels_unobservable(self):
        metric = _Metric("name", "desc", required_labels=["a", "b"])
        metric = metric.labels({"a": 1})
        assert metric not in metric._collector._labeled_metrics.values()

    def test_labels_observable(self):
        metric = _Metric("name", "desc", required_labels=["a", "b"])
        metric = metric.labels({"a": 1, "b": 2})
        assert metric in metric._collector._labeled_metrics.values()

    def test_labels_observable_returns_existing_child(self):
        metric = _Metric("name", "desc", required_labels=["a", "b"])
        metric_a = metric.labels({"a": 1, "b": 2})
        metric_b = metric.labels({"a": 1, "b": 2})
        assert len(metric._collector._labeled_metrics) == 1
        assert metric_a is metric_b

    def test_labels_with_unknown_label(self):
        metric = _Metric("name", "desc", required_labels=["a", "b"])
        with pytest.raises(LabelValidationException):
            metric.labels({"a": 1, "c": 2})

    # default_labels

    def test_metric_with_default_labels(self):
        default_labels = {"bob": "bobvalue"}
        metric = _Metric("name", "desc", required_labels=["bob"], default_labels=default_labels)
        assert metric._collector._default_labels == default_labels

    def test_metric_with_default_labels_raises_without_required_labels(self):
        default_labels = {"bob": "bobvalue"}
        with pytest.raises(LabelValidationException):
            _Metric("name", "desc", default_labels=default_labels)

    def test_metric_with_default_labels_with_label_not_in_required_labels(self):
        default_labels = {"bobby": "bobbyvalue"}
        with pytest.raises(LabelValidationException):
            _Metric("name", "desc", required_labels=["bob"], default_labels=default_labels)

    def test_metric_with_default_labels_with_subset_of_required_labels(self):
        default_labels = {"bob": "bobvalue"}
        metric = _Metric(
            "name",
            "desc",
            required_labels=["bob", "bobby"],
            default_labels=default_labels,
        )
        assert metric._collector._default_labels == default_labels

    def test_get_sample(self):
        from pytheus.metrics import Sample

        metric = _Metric("name", "desc")
        sample = metric._get_sample()
        assert sample == Sample("", None, 0)

    def test_add_default_labels_to_sample(self):
        default_labels = {"bob": "bobvalue"}
        metric = _Metric(
            "name",
            "desc",
            required_labels=["bob", "cat"],
            default_labels=default_labels,
        )
        metric = metric.labels({"cat": 2})
        sample = metric._get_sample()

        assert sample.labels == {"bob": "bobvalue", "cat": 2}

    def test_add_default_labels_to_sample_does_not_ovveride_provided_labels(self):
        default_labels = {"bob": "bobvalue"}
        metric = _Metric(
            "name",
            "desc",
            required_labels=["bob", "cat"],
            default_labels=default_labels,
        )
        metric = metric.labels({"cat": 2, "bob": "newvalue"})
        sample = metric._get_sample()

        assert sample.labels == {"bob": "newvalue", "cat": 2}


class TestCounter:
    @pytest.fixture
    def counter(self):
        return Counter("name", "desc")

    def test_metric_type(self, counter):
        assert counter.type_ == MetricType.COUNTER

    def test_can_increment(self, counter):
        counter.inc()
        assert counter._metric_value_backend.get() == 1

    def test_can_increment_with_value(self, counter):
        counter.inc(7.2)
        assert counter._metric_value_backend.get() == 7.2

    def test_negative_increment_raises(self, counter):
        with pytest.raises(ValueError):
            counter.inc(-1)

    def test_count_exception(self, counter):
        with pytest.raises(ValueError):
            with counter.count_exceptions():
                raise ValueError

        assert counter._metric_value_backend.get() == 1

    def test_count_exception_with_specified(self, counter):
        with pytest.raises(ValueError):
            with counter.count_exceptions((IndexError, ValueError)):
                raise ValueError

        assert counter._metric_value_backend.get() == 1

    def test_count_exception_with_specified_is_ignored(self, counter):
        with pytest.raises(ValueError):
            with counter.count_exceptions(IndexError):
                raise ValueError

        assert counter._metric_value_backend.get() == 0

    def test_count_exception_with_decorator(self, counter):
        @counter
        def test():
            raise ValueError

        with pytest.raises(ValueError):
            test()

        assert counter._metric_value_backend.get() == 1

    def test_count_exception_with_decorator_multiple(self, counter):
        @counter
        def test():
            raise ValueError

        @counter
        def test_2():
            raise ValueError

        with pytest.raises(ValueError):
            test()
        with pytest.raises(ValueError):
            test_2()

        assert counter._metric_value_backend.get() == 2

    def test_count_exception_with_specified_as_decorator(self, counter):
        @counter(exceptions=(IndexError, ValueError))
        def test():
            raise ValueError

        with pytest.raises(ValueError):
            test()

        assert counter._metric_value_backend.get() == 1

    def test_count_exception_with_specified_is_ignored_as_decorator(self, counter):
        @counter(exceptions=IndexError)
        def test():
            raise ValueError

        with pytest.raises(ValueError):
            test()

        assert counter._metric_value_backend.get() == 0


class TestGauge:
    @pytest.fixture
    def gauge(self):
        return Gauge("name", "desc")

    def test_metric_type(self, gauge):
        assert gauge.type_ == MetricType.GAUGE

    def test_gauge_starts_at_zero(self, gauge):
        assert gauge._metric_value_backend.get() == 0

    def test_can_increment(self, gauge):
        gauge.inc()
        assert gauge._metric_value_backend.get() == 1

    def test_can_increment_with_value(self, gauge):
        gauge.inc(7.2)
        assert gauge._metric_value_backend.get() == 7.2

    def test_can_increment_with_negative_value(self, gauge):
        gauge.inc(-7.2)
        assert gauge._metric_value_backend.get() == -7.2

    def test_can_decrement(self, gauge):
        gauge.dec()
        assert gauge._metric_value_backend.get() == -1

    def test_can_decrement_with_value(self, gauge):
        gauge.dec(7.2)
        assert gauge._metric_value_backend.get() == -7.2

    def test_can_decrement_with_negative_value(self, gauge):
        gauge.dec(-7.2)
        assert gauge._metric_value_backend.get() == 7.2

    def test_can_set(self, gauge):
        gauge.set(5.2)
        assert gauge._metric_value_backend.get() == 5.2

    def test_can_set_negative(self, gauge):
        gauge.set(-5.2)
        assert gauge._metric_value_backend.get() == -5.2

    # this has to fail sooner or later, the question is when ?
    def test_set_to_current_time(self, gauge):
        time_ = time.time()
        gauge.set_to_current_time()
        assert int(gauge._metric_value_backend.get()) == int(time_)

    def test_track_inprogress(self, gauge):
        with gauge.track_inprogress():
            assert gauge._metric_value_backend.get() == 1

    def test_track_inprogress_multiple(self, gauge):
        # will increment and decrement when exiting the context manager
        with gauge.track_inprogress():
            pass

        with gauge.track_inprogress():
            with gauge.track_inprogress():
                assert gauge._metric_value_backend.get() == 2

    def test_time(self, gauge):
        with gauge.time():
            pass
        assert gauge._metric_value_backend.get() != 0

    def test_as_decorator(self, gauge):
        @gauge
        def test():
            pass

        test()
        assert gauge._metric_value_backend.get() != 0

    def test_as_decorator_with_track_inprogress(self, gauge):
        backend_mock = mock.Mock()
        gauge._metric_value_backend = backend_mock

        @gauge(track_inprogress=True)
        def test():
            pass

        test()
        backend_mock.inc.assert_called()
        backend_mock.dec.assert_called()

    def test_as_decorator_with_track_inprogress_as_false(self, gauge):
        @gauge(track_inprogress=False)
        def test():
            pass

        test()
        assert gauge._metric_value_backend.get() != 0


class TestHistogram:
    @pytest.fixture
    def histogram(self):
        return Histogram("name", "desc")

    def test_metric_type(self, histogram):
        assert histogram.type_ == MetricType.HISTOGRAM

    def test_create_histogram_with_default_labels(self):
        Histogram("name", "desc", required_labels=["bob", "cat"])

    def test_histogram_fails_with_le_label(self):
        with pytest.raises(LabelValidationException):
            Histogram("name", "desc", required_labels=["bob", "le"])

    def test_buckets_adds_inf_implicitly_float_number(self):
        buckets = [0.2, 0.5, 1]
        expected = [0.2, 0.5, 1, InfFloat("inf")]
        histogram = Histogram("name", "desc", buckets=buckets)
        assert histogram._upper_bounds == expected
        assert isinstance(histogram._upper_bounds[-1], InfFloat)

    def test_buckets_adds_inf_implicitly_float_inf(self):
        buckets = [0.2, 0.5, 1, float("inf")]
        expected = [0.2, 0.5, 1, InfFloat("inf")]
        histogram = Histogram("name", "desc", buckets=buckets)
        assert histogram._upper_bounds == expected
        assert isinstance(histogram._upper_bounds[-1], InfFloat)

    def test_buckets_adds_inf_implicitly_inf_float(self):
        buckets = [0.2, 0.5, 1, InfFloat("inf")]
        expected = [0.2, 0.5, 1, InfFloat("inf")]
        histogram = Histogram("name", "desc", buckets=buckets)
        assert histogram._upper_bounds == expected
        assert isinstance(histogram._upper_bounds[-1], InfFloat)

    def test_buckets_with_sorted_order(self):
        buckets = [0.2, 0.5, 1]
        histogram = Histogram("name", "desc", buckets=buckets)
        assert histogram._upper_bounds == buckets + [InfFloat("inf")]

    def test_buckets_with_unsorted_order_fails(self):
        with pytest.raises(BucketException):
            Histogram("name", "desc", buckets=(0.2, 1, 0.5))

    def test_buckets_empty_uses_default_buckets(self):
        histogram = Histogram("name", "desc", buckets=[])
        assert histogram._upper_bounds == list(histogram.DEFAULT_BUCKETS) + [float("inf")]

    def test_does_not_have_metric_value_backend(self, histogram):
        assert histogram._metric_value_backend is None

    def test_unobservable_does_not_create_buckets(self):
        histogram = Histogram("name", "desc", required_labels=["bob"])
        assert histogram._buckets is None
        assert histogram._sum is None
        assert histogram._count is None

    def test_observable_creates_buckets(self):
        histogram = Histogram("name", "desc", required_labels=["bob"])
        histogram = histogram.labels({"bob": "cat"})
        assert histogram._sum is not None
        assert histogram._count is not None
        assert histogram._buckets is not None
        assert len(histogram._buckets) == len(histogram._upper_bounds)

    def test_labeled_observable_respects_custom_buckets(self):
        buckets = [0.2, 0.5, 1]
        histogram = Histogram("name", "desc", required_labels=["bob"], buckets=buckets)
        child_histogram = histogram.labels({"bob": "cat"})
        assert child_histogram._upper_bounds == histogram._upper_bounds
        assert len(child_histogram._buckets) == len(histogram._upper_bounds)

    def test_collect(self):
        buckets = [0.2, 0.5, 1]
        histogram = Histogram("name", "desc", buckets=buckets)
        samples = histogram.collect()
        samples = list(samples)

        assert "le" in samples[0].labels
        assert "0.2" in samples[0].labels.values()
        assert len(samples) == 6  # includes float('inf')

    def test_osberve_unobservable_raises(self):
        histogram = Histogram("name", "desc", required_labels=["bob"])
        with pytest.raises(UnobservableMetricException):
            histogram.observe(2)

    def test_observe(self):
        histogram = Histogram("name", "desc", buckets=[0.2, 0.5, 1])
        histogram.observe(0.4)

        assert histogram._sum.get() == 0.4
        assert histogram._count.get() == 1
        assert histogram._buckets[0].get() == 0
        assert histogram._buckets[1].get() == 1
        assert histogram._buckets[2].get() == 1

    def test_time(self, histogram):
        with histogram.time():
            pass
        assert histogram._count.get() == 1
        assert histogram._count.get() != 0

    def test_as_decorator(self, histogram):
        @histogram
        def test():
            pass

        test()
        assert histogram._count.get() == 1
        assert histogram._count.get() != 0

    def test_as_decorator_multiple(self, histogram):
        @histogram
        def test():
            pass

        @histogram
        def test_2():
            pass

        test()
        test_2()
        assert histogram._count.get() == 2
        assert histogram._count.get() != 0


class _TestCollector(CustomCollector):
    def collect(self):
        counter = Counter("name", "desc", registry=None)
        counter.inc()
        yield counter


class TestCustomCollector:
    def test_create_custom_collector(self):
        registry = CollectorRegistry()
        registry.register(_TestCollector())

        assert "_testcollector" in registry._collectors

    def test_custom_collector_collect(self):
        custom_collector = _TestCollector()
        metrics = list(custom_collector.collect())

        assert len(metrics) == 1
        assert metrics[0]._metric_value_backend._value == 1.0

    def test_cannot_add_two_custom_collectors_with_same_name(self, set_empty_registry):
        first_collector = _TestCollector()
        second_collector = _TestCollector()
        registry = CollectorRegistry()
        registry.register(first_collector)
        registry.register(second_collector)

        assert first_collector is not second_collector
        assert registry._collectors["_testcollector"] is first_collector

    def test_registry_correctly_return_custom_collector(self):
        custom_collector = _TestCollector()
        registry = CollectorRegistry()
        registry.register(custom_collector)

        collectors = registry.collect()
        assert list(collectors)[0] is custom_collector

    def test_can_remove_from_registry(self):
        custom_collector = _TestCollector()
        registry = CollectorRegistry()
        registry.register(custom_collector)
        registry.unregister(custom_collector)

        collectors = registry.collect()
        assert len(list(collectors)) == 0

    def test_adding_to_registry_with_already_present_metric_with_same_name(self):
        registry = CollectorRegistry()
        counter = Counter("name", "desc", registry=registry)
        registry.register(_TestCollector())

        assert len(registry._collectors) == 1
        assert registry._collectors["name"] is counter._collector
