# Registry

The `Registry` is the object that collects all of your metrics. By default there is a global registry called `REGISTRY` in the module `pytheus.registry`.

When you create a new metric, it will be automatically added to this registry and when you generate metrics with `generate_metrics` it will use this global registry by default.

!!! tip

    You can create a new metric that won't be added automatically to the global `REGISTRY` by passing the `registry` parameter:

    ```python
    counter = Counter('cache_hit_total', 'description', registry=None)
    ```

## Registry Protocol

It is possible to create your own registry if you need, it just has to respect the `Registry` protocol:

```python
class Registry(Protocol):
    prefix: str | None

    def register(self, collector: Collector) -> None:
        ...

    def unregister(self, collector: Collector) -> None:
        ...

    def collect(self) -> Iterable:
        ...
```

It has three required methods:

- `register`: to register a new metric
- `unregister`: to stop tracking a specific metric
- `collect`: to collect all the samples from the registered metrics

## CollectorRegistry

The included registry in the library is a `CollectorRegistry`.

Besides supporting the methods described in the protocol, it supports a `prefix` parameter when created that allows you to prefix all the metrics it collects.

For example if you would have a metric like `http_request_duration_seconds` registered in a registry with prefix `service_a`, when generating metrics for scraping the output would be `service_a_http_request_duration_seconds`.

!!! note

    Naming metrics like this is against prometheus best practices, the preferred approach would be to use labels instead of hardcoding the name in front of it.

    But it is possible that you might require this naming convention, maybe to have metrics for a specific service discoverable by starting to type the name so I feel the choice is up to the user.

To create your own instance of a `CollectorRegistry` you would do:

```python
from pytheus.registry import CollectorRegistry

my_registry = CollectorRegistry()
```

or if you want to have the prefix set:

```python
my_registry = CollectorRegistry(prefix="service_a")
```

---

To have metrics not register to the default global registry but to your new registry, you can pass it on creation:

```python
my_registry = CollectorRegistry()
counter = Counter('cache_hit_total', 'description', registry=my_registry)
```

!!! tip

    You can also register metrics with the `register` method:

    ```python
    my_registry.register(counter)
    ```

    If you didn't set the `registry` parameter when creating your metric it will still be added automatically to the default global registry unless you pass `registry=None`.

    Meaning that the metric would be registered on both the default global registry and your instantiated registry that you called `.register(counter)` on.

and finally you can use the `generate_metrics` function with your own registry:

```python
from pytheus.exposition import generate_metrics

my_registry = CollectorRegistry()
generate_metrics(my_registry)
```

!!! note

    This becomes useful if you want multiple endpoints with different metrics, just create more registries and selectively add metrics to them and have different endpoints with the `generate_metrics` using each their own registry.

## Registry Proxy

The default global registry `REGISTRY` it's actually a `CollectorRegistryProxy`. A proxy created to make it easy to swap the default registry.

It acts like a registry delegating the operations to the actual registry it holds.

If you want to set the default global registry to an instance you created, for example with a prefix, you can do it like this:

```python
from pytheus.registry import REGISTRY, CollectorRegistry

my_registry = CollectorRegistry(prefix='service_a')
REGISTRY.set_registry(my_registry)
```

!!! warning

    This operation should be done before you create your metrics.
