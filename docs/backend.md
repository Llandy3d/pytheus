# Backend / Multiprocessing

This is an important part of the library designed to make the switch from single process to multi process monitoring extremely simple without requiring changes from the user beside a configuration.

`Backend` is a protocol used for each value of a metric, meaning that when you create a `Counter` for example, its actual value will be an instance of a `Backend` that will handle the logic for that value. For single process it could be a mutex based implementation while for multi process it could be a redis backed one.

Regardless of backend used, if you want to increment the `Counter` you would call the same `inc()` method, so that you can easily switch between single and multi process with ease.

!!! note

    One of my goals for this library is to have the interface be the same between single & multi process, meaning that the features supported should always handle both cases.

## Backend Protocol

The backend protocol is as follows:

```python
class Backend(Protocol):
    def __init__(
        self,
        config: BackendConfig,
        metric: "_Metric",
        ,
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
```

When creating a custom backend the `__init__` method has to accept:

- `config: BackendConfig`: possible configuration values for initializing it
- `metric: _Metric`: the metric that is creating the instance of this backend for a value
- `histogram_bucket: str | None`: bucket name in case it's instanced for an histogram

You don't have to use these values in your implementation, they just need to be accepted.

!!! note

    `BackendConfig` is of type `dict[str, Any]`

    `_Metric` is any of `Counter`, `Gauge`, `Histogram`

!!! tip

    It's possible that you want to initialize your custom backend or there are one time steps that you want to happen on import.

    To achieve that you can use the class method hook called `_initialize` that accepts a `BackendConfig` parameter.

    ```python
    @classmethod
    def _initialize(cls, config: "BackendConfig") -> None:
        # initialization steps
    ```

---

## Default Backend

The default backend used is a `SingleProcessBackend`. A thread-safe in-memory implementation that makes use of `threading.Lock`.

```python
from pytheus.metrics import Counter

counter = Counter('cache_hit_total', 'description')
print(counter._metric_value_backend.__class__)
# <class 'pytheus.backends.base.SingleProcessBackend'>
```

---

## Multiprocess Backend

The library also includes a redis based implementation of the backend for supporting multi process python services: `MultiProcessRedisBackend`.

This makes use of the `INCRBYFLOAT` & `HINCRBYFLOAT` redis operations that are `ATOMIC` and as redis is single-threaded it means that even if multiple clients try to update the same value we will end up with the correct one.

!!! tip

    When using the `MultiProcessRedisBackend` you will want to have a separate redis server o database specified per service you are monitoring. If you don't there is a risk that a metric with the same name on one service might overwrite one in another service.

    If you plan to share the same redis server for multiple services, you can configure a prefix that will be added to all the stored metrics with the `key_prefix`.

    For example: `{"host": "127.0.0.1", "port": 6379, "key_prefix": "serviceprefix"}`

---

## Loading a different Backend

To load a different backend you can make use of the `load_backend` function, for example for loading the `MultiProcessRedisBackend`:

```python
from pytheus.backends import load_backend
from pytheus.backends.redis import MultiProcessRedisBackend

load_backend(
    backend_class=MultiProcessRedisBackend,
    backend_config={"host": "127.0.0.1", "port": 6379},
)
```

now when you create a metric it will use the configured backend:

```python
counter = Counter('cache_hit_total', 'description')
print(counter._metric_value_backend.__class__)
# <class 'pytheus.backends.redis.MultiProcessRedisBackend'>
```

!!! warning

    This operation should be done before you create your metrics as an initialization step.

!!! tip

    `load_backend()` it's called automatically when you import the `pytheus` library and it supports environment variables to configure which backend to use and the config, so you can just set them without having to call the function yourself:

    - `PYTHEUS_BACKEND_CLASS`: class to import, for example `pytheus.backends.redis.MultiProcessFileBackend`
    - `PYTHEUS_BACKEND_CONFIG`: path to a `json` file containing the config

!!! note

    The function definition is:
    ```python
    def load_backend(
        backend_class: type[Backend] | None = None,
        backend_config: BackendConfig | None = None,
    ) -> None:
    ```
