from abc import ABC, abstractmethod
import json
import os
from threading import Lock
from typing import Any, Optional, Tuple

from pytheus.exceptions import PytheusException

BackendConfig = dict[str, Any]


class Backend(ABC):
    def __init__(self, config: BackendConfig):
        self.config = config  # TODO: We should discuss validation here (jsonschema, pydantic, etc)

    @abstractmethod
    def inc(self, value: float) -> None:
        pass

    @abstractmethod
    def get(self) -> float:
        pass


class InvalidBackendClassException(PytheusException):
    def __init__(self, class_name: str):
        super().__init__(
            f"Invalid backend class '{class_name}', please use any of the following: "
            f"{', '.join([cls.__name__ for cls in Backend.__subclasses__()])}"
        )

class InvalidBackendConfigException(PytheusException):
    pass


def load_backend(
    backend_class: Optional[Backend] = None,
    backend_config: Optional[BackendConfig] = None,
):

    # Load default backend class
    global BACKEND_CLASS
    backend_class_env_var: str = "PYTHEUS_BACKEND_CLASS"
    if backend_class is not None:  # Explicit
        BACKEND_CLASS = backend_class
    elif backend_class_env_var in os.environ:  # Environment
        class_name = os.environ[backend_class_env_var]
        try:
            BACKEND_CLASS = globals()[class_name]
        except KeyError:
            raise InvalidBackendClassException(class_name)
    else:  # Default
        BACKEND_CLASS = SingleProcessBackend

    # Load default backend config
    global BACKEND_CONFIG
    backend_config_env_var: str = "PYTHEUS_BACKEND_CONFIG"
    if backend_config is not None:  # Explicit
        BACKEND_CONFIG = backend_config
    if backend_config_env_var in os.environ:  # Environment
        try:
            with open(os.environ[backend_config_env_var]) as f:
                BACKEND_CONFIG = json.loads(f.read())  # TODO: Support yaml?
        except Exception as e:
            raise InvalidBackendConfigException(f"{e.__class__}: {e}")
    else:
        BACKEND_CONFIG = {}  # Default


def get_backend() -> Tuple[Backend, BackendConfig]:
    return BACKEND_CLASS, BACKEND_CONFIG


class SingleProcessBackend(Backend):
    """Provides a single-process backend that uses a thread-safe, in-memory approach."""

    def __init__(self, config: BackendConfig) -> None:
        super().__init__(config)
        self._value = 0.0
        self._lock = Lock()

    def inc(self, value: float) -> None:
        with self._lock:
            self._value += value

    def get(self) -> float:
        with self._lock:
            return self._value


class MultipleProcessFileBackend(Backend):
    """Provides a multi-process backend that uses MMAP files."""

    def inc(self, value: float) -> None:
        pass  # TODO

    def get(self) -> float:
        pass  # TODO


class MultipleProcessRedisBackend(Backend):
    """Provides a multi-process backend that uses Redis."""

    def inc(self, value: float) -> None:
        pass  # TODO

    def get(self) -> float:
        pass  # TODO


BACKEND_CLASS: Backend
BACKEND_CONFIG: BackendConfig
