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
