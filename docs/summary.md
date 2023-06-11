# Summary

A `Summary` is a metric that captures individual observations and tracks the total size & number of events observed. It can be useful to track latencies for example.

When scraped a summary produces a couple of time series:

- total sum of observed values (ex. `http_request_duration_seconds_sum`)
- count of events that have been observed (ex. `http_request_duration_seconds_count`)


!!! tip

    For when to use a summary vs histograms check the [prometheus docs](https://prometheus.io/docs/practices/histograms/)

## Usage

```python
from pytheus.metrics import Summary

summary = Summary(name="http_request_duration_seconds", description="My description")
```

---

### Observe a value

To observe a value you can call the `observe()` method:

```python
summary.observe(0.4)
```

---

### Track time

You can track time with the `time()` context manager, it will track the duration in seconds:

```python
with summary.time():
    do_something()
```

---

### As a Decorator


When used as a decorator the `Summary` will time the piece of code, syntactic sugar to the `time()` context manager:

```python
@summary
def do_something():
    ...
```
