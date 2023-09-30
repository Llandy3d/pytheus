import prometheus_client
import pytest

from pytheus.backends.base import load_backend
from pytheus.experimental.adapters import HistogramAdapter, _build_name
from pytheus.experimental.compatibility import patch_client
from pytheus.registry import REGISTRY, CollectorRegistry

# patching without the fixture D=
patch_client(prometheus_client)


@pytest.fixture
def set_empty_registry():
    """
    As the REGISTRY object is global by default, we might have data from other tests.
    So with this fixture we just set a new empty one.
    """
    REGISTRY.set_registry(CollectorRegistry())


@pytest.mark.parametrize(
    "name,namespace,subsystem,expected",
    [
        ("bob", "", "", "bob"),
        ("bob", "namespace", "", "namespace_bob"),
        ("bob", "namespace", "subsystem", "namespace_subsystem_bob"),
        ("bob", "", "subsystem", "subsystem_bob"),
    ],
)
def test_build_name_with_name(name, namespace, subsystem, expected):
    assert _build_name(name, namespace, subsystem) == expected


class TestHistogram:
    @pytest.fixture
    def histogram(self, set_empty_registry):
        load_backend()  # test issues :(
        return prometheus_client.Histogram("name", "desc")

    def test_creation(self, histogram):
        assert isinstance(histogram, HistogramAdapter)
        assert histogram._pytheus_metric.name == "name"
        assert histogram._pytheus_metric.description == "desc"

    def test_observe(self, histogram):
        histogram.observe(7.7)
        assert histogram._pytheus_metric._sum.get() == 7.7

    def test_labels(self):
        histogram = prometheus_client.Histogram("name", "desc", labelnames=["one", "two"])
        child_args = histogram.labels("hello", "world")
        child_kwargs = histogram.labels(one="bob", two="cat")

        child_args.observe(2)
        child_kwargs.observe(3)

        assert child_args._pytheus_metric._sum.get() == 2
        assert child_kwargs._pytheus_metric._sum.get() == 3

    def test_instantiating_multiple_childs(self):
        histogram = prometheus_client.Histogram("name", "desc", labelnames=["one", "two"])
        child_one = histogram.labels(one="hello", two="world")
        child_two = histogram.labels(one="hello", two="world")

        assert child_one._pytheus_metric is child_two._pytheus_metric

    def test_time_decorator(self, histogram):
        @histogram.time()
        def test():
            pass

        test()

        assert histogram._pytheus_metric._sum.get() != 0

    def test_time_contextmanager(self, histogram):
        with histogram.time():
            pass

        assert histogram._pytheus_metric._sum.get() != 0
