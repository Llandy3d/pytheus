import json
import os
from logging import getLogger
from threading import Lock
from typing import Iterable, Protocol, runtime_checkable

from pytheus.exceptions import (
    InvalidRegistryClassException,
    InvalidRegistryConfigException,
)
from pytheus.utils import import_object_from_path

logger = getLogger(__name__)

@runtime_checkable
class Collector(Protocol):
    name: str
    description: str

    def collect(self) -> Iterable:
        ...

    @property
    def type_(self) -> str:
        ...

@runtime_checkable
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


REGISTRY_CLASS_ENV: str = "PYTHEUS_REGISTRY_CLASS"
REGISTRY_CONFIG_ENV: str = "PYTHEUS_REGISTRY_CONFIG"

def _default_registry():
    registry_cls = CollectorRegistry
    registry_config = {}
    if REGISTRY_CLASS_ENV in os.environ:
        class_path = os.environ[REGISTRY_CLASS_ENV]
        try:
            registry_cls = import_object_from_path(class_path)
        except (ValueError, ImportError, AttributeError):
            raise InvalidRegistryClassException(f"{class_path}: path invalid or does not exist")
        # TODO check issubclass of Registry protocol
    if REGISTRY_CONFIG_ENV in os.environ:
        try:
            registry_config = json.loads(os.environ[REGISTRY_CONFIG_ENV])
        except json.JSONDecodeError:
            raise InvalidRegistryConfigException("expected json data")
    return registry_cls(**registry_config)

REGISTRY = _default_registry()
