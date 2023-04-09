# Quickstart

Here we will build piece by piece the introductory example while explaining what the different pieces are doing, we will end with loading the redis backend where you will see that it's a matter of just loading a different backend with a function call :)

We will be using [Flask](https://flask.palletsprojects.com) to create a small api service where we monitor the time it takes for an endpoint to respond and we will have a slow one on purpose so that we have some different data to query when scraped by prometheus!

!!! note

    if you download the source repo for the pytheus project, you can use the included `docker-compose.yaml` file to spin up a redis & prometheus instance already configured that will pick up your metrics so that you can interactively explore them!

    Or you can always configure prometheus yourself to scrape the `/metrics` endpoint :)

## Metrics

Metrics are numeric measurements, represented by time-series data (`timestamp - float value`) that you observe changing over time.

They become useful to monitor things like the time it takes for an endpoint to return a response, to count the number of connections overtime or to monitor active queries for example.

The available metrics types in the library are:

- Counter
- Gauge
- Histogram

!!! note

    I'm leaving out `Summary`, the last type supported by prometheus, for now to leave it as a ticket for someone to contribute to :)

You can import and create a metric like this:

```python
from prometheus.metrics import Counter

page_hit_total = Counter('page_hit_total', 'documentation string')
```

to observe it in the specific case of a `Counter` you would increase it:

```python
page_hit_total.inc()
# or specify the amount
page_hit_total.inc(2)
```

## Registry

The registry it's an object that contains the metrics you created. By default when you create a metric from the appropriate class it will be automatically registered in the global `REGISTRY` object.

This global object is used to generate the text that prometheus can scrape and will handle logic checks to confirm that you are not duplicating metrics name for example.
You can access the global registry object by importing it:

```python
from pytheus.registry import REGISTRY
```

Sometimes you might want to register a metric directly (for example when creating a custom collector) and you can do it like this:

```python
REGISTRY.register(mycollector)
```

!!! note

    `REGISTRY` is not really the registry object in this library, but a proxy used to interact with one.

## Exposition

To expose the metrics for prometheus to scrape use your favourite library!

The library offers the `generate_metrics` function that will ask the global registry to collect all the metrics and return them to you in a text based format. From there is just a matter of exposing an endpoint (usually `/metrics`) where you return that data.

```python
from pytheus.exposition import generate_metrics

metrics_data = generate_metrics()
```

It's good practice to set the `Content-Type` header so it's offered as a constant:

```python
from pytheus.exposition import PROMETHEUS_CONTENT_TYPE

headers = {'Content-Type': PROMETHEUS_CONTENT_TYPE}
```

## Project

Now let's start with the quickstart project!

### Setup

First setup your environment.

```bash
# create the project directory
mkdir quickstart
cd quickstart

# create a python virtual environment and activate it
python3 -m venv venv
. venv/bin/activate

# install the required libraries for the quickstart
pip install pytheus
pip install flask
```

### Api service

Next, let's build a service with two endpoints, one that will return a string normally and one that will be slowed artificially so that it will return the data with some delay.

```python title="quickstart.py"
import time
from flask import Flask

app = Flask(__name__)

# normal endpoint
@app.route('/')
def home():
    return 'hello world!'

# slowed endpoint with the `time` library
@app.route('/slow')
def slow():
    time.sleep(3)
    return 'hello world! from slow!'

app.run(host='0.0.0.0', port=8080)
```

You can now start the server with
```bash
python quickstart.py
```

and you will be able to reach the `localhost:8080/` & `localhost:8080/slow` endpoints for example from your browser or from a networking tool.

The first one will return the string `hello world!` immediately while the second will take 3 seconds to return its string due to the `time.sleep(3)` call.

### Adding metrics

Now that we have a service with two endpoints we want to measure how much time it takes for them to respond. How many requests are handled in less than 1 second ? How many are handled over 5 seconds ? What is the 95th percentile ?

We can answer those questions with metrics.

---

First of all we import the metric class (`Histogram` makes sense for what we want to track):

```python
from pytheus.metrics import Histogram
```

then we instantiate our metric, we need to give it a name and a documentation string explaining what the metric does.

```python
http_request_duration_seconds = Histogram(
    'http_request_duration_seconds', 'documenting the metric..'
)
```

!!! note

    The metric name parameter passed in and the variable name don't have to be the same, here I've done it because it makes it easier to understand what a particular metric is observing.

    The documentation string is a mandatory parameter but can be the empty string `""` although it would be better to document the metric.

Now what is left to do is to use our metric to observe the endpoints, we can either use the `time()` method of the metric class or we can use the shortcut of using the metric as a decorator.

We will show both approaches, one used for each endpoint:

```python hl_lines="3" title="track time with the context manager"
@app.route('/')
def home():
    with http_request_duration_seconds.time():
        return 'hello world!'
```

```python hl_lines="2" title="track time with the decorator shortcut"
@app.route('/slow')
@http_request_duration_seconds
def slow():
    time.sleep(3)
    return 'hello world! from slow!'
```

Congratulations! You have instrumented your service and you are now collecting metrics. 🎉

But wait, where are the metrics?

### Exposing the metrics

With the code you've added the library is collecting metrics but now you need to expose them so that prometheus can scrape them.

The way to do it is usually by having a `/metrics` endpoint with the data ready to be scraped, we can do that with the `generate_metrics` function.

Let's create the endpoint exposing the metrics!

We will start by importing the mentioned function:

```python
from flask import Flask, Response  # we will need the Response class
from pytheus.exposition import generate_metrics, PROMETHEUS_CONTENT_TYPE
```

!!! note

    `PROMETHEUS_CONTENT_TYPE` is an helper containing the correct `Content-Type` for you to use as an header in your response.

then we create the `/metrics` endpoint where we make use of the data generated by that function:

```python
@app.route('/metrics')
def metrics():
    data = generate_metrics()
    return Response(data, headers={'Content-Type': PROMETHEUS_CONTENT_TYPE})
```

if you start the service and visit the `/metrics` endpoint you will see the collected data, and if you visit the other endpoints and then reload the metrics endpoint, you will see the updated data 🎊

``` title="localhost:8080/metrics"
# HELP http_request_duration_seconds documenting the metric..
# TYPE http_request_duration_seconds histogram
http_request_duration_seconds_bucket{le="0.005"} 0.0
http_request_duration_seconds_bucket{le="0.01"} 0.0
http_request_duration_seconds_bucket{le="0.025"} 0.0
http_request_duration_seconds_bucket{le="0.05"} 0.0
http_request_duration_seconds_bucket{le="0.1"} 0.0
http_request_duration_seconds_bucket{le="0.25"} 0.0
http_request_duration_seconds_bucket{le="0.5"} 0.0
http_request_duration_seconds_bucket{le="1"} 0.0
http_request_duration_seconds_bucket{le="2.5"} 0.0
http_request_duration_seconds_bucket{le="5"} 0.0
http_request_duration_seconds_bucket{le="10"} 0.0
http_request_duration_seconds_bucket{le="inf"} 0.0
http_request_duration_seconds_sum 0.0
http_request_duration_seconds_count 0.0
```

!!! tip

    `0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10` are the default bucket values for the `Histogram` and can be changed!

The final file should look like this:

```python title="quickstart.py"
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

### Loading a different Backend

The backend used by the metrics can be changed with the `load_backend` function. This changes where the information is stored and retrieved while leaving the api the same so that there is no difference between a single and a multiprocess use of the library.

This library includes the `MultiProcessRedisBackend`, a Backend that makes use of [Redis](https://redis.io/) to support multi process python applications. If you prefer to use something different, you can create your own backend by respecting the `Backend` protocol.

All we need to do to change from the `SingleProcessBackend`(used by default) to the `MultiProcessRedisBackend` is:

```python
from pytheus.backends import load_backend
from pytheus.backends.redis import MultiProcessRedisBackend

load_backend(
    backend_class=MultiProcessRedisBackend,
    backend_config={"host": "127.0.0.1", "port": 6379},
)
```

- `backend_class`: is the class respecting the `Backend` protocol that we want to use.
- `backend_config`: is the configuration that you want to pass to the class. It's a dictionary.

!!! tip

    It is also possible to define the values to be used with environment variables: `PYTHEUS_BACKEND_CLASS` & `PYTHEUS_BACKEND_CONFIG`

That's it! By adding these lines our metrics are now making use of redis and will work with multiple processes :)
