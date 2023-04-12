# Quickref

## Partial Labels

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

## Default Labels

```python
from pytheus.metrics import Counter

# with default labels
my_metric = Counter('metric_name', 'desc', required_labels=['req1', 'req2'], default_labels={'req2': 'me_set!'})

my_metric.labels({'req1': '1'}).inc()  # as we have req2 as a default label we only need to set the remaining labels for observing
my_metric.labels({'req1': '1', 'req2': '2'})  # you can still override default labels!
```

##  Counter

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

## Gauge

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

## Histogram

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
