from typing import Any, Iterable, Optional, Sequence

from pytheus.metrics import Histogram, _Metric
from pytheus.registry import REGISTRY, Registry


def _build_name(name: str, namespace: str, subsystem: str) -> str:
    merged_name = ""
    if namespace:
        merged_name += f"{namespace}_"
    if subsystem:
        merged_name += f"{subsystem}_"
    merged_name += name

    return merged_name


class HistogramAdapter:
    def __init__(
        self,
        name: str,
        documentation: str,
        labelnames: Optional[Iterable[str]] = None,
        namespace: str = "",
        subsystem: str = "",
        registry: Optional[Registry] = REGISTRY,
        # NOTE: the library accepts str, we only accept floats
        buckets: Sequence[float] = Histogram.DEFAULT_BUCKETS,
        _pytheus_metric: Optional[_Metric] = None,
    ) -> None:
        self._labelnames = sorted(labelnames) if labelnames else None
        self._has_labels = False

        if _pytheus_metric:
            self._pytheus_histogram = _pytheus_metric
            self._has_labels = True
        else:
            self._pytheus_histogram = Histogram(
                _build_name(name, namespace, subsystem),
                description=documentation,
                required_labels=self._labelnames,
                registry=registry,
                buckets=buckets,
            )

    def observe(self, value: float) -> None:
        self._pytheus_histogram.observe(value)  # type: ignore

    def labels(self, *labelvalues: Any, **labelkwargs: Any) -> "HistogramAdapter":
        if not self._labelnames:
            raise ValueError("No label names were set when constructing %s" % self)

        if self._has_labels:
            raise ValueError(f"{self} already has labels set.; can not chain calls to .labels()")

        if labelvalues and labelkwargs:
            raise ValueError("Can't pass both *args and **kwargs")

        if labelkwargs:
            if sorted(labelkwargs) != sorted(self._labelnames):
                raise ValueError("Incorrect label names")
            labelvalues = tuple(str(labelkwargs[label]) for label in self._labelnames)
        else:
            if len(labelvalues) != len(self._labelnames):
                raise ValueError("Incorrect label count")
            labelvalues = tuple(str(label) for label in labelvalues)

        labels = {key: value for key, value in zip(self._labelnames, labelvalues)}
        new_pytheus_metric = self._pytheus_histogram.labels(labels)
        return HistogramAdapter(
            name="",
            documentation="",
            labelnames=self._labelnames,
            _pytheus_metric=new_pytheus_metric,
        )
