from unittest import mock

import pytest
from fakeredis import FakeStrictRedis

from pytheus.backends import load_backend
from pytheus.backends.redis import MultiProcessRedisBackend
from pytheus.metrics import Counter, Histogram
from pytheus.registry import CollectorRegistry

# patch with fakeredis for tests
pool = FakeStrictRedis()
MultiProcessRedisBackend.CONNECTION_POOL = pool


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
                "name",
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
    assert backend._labels_hash == "cat"
    assert pool.hexists(backend._key_name, backend._labels_hash)


def test_create_backend_labeled_with_prefix():
    counter = Counter("name", "desc", required_labels=["bob"])
    counter = counter.labels({"bob": "cat"})
    backend = MultiProcessRedisBackend({"key_prefix": "test"}, counter)

    assert backend._key_name == f"test-{counter.name}"
    assert backend._histogram_bucket is None
    assert backend._labels_hash == "cat"
    assert pool.hexists(backend._key_name, backend._labels_hash)


def test_create_backend_labeled_with_default():
    counter = Counter("name", "desc", required_labels=["bob"], default_labels={"bob": "cat"})
    backend = MultiProcessRedisBackend({}, counter)

    assert backend._key_name == counter.name
    assert backend._histogram_bucket is None
    assert backend._labels_hash == "cat"
    assert pool.hexists(backend._key_name, backend._labels_hash)


def test_create_backend_labeled_with_default_mixed():
    counter = Counter(
        "name", "desc", required_labels=["bob", "bobby"], default_labels={"bob": "cat"}
    )
    counter = counter.labels({"bobby": "fish"})
    backend = MultiProcessRedisBackend({}, counter)

    assert backend._key_name == counter.name
    assert backend._histogram_bucket is None
    assert backend._labels_hash == "cat-fish"
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
        assert key.startswith(b"test-")


# multiple metrics with same name tests, especially when sharing redis as a backend


@mock.patch.object(MultiProcessRedisBackend, "_initialize")
def test_multiple_metrics_with_same_name_with_redis_overlap(_mock_initialize):
    """
    If sharing the same database, single value metrics will be overlapping.
    """
    load_backend(MultiProcessRedisBackend)
    first_collector = CollectorRegistry()
    second_collector = CollectorRegistry()

    counter_a = Counter("shared_name", "description", registry=first_collector)
    counter_b = Counter("shared_name", "description", registry=second_collector)

    counter_a.inc()

    assert counter_a._metric_value_backend.get() == 1.0
    assert counter_b._metric_value_backend.get() == 1.0


@mock.patch.object(MultiProcessRedisBackend, "_initialize")
def test_multiple_metrics_with_same_name_labeled_with_redis_do_not_overlap(_mock_initialize):
    """
    Even while sharing the same database, labeled metrics won't be returned from collectors not
    having the specific child instance.
    """
    load_backend(MultiProcessRedisBackend)
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


@mock.patch.object(MultiProcessRedisBackend, "_initialize")
def test_multiple_metrics_with_same_name_labeled_with_redis_do_overlap_on_shared_child(
    _mock_initialize,
):
    """
    If sharing the same database, labeled metrics will be returned from collectors if having the
    same child instance.
    """
    load_backend(MultiProcessRedisBackend)
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


@mock.patch.object(MultiProcessRedisBackend, "_initialize")
def test_multiple_metrics_with_same_name_with_redis_key_prefix(_mock_initialize):
    first_collector = CollectorRegistry()
    second_collector = CollectorRegistry()

    load_backend(MultiProcessRedisBackend, {"key_prefix": "a"})
    counter_a = Counter("shared_name", "description", registry=first_collector)
    load_backend(MultiProcessRedisBackend, {"key_prefix": "b"})
    counter_b = Counter("shared_name", "description", registry=second_collector)

    counter_a.inc()

    assert counter_a._metric_value_backend.get() == 1.0
    assert counter_b._metric_value_backend.get() == 0


@mock.patch.object(MultiProcessRedisBackend, "_initialize")
def test_multiple_metrics_with_same_name_labeled_with_redis_key_name_do_not_overlap_on_shared_child(
    _mock_initialize,
):
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
