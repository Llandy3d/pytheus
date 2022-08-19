from logging import getLogger
from threading import Lock
from typing import Iterable, Optional, Protocol

logger = getLogger(__name__)


class Collector(Protocol):
    name: str
    description: str

    def collect(self) -> Iterable:
        ...

    @property
    def type_(self) -> str:
        ...


class Registry(Protocol):
    prefix: str | None

    def register(self, collector: Collector):
        ...

    def unregister(self, collector: Collector):
        ...

    def collect(self) -> Iterable:
        ...


class CollectorRegistry:
    def __init__(self, prefix: str = None) -> None:
        self._lock = Lock()
        self.prefix = prefix
        self._collectors: dict[str, Collector] = {}

    def register(self, collector: Collector) -> None:
        with self._lock:
            if collector.name in self._collectors:
                logger.warning(f"collector with name '{collector.name}' already registred")
                return
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
    def __init__(self, registry: Registry = None) -> None:
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
