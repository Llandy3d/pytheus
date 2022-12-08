import time
from flask import Flask
from pytheus.metrics import Counter, Histogram
from pytheus.exposition import generate_metrics


app = Flask(__name__)


histogram = Histogram('page_visits_latency_seconds', 'used for testing')
# counter = Counter('page_visits_total', 'total number of page visits')


@app.route('/metrics')
def metrics():
    return generate_metrics()


@app.route('/')
def home():
    with histogram.time():
        return 'hello world!'


@app.route('/slow')
def slow():
    with histogram.time():
        time.sleep(3)
        return 'hello world! from slow!'


app.run(host='0.0.0.0', port=8080)
