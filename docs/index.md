<p align="center">
  <img width="360px" src="/img/pytheus-logo.png" alt='pytheus'>
</p>
<p align="center">
    <em>playing with metrics</em>
</p>

[![ci](https://github.com/Llandy3d/pytheus/workflows/ci/badge.svg?event=push)](https://github.com/Llandy3d/pytheus/actions?query=event%3Apush+branch%3Amain+workflow%3Aci)
[![pypi](https://img.shields.io/pypi/v/pytheus.svg)](https://pypi.python.org/pypi/pytheus)
[![versions](https://img.shields.io/pypi/pyversions/pytheus.svg)](https://github.com/Llandy3d/pytheus)
[![license](https://img.shields.io/github/license/Llandy3d/pytheus.svg)](https://github.com/Llandy3d/pytheus/blob/main/LICENSE)
[![downloads](https://pepy.tech/badge/pytheus/month)](https://pepy.tech/project/pytheus)

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
from flask import Flask, Response
from pytheus.metrics import Histogram
from pytheus.exposition import generate_metrics, PROMETHEUS_CONTENT_TYPE

app = Flask(__name__)

http_request_duration_seconds = Histogram(
    'http_request_duration_seconds', 'documenting the metric..'
)

@app.route('/metrics')
def metrics():
    data = generate_metrics()
    return Response(data, headers={'Content-Type': PROMETHEUS_CONTENT_TYPE})

# track time with the context manager
@app.route('/')
def home():
    with http_request_duration_seconds.time():
        return 'hello world!'

# alternatively you can also track time with the decorator shortcut
@app.route('/slow')
@http_request_duration_seconds
def slow():
    time.sleep(3)
    return 'hello world! from slow!'

app.run(host='0.0.0.0', port=8080)
```

Run the app with `python example.py` and visit either `localhost:8080` or `localhost:8080/slow` and finally you will be able to see your metrics on `localhost:8080/metrics`!

You can also point prometheus to scrape this endpoint and see directly the metrics in there.
