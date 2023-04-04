from typing import TYPE_CHECKING

import redis

if TYPE_CHECKING:
    from pytheus.backends.base import BackendConfig
    from pytheus.metrics import _Metric


EXPIRE_KEY_TIME = 3600  # 1 hour


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

    @classmethod
    def _initialize(cls, config: "BackendConfig") -> None:
        cls.CONNECTION_POOL = redis.Redis(
            **config,
            decode_responses=True,
        )
        cls.CONNECTION_POOL.ping()

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
        if self._labels_hash:
            value = self.CONNECTION_POOL.hget(self._key_name, self._labels_hash)
        else:
            value = self.CONNECTION_POOL.get(self._key_name)
        return float(value) if value else 0.0
