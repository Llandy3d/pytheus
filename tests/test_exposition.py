import pytest

from pytheus.exposition import generate_metrics
from pytheus.metrics import Counter
from pytheus.registry import REGISTRY, CollectorRegistry


class TestExposition:

    def setup_counters(self):
        c = Counter("http_req_total", "metric desc", required_labels=["p", "m"])
        c.labels({"p": "p1", "m": "m1"}).inc(3)
        c.labels({"p": "p2", "m": "m2"}).inc(1)
        c = Counter("cache_hits_total", "cache desc", required_labels=["name"])
        c.labels({"name": "redis"}).inc(5)
        c = Counter("exception_total", "expection desc")
        c.inc(4)

    def test_generate_metrics(self):
        self.setup_counters()
        metrics_text = generate_metrics()
        assert metrics_text == (
            '# HELP http_req_total metric desc\n'
            '# TYPE http_req_total counter\n'
            'http_req_total{p="p1",m="m1"} 3.0\n'
            'http_req_total{p="p2",m="m2"} 1.0\n'
            '# HELP cache_hits_total cache desc\n'
            '# TYPE cache_hits_total counter\n'
            'cache_hits_total{name="redis"} 5.0\n'
            '# HELP exception_total expection desc\n'
            '# TYPE exception_total counter\n'
            'exception_total 4.0\n'
            ''
        )

    def test_generate_metrics_with_prefix(self):
        registry = CollectorRegistry(prefix="testing")
        REGISTRY.set_registry(registry)
        self.setup_counters()
        metrics_text = generate_metrics()
        assert metrics_text == (
            '# HELP testing_http_req_total metric desc\n'
            '# TYPE testing_http_req_total counter\n'
            'testing_http_req_total{p="p1",m="m1"} 3.0\n'
            'testing_http_req_total{p="p2",m="m2"} 1.0\n'
            '# HELP testing_cache_hits_total cache desc\n'
            '# TYPE testing_cache_hits_total counter\n'
            'testing_cache_hits_total{name="redis"} 5.0\n'
            '# HELP testing_exception_total expection desc\n'
            '# TYPE testing_exception_total counter\n'
            'testing_exception_total 4.0\n'
            ''
        )
