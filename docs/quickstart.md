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
