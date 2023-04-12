<img src="https://user-images.githubusercontent.com/16627175/185823115-b33905c3-f389-40e1-b830-2197889a936a.png" height="400">

# pytheus

*playing with metrics*

---

**Documentation**: https://pythe.us

---

pytheus is a modern python library for collecting [prometheus](https://prometheus.io/docs/introduction/overview/) metrics built with multiprocessing in mind.

Some of the features are:

  - multiple multiprocess support:
    - redis backend ✅
    - bring your own ✅
  - support for default labels value ✅
  - partial labels value (built in an incremental way) ✅
  - customizable registry support ✅
  - registry prefix support ✅

---
## Philosophy

Simply put is to let you work with metrics the way you want.

Be extremely flexible, allow for customization from the user for anything they might want to do without having to resort to hacks and most importantly offer the same api for single & multi process scenarios, the switch should be as easy as loading a different backend without having to change anything in the code.

- What you see is what you get.
- No differences between `singleprocess` & `multiprocess`, the only change is loading a different backend and everything will work out of the box.
- High flexibility with an high degree of `labels` control and customization.

---
## Requirements

- Python 3.10+
- redis >= 4.0.0 (**optional**: for multiprocessing)

---

**Architecture**

A small piece of the architecture is described in the [ARCHITECTURE.md file](ARCHITECTURE.md)

---

**Install**

```
pip install pytheus
```

Optionally if you want to use the Redis backend (for multiprocess support) you will need the redis library:
```python
pip install redis
# or
pip install pytheus[redis]
```

---

**Partial labels support:**

```python
from pytheus.metrics import Counter

# without labels
my_metric = Counter('metric_name', 'desc')
my_metric.inc()  # example for counter

# with labels
my_metric = Counter('metric_name', 'desc', required_labels=['req1', 'req2'])

my_metric.labels({'req1': '1', 'req2': '2'}).inc()  # you can pass all the labels at once
partial_my_metric = my_metric.labels({'req1': '1'})  # a cacheable object with one of the required labels already set
observable_my_metric = partial_my_metric.labels({'req2': '2'})  # finish setting the remaining values before observing
observable_my_metric.inc()

```

---

**Default labels support:**

```python
from pytheus.metrics import Counter

# with default labels
my_metric = Counter('metric_name', 'desc', required_labels=['req1', 'req2'], default_labels={'req2': 'me_set!'})

my_metric.labels({'req1': '1'}).inc()  # as we have req2 as a default label we only need to set the remaining labels for observing
my_metric.labels({'req1': '1', 'req2': '2'})  # you can still override default labels!

```

---

**Exposing metrics:**

You can use the `generate_metrics` function from `pytheus.exposition` to generate the metrics and serve them as an endpoint with your favourite web framework.

Alternatively you can use the `make_wsgi_app` function that creates a simple wsgi app to serve the metrics.

---

## Quickstart / Example

The `example.py` file starts a flask application with three endpoints:
  - `/`: just returns a phrase while observing the time taken for the request to complete
  -  `/slow`: same as before but will sleep so that values will only end up in higher buckets
  -  `/metrics`: the endpoint used by prometheus to scrape the metrics

It uses two histograms, one without labels, and one with labels required and a default label that makes it observable.
To expose the metrics the `generate_metrics()` function is used.
note: the example file is using the redis backend but you can try without and set up prometheus yourself.

### Redis version

For the redis version you can just clone the repository and run `docker-compose up` to start both redis and prometheus scraping on localhost:8080.
Then you can start the local server with `python example.py`. (flask is required for it to work)

Now you can visit the described endpoints and by visiting `localhost:9090` you can query prometheus, for example by looking for all the slow requests buckets: `page_visits_latency_seconds_labeled_bucket{speed="slow"}`

<img width="1693" alt="image" src="https://user-images.githubusercontent.com/16627175/206577287-06bf89c3-7ab6-4a70-b14c-415be32ea890.png">

### Default version

For the default single process version you can create your python server like this:

```python
import time
from flask import Flask
from pytheus.metrics import Histogram
from pytheus.exposition import generate_metrics

app = Flask(__name__)

histogram = Histogram('page_visits_latency_seconds', 'used for testing')

# this is the endpoint that prometheus will use to scrape the metrics
@app.route('/metrics')
def metrics():
    return generate_metrics()

# track time with the context manager
@app.route('/')
def home():
    with histogram.time():
        return 'hello world!'

# you can also track time with the decorator shortcut
@app.route('/slow')
@histogram
def slow():
    time.sleep(3)
    return 'hello world! from slow!'

app.run(host='0.0.0.0', port=8080)
```

and if you have prometheus installed configure it to scrape on localhost:8080 or you can still use the included `docker-compose.yml` file.

---

## Metric types

### Counter

The Counter is a metric that only increases and can resets to 0. (For example if a service restart, it will start again from zero)

```python
from pytheus.metrics import Counter

counter = Counter(name="my_counter", description="My description")

# increase by 1
counter.inc()

# increase by x
counter.inc(7)

# it is possible to count exceptions
with counter.count_exceptions():
    raise ValueError  # increases counter by 1

# you can specify which exceptions to watch for
with counter.count_exceptions((IndexError, ValueError)):
    raise ValueError. # increases counter by 1

# it is possible to use the counter as a decorator as a shortcut to count exceptions
@counter
def test():
    raise ValueError  # increases counter by 1 when called

# specifying which exceptions to look for also works with the decorator
@counter(exceptions=(IndexError, ValueError))
def test():
    raise ValueError  # increases counter by 1 when called
```

---

### Gauge

The Gauge can increase and decrease its value. It is also possible to set a specific value.

```python
from pytheus.metrics import Gauge

gauge = Gauge(name="my_gauge", description="My description")

# increase by 1
gauge.inc()

# increase by x
gauge.inc(7)

# decrease by 1
gauge.dec()

# set a specific value
gauge.set(7)

# set to current unix timestamp
gauge.set_to_current_time()

# it is possible to track progress so that when entered increases the value by 1, and when exited decreases it
with gauge.track_inprogress():
    do_something()

# you can also time a piece of code, will set the duration in seconds to value when exited
with gauge.time():
    do_something()

# tracking time can also be done as a decorator
@gauge
def do_something():
    ...

# tracking progress is also available via decorator with a flag
@gauge(track_inprogress=True)
def do_something():
    ...
```

---

### Histogram

A histogram samples observations (usually things like request durations or response sizes) and counts them in configurable buckets. It also provides a sum of all observed values. ([taken from prometheus docs](https://prometheus.io/docs/concepts/metric_types/#histogram))

```python
from pytheus.metrics import Histogram

histogram = Histogram(name="my_histogram", description="My description")
# by default it will have the following buckets: (.005, .01, .025, .05, .1, .25, .5, 1, 2.5, 5, 10)
# note: the +Inf bucket will be added automatically, this is float('inf') in python

# create a histogram specifying buckets
histogram = Histogram(name="my_histogram", description="My description", buckets=(0.2, 1, 3))

# observe a value
histogram.observe(0.4)

# you can also time a piece of code, will set the duration in seconds to value when exited
with histogram.time():
    do_something()

# tracking time can also be done as a decorator
@histogram
def do_something():
    ...
```

## Custom Collectors

It is possible to use a custom collector in cases you can't directly instrument the code.
You will need to inherit from `CustomCollector` and define the `collect` method.
Also be sure to disable the automatic registering of a newly created metric into the default registry.

```python
from pytheus.metrics import Counter, CustomCollector
from pytheus.registry import REGISTRY

class MyCustomCollector(CustomCollector):
    def collect():
        counter = Counter('name', 'desc', registry=None)  # note that we are disabling automatic registering
        counter.inc()
        yield counter

REGISTRY.register(MyCustomCollector())
```

Note: if one of the yield metrics have a name already registered with the registry you are trying to register to, the custom collector will be ignored.


## How to use different backends

Things work out of the box, using the SingleProcessBackend:

```python
from pytheus.metrics import Counter

counter = Counter(
    name="my_metric",
    description="My description",
    required_labels=["label_a", "label_b"],
)
print(counter._metric_value_backend.__class__)
# <class 'pytheus.backends.base.SingleProcessBackend'>
print(counter._metric_value_backend.config)
# {}
```

You can define environment configuration to have different defaults, using two environment variables:

```bash
export PYTHEUS_BACKEND_CLASS="pytheus.backends.redis.MultiProcessRedisBackend"
export PYTHEUS_BACKEND_CONFIG="./config.json"
```

Now, create the config file, `./config.json`:

```json
{
  "host": "127.0.0.1",
  "port":  6379
}
```

Now we can try the same snippet as above:

```python
from pytheus.metrics import Counter

counter = Counter(
    name="my_metric",
    description="My description",
    required_labels=["label_a", "label_b"],
)
print(counter._metric_value_backend.__class__)
# <class 'pytheus.backends.redis.MultiProcessRedisBackend'>
print(counter._metric_value_backend.config)
# {"host": "127.0.0.1", "port":  6379}
```

You can also pass the values directly in Python, which would take precedence over the environment
setup we have just described:

```python

from pytheus.metrics import Counter
from pytheus.backends import load_backend
from pytheus.backends.redis import MultiProcessRedisBackend

load_backend(
    backend_class=MultiProcessRedisBackend,
    backend_config={
      "host": "127.0.0.1",
      "port":  6379
    }
)
# Notice that if you simply call load_backend(), it would reload config from the environment.

# load_backend() is called automatically at package import, that's why we didn't need to call it
# directly in the previous example

counter = Counter(
    name="my_metric",
    description="My description",
    required_labels=["label_a", "label_b"],
)
print(counter._metric_value_backend.__class__)
# <class 'pytheus.backends.redis.MultiProcessRedisBackend'>
print(counter._metric_value_backend.config)
# {'host': '127.0.0.1', 'port': 6379}
```

## Create your own Backend

### Custom Backend

You can create your own backend by implementing a class that fulfills the `Backend` protocol.

```python
class Backend(Protocol):
    def __init__(
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
```

### Initialization hook

It's possible that you want to initialize your custom backend or there are one time steps that you want to happen on import.

To achieve that you can use the class method hook called `_initialize` that accepts a `BackendConfig` parameter.

```python
@classmethod
def _initialize(cls, config: "BackendConfig") -> None:
    # initialization steps
```
