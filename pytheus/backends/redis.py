import redis

from typing import TYPE_CHECKING

from pytheus.backends.base import Backend, BackendConfig


if TYPE_CHECKING:
    from pytheus.metrics import _Metric

class MultipleProcessRedisBackend(Backend):
    """
    Provides a multi-process backend that uses Redis.
    Single dimension metrics will be stored as list (ex. Counter) while labelled
    metrics will be stored in an hash.
    Currently is very naive, and there is a lot of room for improvement.
    (ex. maybe store all dimensions in the same hash and be smart on retrieving everything...)
    Note: currently not expiring keys
    """

    CONNECTION_POOL: redis.Redis = None

    def __init__(self, config: BackendConfig, metric: '_Metric') -> None:
        super().__init__(config, metric)
        self._key_name = self.metric._collector.name
        self._labels_hash = None
        if self.metric._labels:
            self._labels_hash = '-'.join(sorted(self.metric._labels.values()))

        if self.CONNECTION_POOL is None:
            MultipleProcessRedisBackend.CONNECTION_POOL = redis.Redis(
                **config,
                decode_responses=True,
            )

    def is_valid_config(self, config: BackendConfig) -> bool:
        return True  # TODO

    def inc(self, value: float) -> None:
        if self._labels_hash:
            self.CONNECTION_POOL.hincrbyfloat(self._key_name, self._labels_hash, value)
        else:
            self.CONNECTION_POOL.incrbyfloat(self._key_name, value)

    def dec(self, value: float) -> None:
        if self._labels_hash:
            self.CONNECTION_POOL.hincrbyfloat(self._key_name, self._labels_hash, -value)
        else:
            self.CONNECTION_POOL.incrbyfloat(self._key_name, -value)

    def set(self, value: float) -> None:
        if self._labels_hash:
            self.CONNECTION_POOL.hset(self._key_name, self._labels_hash, value)
        else:
            self.CONNECTION_POOL.set(self._key_name, value)

    def get(self) -> float:
        if self._labels_hash:
            value = self.CONNECTION_POOL.hget(self._key_name, self._labels_hash)
        else:
            value = self.CONNECTION_POOL.get(self._key_name)
        return float(value) if value else 0.0
