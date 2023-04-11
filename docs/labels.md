# Labels

With labels you can differentiate what you are measuring, for example for an `http_request_duration_seconds` metric you might want to differentiate between `GET` or `POST` requests while using the same metric.

!!! warning


    Every new value for a label key represents a new time serie, so you should try to avoid labels that measure things with high cardinality, for example a path that has no specific ending: `/users/{id}` {here id is variable depending on the request}.

    In that case it would be better to observe the metric replacing the last part of the endpoint with a fixed value so that you still get useful information: `/users/:id`

### Creating a metric with a label

To create a metric that requires labels we will use the `required_labels` parameter when creating our metric. It's a list of strings.
To show how to use a label, let's create a `Counter` that will accept a `method` label:

!!! note

    `required_labels`:  accepts a `Sequence[str]`

```python
from pytheus.metrics import Counter

page_hit_total = Counter(
    'page_hit_total',
    'number of time this page got it',
    required_labels=['method'],
)
```

Since our new metric has atleast a label required, if you try to observe it, it will fail:

```python
page_hit_total.inc()

Traceback (most recent call last):
  File "<stdin>", line 1, in <module>
  File "/Users/llandy/dev/pytheus/pytheus/metrics.py", line 283, in inc
    self._raise_if_cannot_observe()
  File "/Users/llandy/dev/pytheus/pytheus/metrics.py", line 198, in _raise_if_cannot_observe
    raise UnobservableMetricException
pytheus.exceptions.UnobservableMetricException
```

A metric is considered "unobservable" if you try to observe it without passing the labels that were defined as required. The correct way to observe it for example with the `method` label mapped to `GET` would be:

```python
page_hit_total.labels({'method': 'GET'}).inc()
```

!!! note

    The `labels` method accepts `dict[str, str]` where the key of the dictionary is the label name and the value is the value of the label.

we can do the same for the label mapped to the value `POST` and the metrics created would be:

```python
page_hit_total.labels({'method': 'POST'}).inc(3)
```

``` title="the created time series"
page_hit_total{method="GET"} 1.0
page_hit_total{method="POST"} 3.0
```

this allows us to check the `page_hit_total` metric in prometheus, or if we want specifics we can check the values for a specific label like `page_hit_total{method="GET"}`!

---

### Caching the instance with a set label

Calling everytime the `labels()` method is tiresome, so it's possible to assign the value it returns to a new variable, it returns an instance of the metric class you used with the label already set!

```python
page_hit_total_with_get = page_hit_total.labels({'method': 'GET'})
```

then we can observe it directly:

```python
page_hit_total_with_get.inc()
```

!!! note

    This works because when you create a metric, for example with `Counter`, the object you receive is like a "view" into the metric.

    Under the hood there is an `_MetricCollector` class that handles all the logic for all the labels combinations, while the object you interact with is a `_Metric` object.

    When you call the `labels()` method on a metric object you will receive a new `_Metric` instance with the labels set. This allows for partial labels!

---

### Default labels

Default labels allow you to define a value that will be used by default for a set of required labels.

For example you might want to measure the duration of http requests from different services with the same metric name, it would be annoying having to set that label everytime so we can just define a default to use and possibly overwrite it when needed!

```python
http_request_duration_seconds = Histogram(
    'http_request_duration_seconds',
    'documenting the metric..',
    required_labels=['service'],
    default_labels={'service': 'main_service'},
)
```

we can observe it directly even if there is a required label since it's configured with a default value:

```python
http_request_duration_seconds.observe(1)
```

or we can override the default value:

```python
http_request_duration_seconds_side_service = http_request_duration_seconds.labels(
    {'service': 'side_service'}
)
```

!!! note

    `default_labels` takes a `dict[str, str]`

---

### Partial labels

With the `labels()` method returning a new instance of the metric class, it's possible to have instances that are not observable but have some defined values. This would be useful if there are a set of labels that you want to share and just a few remaining ones are different.

Let's say that we have two systems `a` & `b`, and we want to meausure how many times a cache gets hit plus we want a label telling us the origin of the call, we can define the metric like this:

```python
cache_hit_count_total = Counter(
    'cache_hit_count_total',
    'number of time the cache got it',
    required_labels=['system', 'origin'],
)

cache_hit_count_total_system_a = cache_hit_count_total.labels({'system': 'a'})
cache_hit_count_total_system_b = cache_hit_count_total.labels({'system': 'b'})
```

we defined two partial metrics with a label set for system `a` and one for system `b`. These are partial labels because if you try to observe them they will raise an error since not all the required labels are set.

We can then use them to observe the metrics avoiding the repetition of having to define the system each time:

```python
cache_hit_count_total_system_a.labels({'origin': 'function_a'}).inc()
cache_hit_count_total_system_a.labels({'origin': 'function_b'}).inc()

cache_hit_count_total_system_b.labels({'origin': 'function_a'}).inc()
```

As you can see there could be some repetition from the previous example if the metric would be used in different places calling `labels()` again and again is annoying so we can create a new variable to hold a metric with also the `origin` label set:

```python
cache_hit_count_total_system_a_with_origin.labels({'origin': 'function_a'})

cache_hit_count_total_system_a_with_origin.inc()
```

This is the flexibility of partial labels, you can "cache" into variables your metric like you want and build upon it for what it makes sense for your use case.

!!! note

    Partial labels are built in an incremental way, meaning that each new instance returned when calling `labels(...)` will return an instance with the previous labels set.

    If you call the `labels({})` method with an empty dicy `{}` it will just return the same instance.
