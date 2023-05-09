from typing import TYPE_CHECKING

import redis

if TYPE_CHECKING:
    from pytheus.backends.base import BackendConfig
    from pytheus.metrics import _Metric


EXPIRE_KEY_TIME = 3600  # 1 hour


from contextvars import ContextVar

pipeline_var = ContextVar("pipeline", default=None)


class MultiProcessRedisBackend:
    """
    Provides a multi-process backend that uses Redis.
    Single dimension metrics will be stored as list (ex. Counter) while labelled
    metrics will be stored in an hash.
    Currently is very naive, and there is a lot of room for improvement.
    (ex. maybe store all dimensions in the same hash and be smart on retrieving everything...)
    """

    CONNECTION_POOL: redis.Redis | None = None

    def __init__(
        self,
        config: "BackendConfig",
        metric: "_Metric",
        histogram_bucket: str | None = None,
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
    def _initialize_pipeline(cls):  # TODO: type hint
        assert pipeline_var.get() is None
        pipeline = cls.CONNECTION_POOL.pipeline()
        pipeline_var.set(pipeline)

    @staticmethod
    def _execute_and_cleanup_pipeline():  # TODO: type hint
        pipeline = pipeline_var.get()
        pipeline_var.set(None)
        return pipeline.execute()

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
        pipeline = pipeline_var.get()
        if pipeline:
            pass

        assert self.CONNECTION_POOL is not None
        if self._labels_hash:
            # value = self.CONNECTION_POOL.hget(self._key_name, self._labels_hash)
            pipeline.hget(self._key_name, self._labels_hash)
        else:
            # value = self.CONNECTION_POOL.get(self._key_name)
            pipeline.get(self._key_name)

        # if not value:
        #     self._init_key()
        #     return 0.0

        # self.CONNECTION_POOL.expire(self._key_name, EXPIRE_KEY_TIME)
        pipeline.expire(self._key_name, EXPIRE_KEY_TIME)
        # return float(value)
        return 0
