from pytheus.metrics import Counter, Histogram, _Metric
from pytheus.registry import CollectorRegistry


class TestCollectorRegistry:
    def test_can_create_collector_registry(self):
        CollectorRegistry()

    def test_can_create_collector_registry_with_prefix(self):
        prefix = "myprefix"
        registry = CollectorRegistry(prefix=prefix)
        assert registry.prefix == prefix

    def test_register_metric(self):
        registry = CollectorRegistry()
        metric = _Metric("name", "desc", registry=None)
        registry.register(metric)

        assert metric.name in registry._collectors
        assert registry._collectors[metric.name] is metric._collector

    def test_register_metric_duplicate_name_is_ignored(self):
        registry = CollectorRegistry()
        metric_first = _Metric("name", "desc", registry=None)
        metric_second = _Metric("name", "desc", registry=None)
        registry.register(metric_first)
        registry.register(metric_second)

        assert metric_first is not metric_second
        assert registry._collectors[metric_first.name] is metric_first._collector

    def test_unregister_metric(self):
        registry = CollectorRegistry()
        metric = _Metric("name", "desc", registry=None)
        registry.register(metric)
        registry.unregister(metric)

        assert metric.name not in registry._collectors

    def test_collect(self):
        registry = CollectorRegistry()
        metric = Counter("name", "desc", registry=None)
        registry.register(metric)

        collectors = registry.collect()
        collectors = list(collectors)

        assert len(collectors) == 1

    def test_collect_with_multiple_metrics(self):
        registry = CollectorRegistry()
        counter = Counter("counter", "desc", registry=None)
        histogram = Histogram("histogram", "desc", registry=None)
        registry.register(counter)
        registry.register(histogram)

        collectors = registry.collect()
        collectors = list(collectors)

        assert len(collectors) == 2

    def test_collect_with_labeled_metrics(self):
        registry = CollectorRegistry()
        counter = Counter("name", "desc", required_labels=["bob", "cat"], registry=None)
        counter.labels({"bob": "2", "cat": "3"})
        registry.register(counter)

        collectors = registry.collect()
        collectors = list(collectors)

        assert len(collectors) == 1
        assert len(list(collectors[0].collect())) == 1

    def test_collect_with_labeled_metrics_unobservable(self):
        registry = CollectorRegistry()
        counter = Counter("name", "desc", required_labels=["bob", "cat"], registry=None)
        registry.register(counter)

        collectors = registry.collect()
        collectors = list(collectors)

        assert len(collectors) == 1
        assert len(list(collectors[0].collect())) == 0
