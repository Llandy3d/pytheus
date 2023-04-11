# Custom Collector

It is possible to use a custom collector in cases you can't directly instrument the code. You will need to inherit from `CustomCollector` and define the collect method. Also be sure to disable the automatic registering of a newly created metric into the default registry.

```python
from pytheus.metrics import Counter, CustomCollector
from pytheus.registry import REGISTRY

class MyCustomCollector(CustomCollector):
    def collect():
        # note that we are disabling automatic registering
        counter = Counter('name', 'desc', registry=None)
        counter.inc()
        yield counter

REGISTRY.register(MyCustomCollector())
```

!!! note

    If one of the yield metrics have a name already registered with the registry you are trying to register to, the custom collector will be ignored.
