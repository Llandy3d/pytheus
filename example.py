import time

from flask import Flask, Response

from pytheus.backends import load_backend
from pytheus.backends.redis import MultiProcessRedisBackend
from pytheus.exposition import PROMETHEUS_CONTENT_TYPE, generate_metrics
from pytheus.metrics import Histogram

load_backend(
    backend_class=MultiProcessRedisBackend,
    backend_config={"host": "127.0.0.1", "port": 6379},
)


app = Flask(__name__)


histogram = Histogram("page_visits_latency_seconds", "used for testing")
histogram_labeled = Histogram(
    "page_visits_latency_seconds_labeled",
    "used for testing",
    required_labels=["speed"],
    default_labels={"speed": "normal"},
)


@app.route("/metrics")
def metrics():
    data = generate_metrics()
    return Response(data, headers={"Content-Type": PROMETHEUS_CONTENT_TYPE})


# track time with the context manager
@app.route("/")
def home():
    with histogram.time():
        with histogram_labeled.time():
            return "hello world!"


# you can also track time with the decorator shortcut
@app.route("/slow")
@histogram
@histogram_labeled.labels({"speed": "slow"})
def slow():
    time.sleep(3)
    return "hello world! from slow!"


app.run(host="0.0.0.0", port=8080)
