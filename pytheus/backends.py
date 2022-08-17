from abc import ABC, abstractmethod
import importlib
import json
import os
from threading import Lock
from typing import Any, Optional, Tuple

from pytheus.exceptions import InvalidBackendClassException, InvalidBackendConfigException

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


def get_backend() -> Backend:
    # Probably ok not to cache this and allow each metric to keep its own
    return BACKEND_CLASS(BACKEND_CONFIG)


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
