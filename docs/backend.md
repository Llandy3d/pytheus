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
