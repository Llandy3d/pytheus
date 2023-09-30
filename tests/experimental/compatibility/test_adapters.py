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


class TestCounter:
    @pytest.fixture
    def counter(self, set_empty_registry):
        return prometheus_client.Counter("name", "desc")

    def test_inc(self, counter):
        counter.inc(3)
        assert counter._pytheus_metric._metric_value_backend.get() == 3

    def test_exception_decorator(self, counter):
        @counter.count_exceptions()
        def test():
            raise ValueError

        try:
            test()
        except Exception:
            pass

        assert counter._pytheus_metric._metric_value_backend.get() == 1

    def test_exception_contextmanager(self, counter):
        try:
            with counter.count_exceptions():
                raise ValueError
        except Exception:
            pass

        assert counter._pytheus_metric._metric_value_backend.get() == 1

    def test_exception_with_specified(self, counter):
        for exception in [ValueError, KeyError]:
            try:
                with counter.count_exceptions(ValueError):
                    raise exception
            except Exception:
                pass

        assert counter._pytheus_metric._metric_value_backend.get() == 1


class TestGauge:
    @pytest.fixture
    def gauge(self, set_empty_registry):
        return prometheus_client.Gauge("name", "desc")

    def test_inc(self, gauge):
        gauge.inc(3)
        assert gauge._pytheus_metric._metric_value_backend.get() == 3

    def test_dec(self, gauge):
        gauge.dec(3)
        assert gauge._pytheus_metric._metric_value_backend.get() == -3

    def test_set(self, gauge):
        gauge.inc(3)
        gauge.set(2)
        assert gauge._pytheus_metric._metric_value_backend.get() == 2

    def test_track_inprogress_decorator(self, gauge):
        @gauge.track_inprogress()
        def test():
            assert gauge._pytheus_metric._metric_value_backend.get() == 1

            test()

        assert gauge._pytheus_metric._metric_value_backend.get() == 0

    def test_track_inprogress_contextmanager(self, gauge):
        with gauge.track_inprogress():
            assert gauge._pytheus_metric._metric_value_backend.get() == 1

        assert gauge._pytheus_metric._metric_value_backend.get() == 0

    def test_time_decorator(self, gauge):
        @gauge.time()
        def test():
            pass

        test()

        assert gauge._pytheus_metric._metric_value_backend.get() != 0

    def test_time_contextmanager(self, gauge):
        with gauge.time():
            pass

        assert gauge._pytheus_metric._metric_value_backend.get() != 0
