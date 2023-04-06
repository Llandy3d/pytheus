<p align="center">
  <img width="360px" src="/img/pytheus-logo.png" alt='pytheus'>
</p>
<p align="center">
    <em>playing with metrics</em>
</p>

# Introduction

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

## Installation

```
pip install pytheus
```

Optionally if you want to use the Redis backend (for multiprocess support) you will need the redis library:
```
pip install redis

# or everything in one command
pip install pytheus[redis]
```

---

## Example

```python title="example.py"
import time
from flask import Flask
from pytheus.metrics import Histogram
from pytheus.exposition import generate_metrics

app = Flask(__name__)

page_visit_latency_seconds = Histogram(
    'page_visit_latency_seconds', 'documenting the metric..'
)

# this is the endpoint that prometheus will use to scrape the metrics
@app.route('/metrics')
def metrics():
    return generate_metrics()

# track time with the context manager
@app.route('/')
def home():
    with page_visit_latency_seconds.time():
        return 'hello world!'

# alternatively you can also track time with the decorator shortcut
@app.route('/slow')
@page_visit_latency_seconds
def slow():
    time.sleep(3)
    return 'hello world! from slow!'

app.run(host='0.0.0.0', port=8080)
```

Run the app with `python example.py` and visit either `localhost:8080` or `localhost:8080/slow` and finally you will be able to see your metrics on `localhost:8080/metrics`!

You can also point prometheus to scrape this endpoint and see directly the metrics in there.
