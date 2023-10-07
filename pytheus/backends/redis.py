import json
from typing import TYPE_CHECKING, Dict, List, Optional

import redis

from pytheus.metrics import Sample
from pytheus.utils import MetricType

if TYPE_CHECKING:
    from pytheus.backends.base import BackendConfig
    from pytheus.metrics import _Metric
    from pytheus.registry import Collector, Registry


EXPIRE_KEY_TIME = 3600  # 1 hour


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
        self._sorted_required_labels = (
            sorted(metric._collector._required_labels)
            if metric._collector._required_labels
            else None
        )

        if not metric._collector._redis_key_name:
            metric._collector._redis_key_name = self._key_name

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
            self._labels_hash = json.dumps(joint_labels)
        elif metric._labels:
            self._labels_hash = json.dumps(metric._labels)

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

        if self._labels_hash and not self.CONNECTION_POOL.hexists(
            self._key_name, self._labels_hash
        ):
            self.CONNECTION_POOL.hincrbyfloat(self._key_name, self._labels_hash, 0.0)

        elif not self._labels_hash and not self.CONNECTION_POOL.exists(self._key_name):
            self.CONNECTION_POOL.incrbyfloat(self._key_name, 0.0)

        self.CONNECTION_POOL.expire(self._key_name, EXPIRE_KEY_TIME)

    @classmethod
    def _generate_samples(cls, registry: "Registry") -> Dict["Collector", List["Sample"]]:
        # cls._initialize_pipeline()
        assert cls.CONNECTION_POOL is not None

        # collect samples that are not yet stored with the value
        samples_dict = {}
        pipeline = cls.CONNECTION_POOL.pipeline()
        for collector in registry.collect():
            samples_list: List[Sample] = []
            samples_dict[collector] = samples_list

            key_name = collector._redis_key_name
            if collector._required_labels:
                # hash
                match collector.type_:
                    case MetricType.COUNTER | MetricType.GAUGE:
                        pipeline.expire(key_name, EXPIRE_KEY_TIME)
                        pipeline.hgetall(key_name)
                    case MetricType.SUMMARY:
                        for suffix in ("count", "sum"):
                            key_with_suffix = f"{key_name}:{suffix}"
                            pipeline.expire(key_with_suffix, EXPIRE_KEY_TIME)
                            pipeline.hgetall(key_with_suffix)
                    case MetricType.HISTOGRAM:
                        for suffix in collector._metric._upper_bounds[:-1] + [
                            "+Inf",
                            "count",
                            "sum",
                        ]:
                            key_with_suffix = f"{key_name}:{suffix}"
                            pipeline.expire(key_with_suffix, EXPIRE_KEY_TIME)
                            pipeline.hgetall(key_with_suffix)
            else:
                # not hash
                match collector.type_:
                    case MetricType.COUNTER | MetricType.GAUGE:
                        pipeline.expire(key_name, EXPIRE_KEY_TIME)
                        pipeline.get(key_name)
                    case MetricType.SUMMARY:
                        for suffix in ("count", "sum"):
                            key_with_suffix = f"{key_name}:{suffix}"
                            pipeline.expire(key_with_suffix, EXPIRE_KEY_TIME)
                            pipeline.get(key_with_suffix)
                    case MetricType.HISTOGRAM:
                        for suffix in collector._metric._upper_bounds[:-1] + [
                            "+Inf",
                            "count",
                            "sum",
                        ]:
                            key_with_suffix = f"{key_name}:{suffix}"
                            pipeline.expire(key_with_suffix, EXPIRE_KEY_TIME)
                            pipeline.get(key_with_suffix)

        pipeline_data = pipeline.execute()

        values = [
            0 if item is None else item for item in pipeline_data if item not in (True, False)
        ]

        # build samples
        for collector, samples_list in samples_dict.items():
            if collector._required_labels:
                # hash
                match collector.type_:
                    case MetricType.COUNTER | MetricType.GAUGE:
                        values_dict = values[0]
                        values = values[1:]
                        for labels, value in values_dict.items():
                            samples_list.append(Sample("", json.loads(labels), float(value)))
                    case MetricType.SUMMARY:
                        count_dict = values[0]
                        sum_dict = values[1]
                        values = values[2:]
                        for labels, value in count_dict.items():
                            samples_list.append(Sample("_count", json.loads(labels), float(value)))

                        for labels, value in sum_dict.items():
                            samples_list.append(Sample("_sum", json.loads(labels), float(value)))

                        # might be able to do something like this for order but is it safe ?
                        # count_dict = values[0]
                        # sum_dict = values[1]
                        # values = values[2:]
                        # for (labels_count, value_count),(labels_sum, value_sum)  in
                        # zip(count_dict.items(), sum_dict.items()):
                        #
                        #     samples_list.append(
                        #         Sample("_count", json.loads(labels_count), float(value_count))
                        #     )
                        #     samples_list.append(
                        #        Sample("_sum", json.loads(labels_sum), float(value_sum))
                        #    )
                    case MetricType.HISTOGRAM:
                        index = 0
                        suffixes = collector._metric._upper_bounds[:-1] + ["+Inf", "count", "sum"]
                        for suffix in suffixes:
                            values_dict = values[index]
                            index += 1

                            if isinstance(suffix, (int, float)) or suffix == "+Inf":
                                for labels, value in values_dict.items():
                                    labels = json.loads(labels)
                                    labels["le"] = str(suffix)
                                    samples_list.append(Sample("_bucket", labels, float(value)))
                            elif suffix == "count":
                                for labels, value in values_dict.items():
                                    samples_list.append(
                                        Sample("_count", json.loads(labels), float(value))
                                    )
                            elif suffix == "sum":
                                for labels, value in values_dict.items():
                                    samples_list.append(
                                        Sample("_sum", json.loads(labels), float(value))
                                    )

                        values = values[len(suffixes) :]
            else:
                match collector.type_:
                    case MetricType.COUNTER | MetricType.GAUGE:
                        value = values[0]
                        values = values[1:]
                        samples_list.append(Sample("", None, float(value)))
                    case MetricType.SUMMARY:
                        count_value = values[0]
                        sum_value = values[1]
                        values = values[2:]
                        samples_list.append(Sample("_count", None, float(count_value)))
                        samples_list.append(Sample("_sum", None, float(sum_value)))
                    case MetricType.HISTOGRAM:
                        index = 0
                        suffixes = collector._metric._upper_bounds[:-1] + ["+Inf", "count", "sum"]
                        for suffix in suffixes:
                            value = values[index]
                            index += 1

                            if isinstance(suffix, (int, float)) or suffix == "+Inf":
                                labels = {"le": str(suffix)}
                                samples_list.append(Sample("_bucket", labels, float(value)))
                            elif suffix == "count":
                                samples_list.append(Sample("_count", None, float(value)))
                            elif suffix == "sum":
                                samples_list.append(Sample("_sum", None, float(value)))

                        values = values[len(suffixes) :]

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
        """
        This is not used directly, useful for tests and possibly debugging so leaving it in but
        it's not used outside of these cases.
        """
        assert self.CONNECTION_POOL is not None

        if self._labels_hash:
            value = self.CONNECTION_POOL.hget(self._key_name, self._labels_hash)
        else:
            value = self.CONNECTION_POOL.get(self._key_name)

        self.CONNECTION_POOL.expire(self._key_name, EXPIRE_KEY_TIME)

        return float(value) if value else 0.0
