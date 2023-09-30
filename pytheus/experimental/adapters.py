import time
from typing import Any, Callable, Iterable, Optional, Sequence, Tuple, Type, Union

from pytheus.metrics import Counter, Gauge, Histogram, _Metric
from pytheus.registry import REGISTRY, Registry


def _build_name(name: str, namespace: str, subsystem: str) -> str:
    merged_name = ""
    if namespace:
        merged_name += f"{namespace}_"
    if subsystem:
        merged_name += f"{subsystem}_"
    merged_name += name

    return merged_name


def _get_pytheus_metric_from_labels(
    instance: Any,
    labelvalues: Any,
    labelkwargs: Any,
    _labelnames: Optional[Sequence[str]],
    _has_labels: bool,
    _pytheus_metric: _Metric,
) -> _Metric:
    pass

    if not _labelnames:
        raise ValueError("No label names were set when constructing %s" % instance)

    if _has_labels:
        raise ValueError(f"{instance} already has labels set.; can not chain calls to .labels()")

    if labelvalues and labelkwargs:
        raise ValueError("Can't pass both *args and **kwargs")

    if labelkwargs:
        if sorted(labelkwargs) != sorted(_labelnames):
            raise ValueError("Incorrect label names")
        labelvalues = tuple(str(labelkwargs[label]) for label in _labelnames)
    else:
        if len(labelvalues) != len(_labelnames):
            raise ValueError("Incorrect label count")
        labelvalues = tuple(str(label) for label in labelvalues)

    labels = {key: value for key, value in zip(_labelnames, labelvalues)}

    # NOTE: here we return new Adapters even for the same labels but the underlying
    # pytheus metric will correctly handle sharing child instances
    return _pytheus_metric.labels(labels)


class DecoratorContextManagerAdapter:
    """
    Please don't judge me.
    """

    def __init__(self, _pytheus_metric: _Metric, _func: str, *args: Any) -> None:
        self._pytheus_metric = _pytheus_metric
        self._func = _func
        self._args = args
        self._pytheus_contextmanager = None

    def __enter__(self):  # type: ignore
        func = getattr(self._pytheus_metric, self._func)
        if self._args:
            self._pytheus_contextmanager = func(self._args)
        else:
            self._pytheus_contextmanager = func()
        self._pytheus_contextmanager.__enter__()

    def __exit__(self, typ, value, traceback):  # type: ignore
        self._pytheus_contextmanager.__exit__(typ, value, traceback)
        pass

    def __call__(self, f: Callable[..., Any]) -> Callable[..., Any]:
        if self._func == "track_inprogress":
            return self._pytheus_metric.__call__(f, track_inprogress=True)  # type: ignore
        else:
            return self._pytheus_metric.__call__(f)  # type: ignore


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
            self._pytheus_metric = _pytheus_metric
            self._has_labels = True
        else:
            self._pytheus_metric = Histogram(
                _build_name(name, namespace, subsystem),
                description=documentation,
                required_labels=self._labelnames,
                registry=registry,
                buckets=buckets,
            )

    def observe(self, amount: float) -> None:
        self._pytheus_metric.observe(amount)  # type: ignore

    def time(self) -> DecoratorContextManagerAdapter:
        return DecoratorContextManagerAdapter(self._pytheus_metric, "time")

    def labels(self, *labelvalues: Any, **labelkwargs: Any) -> "HistogramAdapter":
        new_pytheus_metric = _get_pytheus_metric_from_labels(
            self,
            labelvalues,
            labelkwargs,
            self._labelnames,
            self._has_labels,
            self._pytheus_metric,
        )
        return HistogramAdapter(
            name="",
            documentation="",
            labelnames=self._labelnames,
            _pytheus_metric=new_pytheus_metric,
        )


class CounterAdapter:
    def __init__(
        self,
        name: str,
        documentation: str,
        labelnames: Optional[Iterable[str]] = None,
        namespace: str = "",
        subsystem: str = "",
        registry: Optional[Registry] = REGISTRY,
        _pytheus_metric: Optional[_Metric] = None,
    ) -> None:
        self._labelnames = sorted(labelnames) if labelnames else None
        self._has_labels = False

        if _pytheus_metric:
            self._pytheus_metric = _pytheus_metric
            self._has_labels = True
        else:
            self._pytheus_metric = Counter(
                _build_name(name, namespace, subsystem),
                description=documentation,
                required_labels=self._labelnames,
                registry=registry,
            )

    def inc(self, amount: float = 1) -> None:
        self._pytheus_metric.inc(amount)  # type: ignore

    def count_exceptions(
        self, exception: Union[Type[BaseException], Tuple[Type[BaseException], ...]] = Exception
    ) -> DecoratorContextManagerAdapter:
        return DecoratorContextManagerAdapter(self._pytheus_metric, "count_exceptions", exception)

    def labels(self, *labelvalues: Any, **labelkwargs: Any) -> "CounterAdapter":
        new_pytheus_metric = _get_pytheus_metric_from_labels(
            self,
            labelvalues,
            labelkwargs,
            self._labelnames,
            self._has_labels,
            self._pytheus_metric,
        )
        return CounterAdapter(
            name="",
            documentation="",
            labelnames=self._labelnames,
            _pytheus_metric=new_pytheus_metric,
        )


class GaugeAdapter:
    def __init__(
        self,
        name: str,
        documentation: str,
        labelnames: Optional[Iterable[str]] = None,
        namespace: str = "",
        subsystem: str = "",
        registry: Optional[Registry] = REGISTRY,
        _pytheus_metric: Optional[_Metric] = None,
    ) -> None:
        self._labelnames = sorted(labelnames) if labelnames else None
        self._has_labels = False

        if _pytheus_metric:
            self._pytheus_metric = _pytheus_metric
            self._has_labels = True
        else:
            self._pytheus_metric = Gauge(
                _build_name(name, namespace, subsystem),
                description=documentation,
                required_labels=self._labelnames,
                registry=registry,
            )

    def inc(self, amount: float = 1) -> None:
        self._pytheus_metric.inc(amount)  # type: ignore

    def dec(self, amount: float = 1) -> None:
        self._pytheus_metric.dec(amount)  # type: ignore

    def set(self, amount: float) -> None:
        self._pytheus_metric.set(amount)  # type: ignore

    def set_to_current_time(self) -> None:
        self.set(time.time())

    def track_inprogress(self) -> DecoratorContextManagerAdapter:
        return DecoratorContextManagerAdapter(self._pytheus_metric, "track_inprogress")

    def time(self) -> DecoratorContextManagerAdapter:
        return DecoratorContextManagerAdapter(self._pytheus_metric, "time")

    def labels(self, *labelvalues: Any, **labelkwargs: Any) -> "GaugeAdapter":
        new_pytheus_metric = _get_pytheus_metric_from_labels(
            self,
            labelvalues,
            labelkwargs,
            self._labelnames,
            self._has_labels,
            self._pytheus_metric,
        )
        return GaugeAdapter(
            name="",
            documentation="",
            labelnames=self._labelnames,
            _pytheus_metric=new_pytheus_metric,
        )
