![pytheus-logo](https://user-images.githubusercontent.com/16627175/185823115-b33905c3-f389-40e1-b830-2197889a936a.png)

# pytheus

playing with metrics

---

Experimenting with a different way of creating prometheus metrics in python:
- support for default labels value (wip ⚠️)
- partial labels value (built in an incremental way) ✅
- multiple multiprocess support:
  - mmap file based (wip ⚠️)
  - redis backend ✅
- customizable registry support ✅
- registry prefix support ✅

---

**Install**

```
pip install pytheus
```

*NOTE:* Currently you need the redis library installed but the requirement will be removed soon.
```python
pip install redis
# or
pip install pytheus[redis]
```

---

**Partial labels support:**

```python
from pytheus.metrics import create_counter

# without labels
my_metric = create_counter('metric_name', 'desc')
my_metric.inc()  # example for counter

# with labels
my_metric = create_counter('metric_name', 'desc', required_labels=['req1', 'req2'])

my_metric.labels({'req1': '1', 'req2': '2'}).inc()  # you can pass all the labels at once
partial_my_metric = my_metric.labels({'req1': '1'})  # a cacheable object with one of the required labels already set
observable_my_metric = partial_my_metric.labels({'req2': '2'}).inc()  # finish setting the remaining values before observing

```

---

**Exposing metrics:**

You can use the `generate_metrics` function from `pytheus.exposition` to generate the metrics and serve them as an endpoint with your favourite web framework.

Alternatively you can use the `make_wsgi_app` function that creates a simple wsgi app to serve the metrics.

## How to use different backends

Things work out of the box, using the SingleProcessBackend:

```python
from pytheus.metrics import create_counter

counter = create_counter(
    name="my_metric",
    description="My description",
    required_labels=["label_a", "label_b"],
)
print(counter._metric_value_backend.__class__)
# <class 'pytheus.backends.SingleProcessBackend'>
print(counter._metric_value_backend.config)
# {}
```

You can define environment configuration to have different defaults, using two environment variables:

```bash
export PYTHEUS_BACKEND_CLASS="pytheus.backends.MultipleProcessFileBackend"
export PYTHEUS_BACKEND_CONFIG="./config.json"
```

Now, create the config file, `./config.json`:

```json
{
  "pytheus_file_directory": "./"
}
```

Now we can try the same snippet as above:

```python
from pytheus.metrics import create_counter

counter = create_counter(
    name="my_metric",
    description="My description",
    required_labels=["label_a", "label_b"],
)
print(counter._metric_value_backend.__class__)
# <class 'pytheus.backends.MultipleProcessFileBackend'>
print(counter._metric_value_backend.config)
# {'pytheus_file_directory': "./"}
```

You can also pass the values directly in Python, which would take precedence over the environment
setup we have just described:

```python

from pytheus.metrics import create_counter
from pytheus.backends import MultipleProcessRedisBackend, load_backend

load_backend(
    backend_class=MultipleProcessRedisBackend,
    backend_config={
      "host": "127.0.0.1",
      "port":  6379
    }
)
# Notice that if you simply call load_backend(), it would reload config from the environment.

# load_backend() is called automatically at package import, that's why we didn't need to call it
# directly in the previous example

counter = create_counter(
    name="my_metric",
    description="My description",
    required_labels=["label_a", "label_b"],
)
print(counter._metric_value_backend.__class__)
# <class 'pytheus.backends.MultipleProcessRedisBackend'>
print(counter._metric_value_backend.config)
# {'host': '127.0.0.1', 'port': 6379}
```
