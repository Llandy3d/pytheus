import importlib
import json
import os
from threading import Lock
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

from pytheus.exceptions import InvalidBackendClassException, InvalidBackendConfigException

if TYPE_CHECKING:
    from pytheus.metrics import _Metric


BackendConfig = dict[str, Any]


@runtime_checkable
class Backend(Protocol):
    """
    Describes how to implement a Backend that can be used as a metric value backend.
    It must take the values indicated in the `__init__` method.
    """

    def __init__(
        # optional config ?
        self,
        config: BackendConfig,
        metric: "_Metric",
        histogram_bucket: str | None = None,
    ) -> None:
        ...

    def inc(self, value: float) -> None:
        ...

    def dec(self, value: float) -> None:
        ...

    def set(self, value: float) -> None:
        ...

    def get(self) -> float:
        ...


def _import_backend_class(full_import_path: str) -> type[Backend]:
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
        cls: type[Backend] = getattr(module, class_name)
        if not issubclass(cls, Backend):
            raise InvalidBackendClassException(f"Class '{class_name}' is not a Backend subclass")
        return cls
    except AttributeError:
        raise InvalidBackendClassException(
            f"Class '{class_name}' could not be found in module '{module_path}'"
        )


def load_backend(
    backend_class: type[Backend] | None = None,
    backend_config: BackendConfig | None = None,
) -> None:
    # Load default backend class
    global BACKEND_CLASS
    backend_class_env_var: str = "PYTHEUS_BACKEND_CLASS"
    if backend_class is not None:  # Explicit
        BACKEND_CLASS = backend_class
    elif backend_class_env_var in os.environ:  # Environment
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

    # initialization hook
    if hasattr(BACKEND_CLASS, "_initialize"):
        BACKEND_CLASS._initialize(BACKEND_CONFIG)


def get_backend(metric: "_Metric", histogram_bucket: str | None = None) -> Backend:
    # Probably ok not to cache this and allow each metric to keep its own
    return BACKEND_CLASS(BACKEND_CONFIG, metric, histogram_bucket=histogram_bucket)


class SingleProcessBackend:
    """Provides a single-process backend that uses a thread-safe, in-memory approach."""

    def __init__(
        self,
        config: BackendConfig,
        metric: "_Metric",
        histogram_bucket: str | None = None,
    ) -> None:
        self._value = 0.0
        self._lock = Lock()

    def inc(self, value: float) -> None:
        with self._lock:
            self._value += value

    def dec(self, value: float) -> None:
        with self._lock:
            self._value -= value

    def set(self, value: float) -> None:
        with self._lock:
            self._value = value

    def get(self) -> float:
        with self._lock:
            return self._value


BACKEND_CLASS: type[Backend]
BACKEND_CONFIG: BackendConfig
