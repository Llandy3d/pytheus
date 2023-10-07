from concurrent.futures import ProcessPoolExecutor
from unittest import mock

import pytest

from pytheus.backends.base import SingleProcessBackend, load_backend
from pytheus.backends.redis import MultiProcessRedisBackend
from pytheus.exposition import generate_metrics
from pytheus.metrics import Counter, Gauge, Histogram, Sample, Summary
from pytheus.registry import CollectorRegistry

load_backend(MultiProcessRedisBackend)
pool = MultiProcessRedisBackend.CONNECTION_POOL


# automatically clear the cache after every test function
@pytest.fixture(autouse=True)
def clear_redis():
    pool.flushall()


@pytest.mark.parametrize(
    "backend",
    [
        MultiProcessRedisBackend({}, Counter("name", "desc", registry=None)),
        MultiProcessRedisBackend(
            {},
            Counter(
                "name_labels",
                "desc",
                required_labels=["bob"],
                default_labels={"bob": "cat"},
                registry=None,
            ),
        ),
    ],
)
class TestMultiProcessRedisBackend:
    @pytest.fixture(autouse=True)
    def _init_key(self, backend):
        backend._init_key()

    def test_get(self, backend):
        assert backend.get() == 0.0

    def test_inc(self, backend):
        backend.inc(1.0)
        assert backend.get() == 1.0

    def test_dec(self, backend):
        backend.dec(1.0)
        assert backend.get() == -1.0

    def test_set(self, backend):
        backend.set(3.0)
        assert backend.get() == 3.0

    def test_get_handles_remote_key_deletion(self, backend):
        pool.flushall()
        assert backend.get() == 0.0


def test_create_backend():
    counter = Counter("name", "desc")
    backend = MultiProcessRedisBackend({}, counter)

    assert backend._key_name == counter.name
    assert backend._histogram_bucket is None
    assert backend._labels_hash is None
    assert pool.exists(backend._key_name)


def test_create_backend_with_prefix():
    counter = Counter("name", "desc")
    backend = MultiProcessRedisBackend({"key_prefix": "test"}, counter)

    assert backend._key_name == f"test-{counter.name}"
    assert backend._histogram_bucket is None
    assert backend._labels_hash is None
    assert pool.exists(backend._key_name)


def test_create_backend_labeled():
    counter = Counter("name", "desc", required_labels=["bob"])
    counter = counter.labels({"bob": "cat"})
    backend = MultiProcessRedisBackend({}, counter)

    assert backend._key_name == counter.name
    assert backend._histogram_bucket is None
    assert backend._labels_hash == '{"bob": "cat"}'
    assert pool.hexists(backend._key_name, backend._labels_hash)


def test_create_backend_labeled_with_prefix():
    counter = Counter("name", "desc", required_labels=["bob"])
    counter = counter.labels({"bob": "cat"})
    backend = MultiProcessRedisBackend({"key_prefix": "test"}, counter)

    assert backend._key_name == f"test-{counter.name}"
    assert backend._histogram_bucket is None
    assert backend._labels_hash == '{"bob": "cat"}'
    assert pool.hexists(backend._key_name, backend._labels_hash)


def test_create_backend_labeled_with_default():
    counter = Counter("name", "desc", required_labels=["bob"], default_labels={"bob": "cat"})
    backend = MultiProcessRedisBackend({}, counter)

    assert backend._key_name == counter.name
    assert backend._histogram_bucket is None
    assert backend._labels_hash == '{"bob": "cat"}'
    assert pool.hexists(backend._key_name, backend._labels_hash)


def test_create_backend_labeled_with_default_mixed():
    counter = Counter(
        "name", "desc", required_labels=["bob", "bobby"], default_labels={"bob": "cat"}
    )
    counter = counter.labels({"bobby": "fish"})
    backend = MultiProcessRedisBackend({}, counter)

    assert backend._key_name == counter.name
    assert backend._histogram_bucket is None
    assert backend._labels_hash == '{"bob": "cat", "bobby": "fish"}'
    assert pool.hexists(backend._key_name, backend._labels_hash)


def test_create_backend_with_histogram_bucket():
    histogram_bucket = "+Inf"
    counter = Counter("name", "desc")
    backend = MultiProcessRedisBackend({}, counter, histogram_bucket=histogram_bucket)

    assert backend._key_name == f"{counter.name}:{histogram_bucket}"
    assert backend._histogram_bucket == histogram_bucket
    assert backend._labels_hash is None
    assert pool.exists(f"{counter.name}:{histogram_bucket}")


@mock.patch.object(MultiProcessRedisBackend, "_initialize")
def test_create_histogram_with_prefix(_mock_initialize):
    load_backend(MultiProcessRedisBackend, {"key_prefix": "test"})

    Histogram("histogram", "description")

    histogram_keys = pool.keys()
    assert len(histogram_keys) == 14
    for key in histogram_keys:
        assert key.startswith("test-")


# multiple metrics with same name tests, especially when sharing redis as a backend


def test_multiple_metrics_with_same_name_with_redis_overlap():
    """
    If sharing the same database, single value metrics will be overlapping.
    """
    first_collector = CollectorRegistry()
    second_collector = CollectorRegistry()

    counter_a = Counter("shared_name", "description", registry=first_collector)
    counter_b = Counter("shared_name", "description", registry=second_collector)

    counter_a.inc()

    assert counter_a._metric_value_backend.get() == 1.0
    assert counter_b._metric_value_backend.get() == 1.0


def test_multiple_metrics_with_same_name_labeled_with_redis_do_not_overlap():
    """
    Even while sharing the same database, labeled metrics won't be returned from collectors not
    having the specific child instance.
    """
    first_collector = CollectorRegistry()
    second_collector = CollectorRegistry()

    counter_a = Counter(
        "shared_name", "description", required_labels=["bob"], registry=first_collector
    )
    counter_b = Counter(
        "shared_name", "description", required_labels=["bob"], registry=second_collector
    )

    counter_a.labels({"bob": "cat"})
    counter_b.labels({"bob": "bobby"})

    first_collector_metrics_count = len(list(first_collector.collect().__next__().collect()))
    second_collector_metrics_count = len(list(second_collector.collect().__next__().collect()))

    assert first_collector_metrics_count == 1
    assert second_collector_metrics_count == 1


def test_multiple_metrics_with_same_name_labeled_with_redis_do_overlap_on_shared_child():
    """
    If sharing the same database, labeled metrics will be returned from collectors if having the
    same child instance.
    """
    first_collector = CollectorRegistry()
    second_collector = CollectorRegistry()

    counter_a = Counter(
        "shared_name", "description", required_labels=["bob"], registry=first_collector
    )
    counter_b = Counter(
        "shared_name", "description", required_labels=["bob"], registry=second_collector
    )

    counter_a.labels({"bob": "cat"})
    counter_b.labels({"bob": "bobby"})
    counter_b.labels({"bob": "cat"}).inc()

    first_collector_metrics_count = len(list(first_collector.collect().__next__().collect()))
    second_collector_metrics_count = len(list(second_collector.collect().__next__().collect()))

    assert first_collector_metrics_count == 1
    assert second_collector_metrics_count == 2
    assert counter_a.labels({"bob": "cat"})._metric_value_backend.get() == 1
    assert counter_b.labels({"bob": "cat"})._metric_value_backend.get() == 1


def test_multiple_metrics_with_same_name_with_redis_key_prefix():
    first_collector = CollectorRegistry()
    second_collector = CollectorRegistry()

    load_backend(MultiProcessRedisBackend, {"key_prefix": "a"})
    counter_a = Counter("shared_name", "description", registry=first_collector)
    load_backend(MultiProcessRedisBackend, {"key_prefix": "b"})
    counter_b = Counter("shared_name", "description", registry=second_collector)

    counter_a.inc()

    assert counter_a._metric_value_backend.get() == 1.0
    assert counter_b._metric_value_backend.get() == 0


def test_multiple_metrics_with_same_name_labeled_with_redis_key_name_dont_overlap_on_shared_child():
    first_collector = CollectorRegistry()
    second_collector = CollectorRegistry()

    load_backend(MultiProcessRedisBackend, {"key_prefix": "a"})
    counter_a = Counter(
        "shared_name", "description", required_labels=["bob"], registry=first_collector
    )
    counter_a.labels({"bob": "cat"})
    load_backend(MultiProcessRedisBackend, {"key_prefix": "b"})
    counter_b = Counter(
        "shared_name", "description", required_labels=["bob"], registry=second_collector
    )

    counter_b.labels({"bob": "bobby"})
    counter_b.labels({"bob": "cat"}).inc()

    first_collector_metrics_count = len(list(first_collector.collect().__next__().collect()))
    second_collector_metrics_count = len(list(second_collector.collect().__next__().collect()))

    assert first_collector_metrics_count == 1
    assert second_collector_metrics_count == 2
    assert counter_a.labels({"bob": "cat"})._metric_value_backend.get() == 0
    assert counter_b.labels({"bob": "cat"})._metric_value_backend.get() == 1


@mock.patch("pytheus.backends.redis.pipeline_var")
def test_initialize_pipeline(pipeline_var_mock):
    pipeline_var_mock.get.return_value = None
    MultiProcessRedisBackend._initialize_pipeline()
    assert pipeline_var_mock.set.called
    assert pipeline_var_mock.set.call_args[0][0] is not None


@mock.patch("pytheus.backends.redis.pipeline_var")
def test_execute_and_cleanup_pipeline(pipeline_var_mock):
    pipeline_mock = mock.Mock()
    pipeline_var_mock.get.return_value = pipeline_mock
    MultiProcessRedisBackend._execute_and_cleanup_pipeline()
    assert pipeline_var_mock.set.called
    assert pipeline_var_mock.set.call_args[0][0] is None
    assert pipeline_mock.execute.called


def test_generate_samples():
    registry = CollectorRegistry()
    counter = Counter("name", "desc", registry=registry)
    histogram = Histogram("histogram", "desc", registry=registry)
    samples = MultiProcessRedisBackend._generate_samples(registry)
    assert len(samples[counter._collector]) == 1
    assert len(samples[histogram._collector]) == 14


def test_generate_samples_with_labels():
    load_backend(MultiProcessRedisBackend)
    registry = CollectorRegistry()
    counter = Counter(
        "name", "desc", required_labels=["bob"], default_labels={"bob": "c"}, registry=registry
    )
    counter.labels({"bob": "a"})
    counter.labels({"bob": "b"})
    samples = MultiProcessRedisBackend._generate_samples(registry)
    assert len(samples[counter._collector]) == 3


def _run_multiprocess(extra_label):
    load_backend(
        backend_class=MultiProcessRedisBackend,
        # backend_config={"host": "127.0.0.1", "port": 6379},
    )
    registry = CollectorRegistry()
    counter = Counter("name_multiple", "desc", required_labels=["bob"], registry=registry)
    counter.labels(bob="cat")
    if extra_label:
        counter.labels(bob="created_only_on_one").inc(3.0)
    return generate_metrics(registry)


def test_multiple_return_all_metrics_entries():
    """
    Test that if a metric labeled child is created on a process, it will be retrieved even if the
    instance doesn't exist on a different process.
    """
    with ProcessPoolExecutor() as executor:
        first_result = executor.submit(_run_multiprocess, extra_label=True)
        first_result = first_result.result()
        second_result = executor.submit(_run_multiprocess, extra_label=False)
        second_result = second_result.result()

        assert first_result == second_result


def test_sets_key_on_collector():
    counter = Counter("name", "desc")
    MultiProcessRedisBackend({}, counter)
    assert counter._collector._redis_key_name == "name"


class TestGenerateSamples:
    def test_counter(self):
        registry = CollectorRegistry()
        counter = Counter("counter", "desc", registry=registry)
        expected_samples = {counter._collector: [Sample("", None, 0.0)]}

        samples = MultiProcessRedisBackend._generate_samples(registry)
        assert samples == expected_samples

    def test_counter_labeled(self):
        registry = CollectorRegistry()
        counter = Counter("counter", "desc", required_labels=["bob"], registry=registry)
        counter.labels(bob="cat").inc(2.7)
        expected_samples = {counter._collector: [Sample("", {"bob": "cat"}, 2.7)]}

        samples = MultiProcessRedisBackend._generate_samples(registry)
        assert samples == expected_samples

    def test_gauge(self):
        registry = CollectorRegistry()
        gauge = Gauge("gauge", "desc", registry=registry)
        expected_samples = {gauge._collector: [Sample("", None, 0.0)]}

        samples = MultiProcessRedisBackend._generate_samples(registry)
        assert samples == expected_samples

    def test_gauge_labeled(self):
        registry = CollectorRegistry()
        gauge = Gauge("gauge", "desc", required_labels=["bob"], registry=registry)
        gauge.labels(bob="cat").inc(2.7)
        expected_samples = {gauge._collector: [Sample("", {"bob": "cat"}, 2.7)]}

        samples = MultiProcessRedisBackend._generate_samples(registry)
        assert samples == expected_samples

    def test_metric_labeled_multiple(self):
        registry = CollectorRegistry()
        counter_labeled = Counter(
            "counter_labeled", "desc", required_labels=["bob"], registry=registry
        )
        counter_labeled.labels(bob="cat").inc(2.7)
        gauge = Gauge("gauge", "desc", required_labels=["bob"], registry=registry)
        gauge.labels(bob="gage").inc(3.0)
        gauge.labels(bob="blob").inc(3.2)
        counter = Counter("counter", "desc", registry=registry)
        expected_samples = {
            counter_labeled._collector: [Sample("", {"bob": "cat"}, 2.7)],
            gauge._collector: [Sample("", {"bob": "gage"}, 3.0), Sample("", {"bob": "blob"}, 3.2)],
            counter._collector: [Sample("", None, 0.0)],
        }

        samples = MultiProcessRedisBackend._generate_samples(registry)
        assert samples == expected_samples

    def test_summary(self):
        registry = CollectorRegistry()
        summary = Summary("summary", "desc", registry=registry)
        expected_samples = {
            summary._collector: [Sample("_count", None, 0.0), Sample("_sum", None, 0.0)],
        }

        samples = MultiProcessRedisBackend._generate_samples(registry)
        assert samples == expected_samples

    def test_summary_labeled(self):
        registry = CollectorRegistry()
        summary = Summary(
            "summary",
            "desc",
            registry=registry,
            required_labels=["bob"],
            default_labels={"bob": "cat"},
        )
        summary.observe(7)
        expected_samples = {
            summary._collector: [
                Sample("_count", {"bob": "cat"}, 1.0),
                Sample("_sum", {"bob": "cat"}, 7.0),
            ],
        }

        samples = MultiProcessRedisBackend._generate_samples(registry)
        assert samples == expected_samples

    def test_histogram(self):
        registry = CollectorRegistry()
        histogram = Histogram("histogram", "desc", buckets=[1, 2, 3], registry=registry)
        histogram.observe(2.7)
        expected_samples = {
            histogram._collector: [
                Sample("_bucket", {"le": "1"}, 0.0),
                Sample("_bucket", {"le": "2"}, 0.0),
                Sample("_bucket", {"le": "3"}, 1.0),
                Sample("_bucket", {"le": "+Inf"}, 1.0),
                Sample("_count", None, 1.0),
                Sample("_sum", None, 2.7),
            ],
        }

        samples = MultiProcessRedisBackend._generate_samples(registry)
        assert samples == expected_samples

    def test_histogram_labeled(self):
        registry = CollectorRegistry()
        histogram = Histogram(
            "histogram", "desc", buckets=[1, 2, 3], required_labels=["bob"], registry=registry
        )
        histogram.labels(bob="cat").observe(2.7)
        expected_samples = {
            histogram._collector: [
                Sample("_bucket", {"bob": "cat", "le": "1"}, 0.0),
                Sample("_bucket", {"bob": "cat", "le": "2"}, 0.0),
                Sample("_bucket", {"bob": "cat", "le": "3"}, 1.0),
                Sample("_bucket", {"bob": "cat", "le": "+Inf"}, 1.0),
                Sample("_count", {"bob": "cat"}, 1.0),
                Sample("_sum", {"bob": "cat"}, 2.7),
            ],
        }

        samples = MultiProcessRedisBackend._generate_samples(registry)
        assert samples == expected_samples


# reset to the SingleProcessBackend for other tests
load_backend(SingleProcessBackend)
