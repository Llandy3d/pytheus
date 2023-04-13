from pytheus.exposition import generate_metrics
from pytheus.metrics import Counter, Histogram
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
            "# HELP http_req_total metric desc\n"
            "# TYPE http_req_total counter\n"
            'http_req_total{p="p1",m="m1"} 3.0\n'
            'http_req_total{p="p2",m="m2"} 1.0\n'
            "# HELP cache_hits_total cache desc\n"
            "# TYPE cache_hits_total counter\n"
            'cache_hits_total{name="redis"} 5.0\n'
            "# HELP exception_total expection desc\n"
            "# TYPE exception_total counter\n"
            "exception_total 4.0\n"
            ""
        )

    def test_generate_metrics_with_prefix(self):
        registry = CollectorRegistry(prefix="testing")
        REGISTRY.set_registry(registry)
        self.setup_counters()
        metrics_text = generate_metrics()
        assert metrics_text == (
            "# HELP testing_http_req_total metric desc\n"
            "# TYPE testing_http_req_total counter\n"
            'testing_http_req_total{p="p1",m="m1"} 3.0\n'
            'testing_http_req_total{p="p2",m="m2"} 1.0\n'
            "# HELP testing_cache_hits_total cache desc\n"
            "# TYPE testing_cache_hits_total counter\n"
            'testing_cache_hits_total{name="redis"} 5.0\n'
            "# HELP testing_exception_total expection desc\n"
            "# TYPE testing_exception_total counter\n"
            "testing_exception_total 4.0\n"
            ""
        )

    def test_generate_metrics_histogram(self):
        registry = CollectorRegistry()
        REGISTRY.set_registry(registry)

        histogram = Histogram("hello", "world")
        histogram.observe(0.4)
        metrics_text = generate_metrics()
        assert metrics_text == (
            '# HELP hello world\n# TYPE hello histogram\nhello_bucket{le="0.005"} 0.0\nhello_bucket{le="0.01"} 0.0\nhello_bucket{le="0.025"} 0.0\nhello_bucket{le="0.05"} 0.0\nhello_bucket{le="0.1"} 0.0\nhello_bucket{le="0.25"} 0.0\nhello_bucket{le="0.5"} 1.0\nhello_bucket{le="1"} 1.0\nhello_bucket{le="2.5"} 1.0\nhello_bucket{le="5"} 1.0\nhello_bucket{le="10"} 1.0\nhello_bucket{le="+Inf"} 1.0\nhello_sum 0.4\nhello_count 1.0\n'
        )

    def test_generate_metrics_histogram_with_labels(self):
        registry = CollectorRegistry()
        REGISTRY.set_registry(registry)

        histogram = Histogram("hello", "world", required_labels=["bob"])
        histogram_a = histogram.labels({"bob": "a"})
        histogram_b = histogram.labels({"bob": "b"})
        histogram_a.observe(0.4)
        histogram_b.observe(7)
        metrics_text = generate_metrics()
        assert metrics_text == (
            '# HELP hello world\n# TYPE hello histogram\nhello_bucket{bob="a",le="0.005"} 0.0\nhello_bucket{bob="a",le="0.01"} 0.0\nhello_bucket{bob="a",le="0.025"} 0.0\nhello_bucket{bob="a",le="0.05"} 0.0\nhello_bucket{bob="a",le="0.1"} 0.0\nhello_bucket{bob="a",le="0.25"} 0.0\nhello_bucket{bob="a",le="0.5"} 1.0\nhello_bucket{bob="a",le="1"} 1.0\nhello_bucket{bob="a",le="2.5"} 1.0\nhello_bucket{bob="a",le="5"} 1.0\nhello_bucket{bob="a",le="10"} 1.0\nhello_bucket{bob="a",le="+Inf"} 1.0\nhello_sum{bob="a"} 0.4\nhello_count{bob="a"} 1.0\nhello_bucket{bob="b",le="0.005"} 0.0\nhello_bucket{bob="b",le="0.01"} 0.0\nhello_bucket{bob="b",le="0.025"} 0.0\nhello_bucket{bob="b",le="0.05"} 0.0\nhello_bucket{bob="b",le="0.1"} 0.0\nhello_bucket{bob="b",le="0.25"} 0.0\nhello_bucket{bob="b",le="0.5"} 0.0\nhello_bucket{bob="b",le="1"} 0.0\nhello_bucket{bob="b",le="2.5"} 0.0\nhello_bucket{bob="b",le="5"} 0.0\nhello_bucket{bob="b",le="10"} 1.0\nhello_bucket{bob="b",le="+Inf"} 1.0\nhello_sum{bob="b"} 7.0\nhello_count{bob="b"} 1.0\n'
        )

    def test_generate_metrics_histogram_with_labels_and_default_labels(self):
        registry = CollectorRegistry()
        REGISTRY.set_registry(registry)

        histogram = Histogram(
            "hello", "world", required_labels=["bob"], default_labels={"bob": "default"}
        )
        histogram = histogram.labels({"bob": "a"})
        histogram.observe(0.4)
        metrics_text = generate_metrics()
        assert metrics_text == (
            '# HELP hello world\n# TYPE hello histogram\nhello_bucket{bob="a",le="0.005"} 0.0\nhello_bucket{bob="a",le="0.01"} 0.0\nhello_bucket{bob="a",le="0.025"} 0.0\nhello_bucket{bob="a",le="0.05"} 0.0\nhello_bucket{bob="a",le="0.1"} 0.0\nhello_bucket{bob="a",le="0.25"} 0.0\nhello_bucket{bob="a",le="0.5"} 1.0\nhello_bucket{bob="a",le="1"} 1.0\nhello_bucket{bob="a",le="2.5"} 1.0\nhello_bucket{bob="a",le="5"} 1.0\nhello_bucket{bob="a",le="10"} 1.0\nhello_bucket{bob="a",le="+Inf"} 1.0\nhello_sum{bob="a"} 0.4\nhello_count{bob="a"} 1.0\nhello_bucket{bob="default",le="0.005"} 0.0\nhello_bucket{bob="default",le="0.01"} 0.0\nhello_bucket{bob="default",le="0.025"} 0.0\nhello_bucket{bob="default",le="0.05"} 0.0\nhello_bucket{bob="default",le="0.1"} 0.0\nhello_bucket{bob="default",le="0.25"} 0.0\nhello_bucket{bob="default",le="0.5"} 0.0\nhello_bucket{bob="default",le="1"} 0.0\nhello_bucket{bob="default",le="2.5"} 0.0\nhello_bucket{bob="default",le="5"} 0.0\nhello_bucket{bob="default",le="10"} 0.0\nhello_bucket{bob="default",le="+Inf"} 0.0\nhello_sum{bob="default"} 0.0\nhello_count{bob="default"} 0.0\n'
        )
