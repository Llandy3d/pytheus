from logging import getLogger
from threading import Lock
from typing import Iterable, Protocol

from pytheus.utils import MetricType

logger = getLogger(__name__)


class Collector(Protocol):
    name: str
    description: str
    type_: MetricType

    def collect(self) -> Iterable:
        ...


class Registry(Protocol):
    prefix: str | None

    def register(self, collector: Collector) -> None:
        ...

    def unregister(self, collector: Collector) -> None:
        ...

    def collect(self) -> Iterable:
        ...


class CollectorRegistry:
    def __init__(self, prefix: str | None = None) -> None:
        self._lock = Lock()
        self.prefix = prefix
        self._collectors: dict[str, Collector] = {}

    def register(self, collector: Collector) -> None:
        with self._lock:
            if collector.name in self._collectors:
                logger.warning(
                    f"collector with name '{collector.name}' already registered."
                    " Keeping previous entry"
                )
                return
            # if it has not this field it's a custom collector, I do not like this approach but
            # let's get it working
            if not hasattr(collector, "type_"):
                for _collector in collector.collect():
                    if _collector.name in self._collectors:
                        logger.warning(
                            f"CustomCollector: {collector.name} - collector with name"
                            f" '{_collector.name}' already registered. Ignoring custom collector"
                        )
                        return

            # NOTE: in case the user is adding directly a metric to the registry
            # we need to add the _MetricCollector to the registry. There might be a better way
            # to d this but it should work for now.
            if hasattr(collector, "_collector"):
                collector = collector._collector
            self._collectors[collector.name] = collector

    def unregister(self, collector: Collector) -> None:
        with self._lock:
            if collector.name not in self._collectors:
                logger.warning(f"no collector found with name '{collector.name}'")
                return
            del self._collectors[collector.name]

    def collect(self) -> Iterable[Collector]:
        yield from self._collectors.values()


class CollectorRegistryProxy:
    def __init__(self, registry: Registry | None = None) -> None:
        self._registry = registry or CollectorRegistry()
        self.prefix = self._registry.prefix

    def set_registry(self, registry: Registry) -> None:
        self._registry = registry
        self.prefix = self._registry.prefix

    def register(self, collector: Collector) -> None:
        self._registry.register(collector)

    def unregister(self, collector: Collector) -> None:
        self._registry.unregister(collector)

    def collect(self) -> Iterable:
        return self._registry.collect()


REGISTRY = CollectorRegistryProxy()
