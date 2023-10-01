"""
Attempts to patch `prometheus_client` so that it uses the internal pieces from pytheus making it
easier to just try it out.
I just need to try some things without changing a whole internal library first :)

1. Configure pytheus
2. Call `patch_client`
3. ?
"""
from pytheus.experimental.adapters import (
    CollectorRegistryAdapter,
    CounterAdapter,
    GaugeAdapter,
    HistogramAdapter,
    SummaryAdapter,
)
from pytheus.exposition import generate_metrics

default_global_registry = CollectorRegistryAdapter()

patches = {
    # registry
    "REGISTRY": default_global_registry,
    "CollectorRegistry": CollectorRegistryAdapter,
    # metrics
    "Counter": CounterAdapter,
    "Gauge": GaugeAdapter,
    "Histogram": HistogramAdapter,
    "Summary": SummaryAdapter,
    # misc
    "generate_latest": generate_metrics,
}


def patch_client(client) -> None:  # type: ignore
    for target, substitute in patches.items():
        setattr(client, target, substitute)
