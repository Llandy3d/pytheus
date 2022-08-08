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
