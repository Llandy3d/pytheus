from contextvars import ContextVar
from typing import TYPE_CHECKING, Dict, List, Optional, Union

import redis

if TYPE_CHECKING:
    from pytheus.backends.base import BackendConfig
    from pytheus.metrics import Sample, _Metric
    from pytheus.registry import Collector, Registry


EXPIRE_KEY_TIME = 3600  # 1 hour


pipeline_var: ContextVar[Optional[redis.client.Pipeline]] = ContextVar("pipeline", default=None)


class MultiProcessRedisBackend:
    """
    Provides a multi-process backend that uses Redis.
    Single dimension metrics will be stored as list (ex. Counter) while labelled
    metrics will be stored in an hash.
    Currently is very naive, and there is a lot of room for improvement.
    (ex. maybe store all dimensions in the same hash and be smart on retrieving everything...)
    """

    CONNECTION_POOL: Optional[redis.Redis] = None

    def __init__(
        self,
        config: "BackendConfig",
        metric: "_Metric",
        histogram_bucket: Optional[str] = None,
    ) -> None:
        self._key_name = metric._collector.name
        self._labels_hash = None
        self._histogram_bucket = histogram_bucket

        # keys for histograms are of type `myhisto:2.5`
        if histogram_bucket:
            self._key_name = f"{self._key_name}:{histogram_bucket}"

        # default labels
        joint_labels = None
        if metric._collector._default_labels_count:
            joint_labels = metric._collector._default_labels.copy()  # type: ignore
            if metric._labels:
                joint_labels.update(metric._labels)

        if joint_labels:
            self._labels_hash = "-".join(sorted(joint_labels.values()))
        elif metric._labels:
            self._labels_hash = "-".join(sorted(metric._labels.values()))

        if "key_prefix" in config:
            self._key_prefix = config["key_prefix"]
            self._key_name = f"{self._key_prefix}-{self._key_name}"

        # initialize the key in redis
        self._init_key()

    @classmethod
    def _initialize(cls, config: "BackendConfig") -> None:
        redis_config = config.copy()
        if "key_prefix" in redis_config:
            del redis_config["key_prefix"]

        cls.CONNECTION_POOL = redis.Redis(
            **redis_config,
            decode_responses=True,
        )
        cls.CONNECTION_POOL.ping()

    def _init_key(self) -> None:
        """
        If the key doesn't exist in redis we initialize it and set the expiry time.
        `incrbyfloat` & `hincrbyfloat` are used so if for any reason multiple clients try to
        initialize the same key, it will be idempotent.
        """
        assert self.CONNECTION_POOL is not None
        if not self.CONNECTION_POOL.exists(self._key_name):
            if self._labels_hash:
                self.CONNECTION_POOL.hincrbyfloat(self._key_name, self._labels_hash, 0.0)
            else:
                self.CONNECTION_POOL.incrbyfloat(self._key_name, 0.0)

        self.CONNECTION_POOL.expire(self._key_name, EXPIRE_KEY_TIME)

    @classmethod
    def _initialize_pipeline(cls) -> None:
        assert cls.CONNECTION_POOL is not None
        assert pipeline_var.get() is None
        pipeline = cls.CONNECTION_POOL.pipeline()
        pipeline_var.set(pipeline)

    @staticmethod
    def _execute_and_cleanup_pipeline() -> List[Optional[Union[float, bool]]]:
        pipeline = pipeline_var.get()
        assert pipeline is not None
        pipeline_var.set(None)
        return pipeline.execute()

    @classmethod
    def _generate_samples(cls, registry: "Registry") -> Dict["Collector", List["Sample"]]:
        cls._initialize_pipeline()

        # collect samples that are not yet stored with the value
        samples_dict = {}
        for collector in registry.collect():
            samples_list: List[Sample] = []
            samples_dict[collector] = samples_list
            # collecting also builds requests in the pipeline
            for sample in collector.collect():
                samples_list.append(sample)

        pipeline_data = cls._execute_and_cleanup_pipeline()
        values = [
            0 if item is None else item for item in pipeline_data if item not in (True, False)
        ]

        # assign correct values to the samples
        for samples in samples_dict.values():
            owned_values = values[: len(samples)]
            values = values[len(samples) :]

            for sample, value in zip(samples, owned_values):
                sample.value = value
        return samples_dict

    def inc(self, value: float) -> None:
        assert self.CONNECTION_POOL is not None
        if self._labels_hash:
            self.CONNECTION_POOL.hincrbyfloat(self._key_name, self._labels_hash, value)
        else:
            self.CONNECTION_POOL.incrbyfloat(self._key_name, value)

        self.CONNECTION_POOL.expire(self._key_name, EXPIRE_KEY_TIME)

    def dec(self, value: float) -> None:
        assert self.CONNECTION_POOL is not None
        if self._labels_hash:
            self.CONNECTION_POOL.hincrbyfloat(self._key_name, self._labels_hash, -value)
        else:
            self.CONNECTION_POOL.incrbyfloat(self._key_name, -value)

        self.CONNECTION_POOL.expire(self._key_name, EXPIRE_KEY_TIME)

    def set(self, value: float) -> None:
        assert self.CONNECTION_POOL is not None
        if self._labels_hash:
            self.CONNECTION_POOL.hset(self._key_name, self._labels_hash, value)
        else:
            self.CONNECTION_POOL.set(self._key_name, value)

        self.CONNECTION_POOL.expire(self._key_name, EXPIRE_KEY_TIME)

    def get(self) -> float:
        assert self.CONNECTION_POOL is not None
        client = self.CONNECTION_POOL

        pipeline = pipeline_var.get()
        if pipeline:
            client = pipeline

        if self._labels_hash:
            value = client.hget(self._key_name, self._labels_hash)
        else:
            value = client.get(self._key_name)

        client.expire(self._key_name, EXPIRE_KEY_TIME)

        if pipeline:
            return 0.0

        # NOTE: get() directly is only used when collecting metrics & in tests so it makes sense
        # to consider adding a method only for tests
        return float(value) if value else 0.0
