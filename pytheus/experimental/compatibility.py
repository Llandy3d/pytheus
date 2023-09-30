"""
Attempts to patch `prometheus_client` so that it uses the internal pieces from pytheus making it
easier to just try it out.
I just need to try some things without changing a whole internal library first :)

1. Configure pytheus
2. Call `patch_client`
3. ?
"""
from pytheus.experimental.adapters import HistogramAdapter
from pytheus.exposition import generate_metrics
from pytheus.metrics import Counter, Gauge, Summary
from pytheus.registry import REGISTRY, CollectorRegistry

"""
from pytheus.registry import REGISTRY, CollectorRegistry

from pytheus.metrics import Counter, Gauge, Summary

from pytheus.exposition import generate_metrics
"""

# TODO:  need adapters :(

# CounterMetricFamily ???

# exposition.MetricsHandler needs patching on .registry ??

patches = {
    # registry
    "REGISTRY": REGISTRY,
    "CollectorRegistry": CollectorRegistry,
    # metrics
    "Counter": Counter,
    "Gauge": Gauge,
    "Histogram": HistogramAdapter,
    "Summary": Summary,
    # misc
    "generate_latest": generate_metrics,
}


def patch_client(client) -> None:  # type: ignore
    for target, substitute in patches.items():
        setattr(client, target, substitute)
