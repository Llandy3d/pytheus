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
