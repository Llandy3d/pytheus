import time
import pytest

from pytheus.exceptions import UnobservableMetricException, LabelValidationException
from pytheus.metrics import _MetricCollector, _Metric, Counter, Gauge, Histogram


class TestMetricCollector:

    @pytest.mark.parametrize(
        'name',
        [
            'prometheus_notifications_total',
            'process_cpu_seconds_total',
            'http_request_duration_seconds',
            'node_memory_usage_bytes',
            'http_requests_total',
            'foobar_build_info',
            'data_pipeline_last_record_processed_timestamp_seconds',
        ],
    )
    def test_name_with_correct_values(self, name):
        _MetricCollector(name, 'desc', _Metric)

    @pytest.mark.parametrize(
        'name',
        [
            'invalid.name',
            'µspecialcharacter',
            'http_req@st_total',
            'http{request}',
        ],
    )
    def test_name_with_incorrect_values(self, name):
        with pytest.raises(ValueError):
            _MetricCollector(name, 'desc', _Metric)

    def test_validate_required_labels_with_correct_values(self):
        labels = ['action', 'method', '_type']
        collector = _MetricCollector('name', 'desc', _Metric)
        collector._validate_required_labels(labels)

    @pytest.mark.parametrize(
        'label',
        [
            '__private',
            'microµ',
            '@type',
        ],
    )
    def test_validate_required_labels_with_incorrect_values(self, label):
        collector = _MetricCollector('name', 'desc', _Metric)
        with pytest.raises(LabelValidationException):
            collector._validate_required_labels([label])

    def test_collect_without_labels(self):
        counter = Counter('name', 'desc')
        samples = counter._collector.collect()
        assert len(list(samples)) == 1

    def test_collect_with_labels(self):
        counter = Counter('name', 'desc', required_labels=['a', 'b'])
        counter_a = counter.labels({'a': '1', 'b': '2'})
        counter_b = counter.labels({'a': '7', 'b': '8'})
        counter_c = counter.labels({'a': '6'})  # this should not be creating a sample
        samples = counter._collector.collect()
        assert len(list(samples)) == 2

    def test_collect_with_default_labels(self):
        counter = Counter('name', 'desc', required_labels=['a'], default_labels={'a': 1})
        samples = counter._collector.collect()
        samples = list(samples)
        assert len(samples) == 1
        assert 'a' in samples[0].labels
        assert 1 == samples[0].labels['a']

    def test_collect_with_labels_and_default_labels(self):
        default_labels = {'a': 3}
        counter = Counter('name', 'desc', required_labels=['a', 'b'], default_labels=default_labels)
        counter_a = counter.labels({'a': '1', 'b': '2'})
        counter_b = counter.labels({'a': '7', 'b': '8'})
        counter_c = counter.labels({'a': '6'})  # this should not be creating a sample
        counter_d = counter.labels({'b': '5'})
        samples = counter._collector.collect()
        samples = list(samples)
        assert len(samples) == 3
        assert samples[0].labels['a'] == '1'
        assert samples[1].labels['a'] == '7'
        assert samples[2].labels['a'] == 3

    def test_collector_created_on_metric_creation(self):
        counter = Counter('name', 'desc', required_labels=['a', 'b'])
        assert counter._collector.name == 'name'
        assert counter._collector.description == 'desc'
        assert counter._collector._required_labels == {'a', 'b'}

    def test_collector_reused_on_new_metric_instance(self):
        counter = Counter('name', 'desc', required_labels=['a', 'b'])
        counter_instance = Counter('name', 'desc', collector=counter._collector)
        assert counter._collector is counter_instance._collector


class TestMetric:

    def test_create_metric(self):
        metric = _Metric('name', 'desc')
        assert metric._name == 'name'
        assert metric._description == 'desc'

    def test_create_metric_with_required_labels(self):
        required_labels = ['bob', 'cat']
        metric = _Metric('name', 'desc', required_labels=required_labels)
        assert metric._collector._required_labels == set(required_labels)

    def test_create_metric_raises_with_labels(self):
        # only default labels are allowed to be set on creation
        with pytest.raises(LabelValidationException):
            _Metric('name', 'desc', required_labels=['a'], labels={'a': 1})

    def test_check_can_observe_without_required_labels(self):
        metric = _Metric('name', 'desc')
        assert metric._check_can_observe() is True

    def test_check_can_observe_with_required_labels_without_labels(self):
        metric = _Metric('name', 'desc', required_labels=['bob', 'cat'])
        assert metric._check_can_observe() is False

    def test_check_can_observe_with_required_labels_with_partial_labels(self):
        metric = _Metric('name', 'desc', required_labels=['bob', 'cat'])
        metric = metric.labels({'bob': 2})
        assert metric._check_can_observe() is False

    def test_check_can_observe_with_required_labels_with_labels(self):
        metric = _Metric('name', 'desc', required_labels=['bob', 'cat'])
        metric = metric.labels({'bob': 1, 'cat': 2})
        assert metric._check_can_observe() is True

    def test_raises_if_cannot_be_observed_observable(self):
        metric = _Metric('name', 'desc', required_labels=['bob', 'cat'])
        metric = metric.labels({'bob': 1, 'cat': 2})
        metric._raise_if_cannot_observe()

    def test_raises_if_cannot_be_observed_unobservable(self):
        metric = _Metric('name', 'desc', required_labels=['bob', 'cat'])
        metric = metric.labels({'bob': 1})
        with pytest.raises(UnobservableMetricException):
            metric._raise_if_cannot_observe()

    def test_check_can_observe_with_default_labels(self):
        metric = _Metric('name', 'desc', required_labels=['bob', 'cat'], default_labels={'bob': 1, 'cat': 2})
        assert metric._check_can_observe() is True

    def test_check_can_observe_with_default_labels_partial_uncomplete(self):
        metric = _Metric('name', 'desc', required_labels=['bob', 'cat'], default_labels={'bob': 1})
        assert metric._check_can_observe() is False

    def test_check_can_observe_with_default_labels_partial_complete(self):
        metric = _Metric('name', 'desc', required_labels=['bob', 'cat'], default_labels={'bob': 1})
        metric = metric.labels({'cat': 2})
        assert metric._check_can_observe() is True

    def test_check_can_observe_with_default_labels_partial_overriden_label(self):
        metric = _Metric('name', 'desc', required_labels=['bob', 'cat'], default_labels={'bob': 1})
        metric = metric.labels({'cat': 2, 'bob': 2})
        assert metric._check_can_observe() is True

    # labels

    def test_labels_without_labels_return_itself(self):
        metric = _Metric('name', 'desc')
        new = metric.labels({})
        assert new is metric

    def test_labels_without_required_labels_raises(self):
        metric = _Metric('name', 'desc')
        with pytest.raises(LabelValidationException):
            metric.labels({'a': 1})

    def test_labels_unobservable(self):
        metric = _Metric('name', 'desc', required_labels=['a', 'b'])
        metric = metric.labels({'a': 1})
        assert metric not in metric._collector._labeled_metrics.values()

    def test_labels_observable(self):
        metric = _Metric('name', 'desc', required_labels=['a', 'b'])
        metric = metric.labels({'a': 1, 'b': 2})
        assert metric in metric._collector._labeled_metrics.values()

    def test_labels_observable_returns_existing_child(self):
        metric = _Metric('name', 'desc', required_labels=['a', 'b'])
        metric_a = metric.labels({'a': 1, 'b': 2})
        metric_b = metric.labels({'a': 1, 'b': 2})
        assert len(metric._collector._labeled_metrics) == 1
        assert metric_a is metric_b

    def test_labels_with_unknown_label(self):
        metric = _Metric('name', 'desc', required_labels=['a', 'b'])
        with pytest.raises(LabelValidationException):
            metric.labels({'a': 1, 'c': 2})

    # default_labels

    def test_metric_with_default_labels(self):
        default_labels = {'bob': 'bobvalue'}
        metric = _Metric('name', 'desc', required_labels=['bob'], default_labels=default_labels)
        assert metric._collector._default_labels == default_labels

    def test_metric_with_default_labels_raises_without_required_labels(self):
        default_labels = {'bob': 'bobvalue'}
        with pytest.raises(LabelValidationException):
            _Metric('name', 'desc', default_labels=default_labels)

    def test_metric_with_default_labels_with_label_not_in_required_labels(self):
        default_labels = {'bobby': 'bobbyvalue'}
        with pytest.raises(LabelValidationException):
            _Metric('name', 'desc', required_labels=['bob'], default_labels=default_labels)

    def test_metric_with_default_labels_with_subset_of_required_labels(self):
        default_labels = {'bob': 'bobvalue'}
        metric = _Metric(
            'name',
            'desc',
            required_labels=['bob', 'bobby'],
            default_labels=default_labels
        )
        assert metric._collector._default_labels == default_labels

    def test_get_sample(self):
        from pytheus.metrics import Sample
        metric = _Metric('name', 'desc')
        sample = metric._get_sample()
        assert sample == Sample('', None, 0)

    def test_add_default_labels_to_sample(self):
        default_labels = {'bob': 'bobvalue'}
        metric = _Metric('name', 'desc', required_labels=['bob', 'cat'], default_labels=default_labels)
        metric = metric.labels({'cat': 2})
        sample = metric._get_sample()

        assert sample.labels == {'bob': 'bobvalue', 'cat': 2}

    def test_add_default_labels_to_sample_does_not_ovveride_provided_labels(self):
        default_labels = {'bob': 'bobvalue'}
        metric = _Metric('name', 'desc', required_labels=['bob', 'cat'], default_labels=default_labels)
        metric = metric.labels({'cat': 2, 'bob': 'newvalue'})
        sample = metric._get_sample()

        assert sample.labels == {'bob': 'newvalue', 'cat': 2}


class TestCounter:

    @pytest.fixture
    def counter(self):
        return Counter('name', 'desc')

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

    def test_collect_adds_correct_suffix(self, counter):
        sample = counter.collect()
        assert sample.suffix == '_total'


class TestGauge:

    @pytest.fixture
    def gauge(self):
        return Gauge('name', 'desc')

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


class TestHistogram:

    @pytest.fixture
    def histogram(self):
        return Histogram('name', 'desc')

    def test_create_histogram_with_default_labels(self):
        Histogram('name', 'desc', required_labels=['bob', 'cat'])

    def test_histogram_fails_with_le_label(self):
        with pytest.raises(LabelValidationException):
            Histogram('name', 'desc', required_labels=['bob', 'le'])
