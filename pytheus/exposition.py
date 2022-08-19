import os
from typing import Callable

from pytheus import registry as internal_regisry
from pytheus.metrics import Labels
from pytheus.registry import Collector, Registry

LINE_SEPARATOR = os.linesep
LABEL_SEPARATOR = ","
PROMETHEUS_CONTENT_TYPE = "text/plain; version=0.0.4; charset=utf-8"


def generate_metrics(registry: Registry = None) -> str:
    """
    Returns the metrics from the registry in prometheus text format
    """

    if not registry:
        registry = internal_regisry.REGISTRY

    lines = (
        generate_from_collector(collector, registry.prefix)
        for collector in registry.collect()
    )
    output = LINE_SEPARATOR.join(lines)
    output += "\n"
    return output


def format_labels(labels: Labels) -> str:
    label_str = (f'{name}="{value}"' for name, value in labels.items())
    return f"{{{LABEL_SEPARATOR.join(label_str)}}}"


def generate_from_collector(collector: Collector, prefix: str = None) -> str:
    """
    Returns the metrics from a given collector in prometheus text format
    """
    metric_name = f'{prefix}_{collector.name}' if prefix else collector.name
    help_text = f"# HELP {metric_name} {collector.description}"
    type_text = f"# TYPE {metric_name} {collector.type_}"
    output = [help_text, type_text]

    for sample in collector.collect():
        labelstr = format_labels(sample.labels)
        metric = f"{metric_name}{sample.suffix}{labelstr} {sample.value}"
        output.append(metric)
    return LINE_SEPARATOR.join(output)


def make_wsgi_app(registry: Registry = None) -> Callable:
    """Create a WSGI app which serves the metrics from a registry."""
    if not registry:
        registry = internal_regisry.REGISTRY

    def prometheus_app(environ, start_response):
        status = '200 OK'
        if environ['PATH_INFO'] == '/favicon.ico':
            # Serve empty response for browsers
            headers = [('', '')]
            output = ''
        else:
            output = generate_metrics(registry)
            headers = [('Content-Type', PROMETHEUS_CONTENT_TYPE)]
        start_response(status, headers)
        return [output.encode()]

    return prometheus_app
