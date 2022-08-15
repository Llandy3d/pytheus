import pytest

from pytheus.metrics import MetricCollector, Metric, create_counter


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
        MetricCollector(name, Metric)

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
            MetricCollector(name, Metric)

    def test_validate_label_with_correct_values(self):
        labels = ['action', 'method', '_type']
        collector = MetricCollector('name', Metric)
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
        collector = MetricCollector('name', Metric)
        with pytest.raises(ValueError):
            collector._validate_labels([label])


class TestCounter:

    def test_can_increment(self):
        counter = create_counter('name')
        counter.inc()
        assert counter._value == 1

    def test_can_increment_with_value(self):
        counter = create_counter('name')
        counter.inc(7.2)
        assert counter._value == 7.2

    def test_negative_increment_raises(self):
        counter = create_counter('name')
        with pytest.raises(ValueError):
            counter.inc(-1)
