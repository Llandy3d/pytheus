import os

from pytheus.exposition import generate_metrics
from pytheus.metrics import create_counter
from pytheus import registry
from pytheus.registry import REGISTRY_CONFIG_ENV, _default_registry


class TestExposition:

    def setup_counters(self):
        registry.REGISTRY._collectors = {}
        c = create_counter("http_req", "metric desc", required_labels=["p", "m"])
        c.labels({"p": "p1", "m": "m1"}).inc(3)
        c.labels({"p": "p2", "m": "m2"}).inc(1)
        c = create_counter("cache_hits", "cache desc", required_labels=["name"])
        c.labels({"name": "redis"}).inc(5)
        c = create_counter("exception", "expection desc")
        c.inc(4)

    def test_generate_metrics(self):
        self.setup_counters()
        metrics_text = generate_metrics()
        assert metrics_text == (
            '# HELP http_req metric desc\n'
            '# TYPE http_req counter\n'
            'http_req_total{p="p1",m="m1"} 3.0\n'
            'http_req_total{p="p2",m="m2"} 1.0\n'
            '# HELP cache_hits cache desc\n'
            '# TYPE cache_hits counter\n'
            'cache_hits_total{name="redis"} 5.0\n'
            '# HELP exception expection desc\n'
            '# TYPE exception counter\n'
            'exception_total 4.0\n'
            ''
        )

    def test_generate_metrics_with_prefix(self):
        os.environ[REGISTRY_CONFIG_ENV] = '{"prefix":"testing"}'
        registry.REGISTRY = _default_registry()
        self.setup_counters()
        metrics_text = generate_metrics()
        assert metrics_text == (
            '# HELP testing_http_req metric desc\n'
            '# TYPE testing_http_req counter\n'
            'testing_http_req_total{p="p1",m="m1"} 3.0\n'
            'testing_http_req_total{p="p2",m="m2"} 1.0\n'
            '# HELP testing_cache_hits cache desc\n'
            '# TYPE testing_cache_hits counter\n'
            'testing_cache_hits_total{name="redis"} 5.0\n'
            '# HELP testing_exception expection desc\n'
            '# TYPE testing_exception counter\n'
            'testing_exception_total 4.0\n'
            ''
        )
