# Histogram

An `Histogram` is a metric that samples observations and counts them in configurable buckets. It is useful to measure things like request durations or response sizes.

When scraped an histogram produces multiple time series:

- cumulative counters for the observation buckets (ex. `http_request_duration_seconds{le="1"}`)
- total sum of observed values (ex. `http_request_duration_seconds_sum`)
- count of events that have been observed (ex. `http_request_duration_seconds_count`)

!!! tip

    You can use the `histogram_quantile` function in prometheus to calculate quantiles, for examples if you have an `http_request_duration_seconds` histogram you could see how an endpoint is doing in the 95th percentile.

!!! tip

    For more information on how to use histograms check the [prometheus docs](https://prometheus.io/docs/practices/histograms/)

## Usage

```python
from pytheus.metrics import Histogram

histogram = Histogram(name="http_request_duration_seconds", description="My description")
```

---

### Configure Buckets

By default an `Histogram` will be created with the following buckets:
```
(.005, .01, .025, .05, .1, .25, .5, 1, 2.5, 5, 10)
```

Default buckets are tailored to broadly measure the response time (in seconds) of a network, you most likely will want to pass a customized list and you can with the `buckets` parameter when creating the histogram:

```python
customized_buckets = (0.1, 0.3, 2, 5)
histogram = Histogram(
    name="http_request_duration_seconds",
    description="My description",
    buckets=customized_buckets,
)
```

!!! note

    `buckets` accepts a `Sequence[float]`.

!!! note

    The `+Inf` bucket will be added automatically, this is `float('inf')` in python

---

### Observe a value

To observe a value you can call the `observe()` method:

```python
histogram.observe(0.4)
```

---

### Track time

You can track time with the `time()` context manager, it will track the duration in seconds:

```python
with histogram.time():
    do_something()
```

---

### As a Decorator


When used as a decorator the `Histogram` will time the piece of code, syntactic sugar to the `time()` context manager:

```python
@histogram
def do_something():
    ...
```
