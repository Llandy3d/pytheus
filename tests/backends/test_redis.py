import pytest
from fakeredis import FakeStrictRedis

from pytheus.backends.redis import MultiProcessRedisBackend
from pytheus.metrics import Counter

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


def test_create_backend_labeled():
    counter = Counter("name", "desc", required_labels=["bob"])
    counter = counter.labels({"bob": "cat"})
    backend = MultiProcessRedisBackend({}, counter)

    assert backend._key_name == counter.name
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
