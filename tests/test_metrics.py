import pytest

from pytheus.metrics import _MetricCollector, Metric, Counter


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
        _MetricCollector(name, 'desc', Metric)

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
            _MetricCollector(name, 'desc', Metric)

    def test_validate_label_with_correct_values(self):
        labels = ['action', 'method', '_type']
        collector = _MetricCollector('name', 'desc', Metric)
        collector._validate_labels(labels)

    @pytest.mark.parametrize(
        'label',
        [
            '__private',
            'microµ',
            '@type',
        ],
    )
    def test_validate_label_with_incorrect_values(self, label):
        collector = _MetricCollector('name', 'desc', Metric)
        with pytest.raises(ValueError):
            collector._validate_labels([label])

    def test_collect_without_labels(self):
        counter = Counter('name', 'desc')
        samples = counter._collector.collect()
        assert len(samples) == 1

    def test_collect_with_labels(self):
        counter = Counter('name', 'desc', required_labels=['a', 'b'])
        counter_a = counter.labels({'a': '1', 'b': '2'})
        counter_b = counter.labels({'a': '7', 'b': '8'})
        counter_c = counter.labels({'a': '6'})  # this should not be creating a sample
        samples = counter._collector.collect()
        assert len(list(samples)) == 2

    def test_collector_created_on_metric_creation(self):
        counter = Counter('name', 'desc', required_labels=['a', 'b'])
        assert counter._collector.name == 'name'
        assert counter._collector.description == 'desc'
        assert counter._collector._required_labels == {'a', 'b'}

    def test_collector_reused_on_new_metric_instance(self):
        counter = Counter('name', 'desc', required_labels=['a', 'b'])
        counter_instance = Counter('name', 'desc', collector=counter._collector)
        assert counter._collector is counter_instance._collector


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
