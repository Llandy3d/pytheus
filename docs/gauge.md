# Gauge

The `Gauge` is a metric whose value can go up and down. It's useful to measure things like memory usage or temperatures for example.

## Usage

```python
from pytheus.metrics import Gauge

gauge = Gauge('room_temperature', 'temperature in the living room')
```

---

### Increment

It is possible to increment by 1 by calling `inc()`:

```python
# increase by 1
gauge.inc()
```

it's also possible to specify the amount:

```python
# increase by 7
gauge.inc(7)
```

---

### Decrement

As for incrementing we can call `dec()` to decrement the value by 1:

```python
# decrease by 1
gauge.dec()
```

or we can specify the amount we want to decrement:

```python
# decrease by 7
gauge.dec(7)
```

---

### Set a value

A `Gauge` value can be set directly with the `set()` method:

```python
gauge.set(3)
```

and as an utility you can also set it to the current time (unix timestamp):

```python
gauge.set_to_current_time()
```

---

### Track progress

You can use the `track_inprogress` context manager to track progress of things, each time the context manager is entered it will increase the gauge value by 1 and each time it exits it will decrease that value:

```python
with gauge.track_inprogress():
    do_something()
```
