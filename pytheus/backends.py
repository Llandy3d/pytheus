import importlib
import json
import os

from abc import ABC, abstractmethod
from threading import Lock
from typing import Any, TYPE_CHECKING

import redis

from pytheus.exceptions import InvalidBackendClassException, InvalidBackendConfigException


if TYPE_CHECKING:
    from pytheus.metrics import Metric


BackendConfig = dict[str, Any]


class Backend(ABC):
    def __init__(self, config: BackendConfig, metric: 'Metric') -> None:
        self.metric = metric
        if self.is_valid_config(config):
            self.config = config
        else:
            raise InvalidBackendConfigException(
                f"Configuration object '{config}' is not valid for the backend class "
                f"'{self.__class__}'"
            )

    @abstractmethod
    def is_valid_config(self, config: BackendConfig) -> True:
        return True

    @abstractmethod
    def inc(self, value: float) -> None:
        return None

    @abstractmethod
    def get(self) -> float:
        return 0.0


def _import_backend_class(full_import_path: str) -> Backend:
    try:
        module_path, class_name = full_import_path.rsplit(".", 1)
    except ValueError:  # Empty string or not full path to the class
        raise InvalidBackendClassException(
            "Backend class could not be imported. Full import path needs to be provided, e.g. "
            "my_package.my_module.MyClass"
        )
    try:
        module = importlib.import_module(module_path)
    except ImportError as e:
        raise InvalidBackendClassException(f"Module '{module_path}' could not be imported: {e}")
    try:
        cls = getattr(module, class_name)
        if not issubclass(cls, Backend):
            raise InvalidBackendClassException(f"Class '{class_name}' is not a Backend subclass")
        return cls
    except AttributeError:
        raise InvalidBackendClassException(
            f"Class '{class_name}' could not be found in module '{module_path}'"
        )


def load_backend(
    backend_class: Backend | None = None,
    backend_config: Backend | None = None,
):

    # Load default backend class
    global BACKEND_CLASS
    backend_class_env_var: str = "PYTHEUS_BACKEND_CLASS"
    if backend_class is not None:  # Explicit
        BACKEND_CLASS = backend_class
    elif backend_class_env_var in os.environ:  # Environment
        class_name = os.environ[backend_class_env_var]
        BACKEND_CLASS = _import_backend_class(os.environ[backend_class_env_var])
    else:  # Default
        BACKEND_CLASS = SingleProcessBackend

    # Load default backend config
    global BACKEND_CONFIG
    backend_config_env_var: str = "PYTHEUS_BACKEND_CONFIG"
    if backend_config is not None:  # Explicit
        BACKEND_CONFIG = backend_config
    elif backend_config_env_var in os.environ:  # Environment
        try:
            with open(os.environ[backend_config_env_var]) as f:
                BACKEND_CONFIG = json.loads(f.read())  # TODO: Support yaml?
        except Exception as e:
            raise InvalidBackendConfigException(f"{e.__class__}: {e}")
    else:
        BACKEND_CONFIG = {}  # Default


def get_backend(metric: 'Metric') -> Backend:
    # Probably ok not to cache this and allow each metric to keep its own
    return BACKEND_CLASS(BACKEND_CONFIG, metric)


class SingleProcessBackend(Backend):
    """Provides a single-process backend that uses a thread-safe, in-memory approach."""

    def __init__(self, config: BackendConfig, metric: 'Metric') -> None:
        super().__init__(config, metric)
        self._value = 0.0
        self._lock = Lock()

    def is_valid_config(self, config: BackendConfig) -> True:
        return True

    def inc(self, value: float) -> None:
        with self._lock:
            self._value += value

    def get(self) -> float:
        with self._lock:
            return self._value


class MultipleProcessFileBackend(Backend):
    """Provides a multi-process backend that uses MMAP files."""

    def is_valid_config(self, config: BackendConfig) -> True:
        return True  # TODO

    def inc(self, value: float) -> None:
        pass  # TODO

    def get(self) -> float:
        pass  # TODO


class MultipleProcessRedisBackend(Backend):
    """
    Provides a multi-process backend that uses Redis.
    Single dimension metrics will be stored as list (ex. Counter) while labelled
    metrics will be stored in an hash.
    Currently is very naive, and there is a lot of room for improvement.
    (ex. maybe store all dimensions in the same hash and be smart on retrieving everything...)
    Note: currently not expiring keys
    """

    CONNECTION_POOL: redis.Redis = None

    def __init__(self, config: BackendConfig, metric: 'Metric') -> None:
        super().__init__(config, metric)
        self._key_name = self.metric._collector.name
        self._labels_hash = None
        if self.metric._labels:
            self._labels_hash = '-'.join(sorted(self.metric._labels.values()))

        if self.CONNECTION_POOL is None:
            MultipleProcessRedisBackend.CONNECTION_POOL = redis.Redis(
                **config,
                decode_responses=True,
            )

    def is_valid_config(self, config: BackendConfig) -> bool:
        return True  # TODO

    def inc(self, value: float) -> None:
        if self._labels_hash:
            self.CONNECTION_POOL.hincrbyfloat(self._key_name, self._labels_hash, value)
        else:
            self.CONNECTION_POOL.incrbyfloat(self._key_name, value)

    def get(self) -> float:
        if self._labels_hash:
            value = self.CONNECTION_POOL.hget(self._key_name, self._labels_hash)
        else:
            value = self.CONNECTION_POOL.get(self._key_name)
        return float(value) if value else 0.0


BACKEND_CLASS: Backend
BACKEND_CONFIG: BackendConfig
