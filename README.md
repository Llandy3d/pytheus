# pytheus

playing with metrics

---

Currently experimenting with the core metrics interface.
For a specific named metric, this approach has only a single collector (this is internal). The user will use a "view" class to interact with its metric, that will observe based on its labels.
From this "view" class, it will be possible to have predefined labels, set some labels or set all the labels before observing, making it easily cacheable and reusable while the core logic is hidden beneath and the user doesn't have to worry about managing labels.

```python
# this examples use a Metric class, eventually they will be their types (Counter, Gauge,..)

# without labels
my_metric = create_metric('metric_name')
my_metric.inc()  # example for counter

# with labels
my_metric = create_metric('metric_name', required_labels=['req1', 'req2'])
my_metric.inc()  # would fail as we have not set labels

my_metric.labels({'req1': '1', 'req2': '2'}).inc()  # would work

my_metric_with_label_set = my_metric.labels({'req1': '1'})
my_metric_with_label_set.inc()  # would fail as it requires 2 labels
my_metric_with_label_set.labels({'req2': '2'}).inc()  # would work because it has an already set label and now it has both the requires ones!

# this should also support default labels created on metric creation

```

The way to create metrics is up to discussion, instead of a separated function it could be the class itself that creates everything with the appropriate arguments.

## How to use different backends

Things work out of the box, using the SingleProcessBackend:

```python
from pytheus.metrics import create_counter

counter = create_counter(
    name="my_metric",
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
    required_labels=["label_a", "label_b"],
)
print(counter._metric_value_backend.__class__)
# <class 'pytheus.backends.MultipleProcessRedisBackend'>
print(counter._metric_value_backend.config)
# {'host': '127.0.0.1', 'port': 6379}
```