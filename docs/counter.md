# Counter

A `Counter` is a metric that only increases in value, it could also reset to 0 for example in case of a service restart.

As the name suggests it's useful to count things, for example cache hits, number of connections or even count exceptions.

!!! tip

    If you need a metric that can go up and down in value, checkout the [Gauge](gauge.md).

## Usage

To create a `Counter` import it and instantiate:

```python
from pytheus.metrics import Counter

cache_hit_total = Counter(name='cache_hit_total', description='number of times the cache got it')
```

---

### Increment the value

Now it's possible to increment the count by calling the `inc()`:

```python
# increases value by 1
cache_hit_total.inc()
```

it is also possible to specify by which amount to increase:

```python
# increases value by 7
cache_hit_total.inc(7)
```

!!! warning

    `inc()` accepts only positive values as counters cannot decrease.

---

### Count Exceptions

As counters are a good fit for counting exceptions there are some nicities included, you can count exceptions within a `with` statement with `count_exceptions`:

!!! note

    the following examples assume a `Counter` called `counter`.

```python
with counter.count_exceptions():
    raise ValueError  # increases counter by 1
```

It is also possible to specify which `Exceptions` to count:

```python
with counter.count_exceptions((IndexError, ValueError)):
    raise KeyError. # does not increase as it's not included in the list
```

!!! tip

    `count_exceptions` accepts an `Exception` or a tuple of exceptions.

---

### As a Decorator

When used as a decorator the `Counter` will count exceptions, syntactic sugar to `count_exceptions`:

```python
@counter
def my_func():
    raise ValueError  # increases counter by 1 when it raises
```

you are still able to specify which exceptions you want to count:

```python
@counter(exceptions=(IndexError, ValueError))
def my_func():
    raise KeyError  # won't increase when raised as it's not in the list
```
