# Changelog

## Unreleased

- New improved implementation of `_generate_samples` for `MultiProcessRedisBackend`:
    - Improved performance for generating metrics
    - Fixed a bug where on multiprocess on some scrapes a metric wouldn't be picked up due to missing local collector child
    - Now on labeled metrics, the labels/value combination will be initialized to 0 if it doesn't exists (before only the key would be initialized)

- Redis keys expire time can now be configured via the `expire_key_time` config passed when loading the backend

- Experimental `prometheus_client` patching in-place to quickly test the library on existing codebases

- **DEPRECATED**: `key_prefix` for redis configuration. Prefer a side-car container or a separate redis/redis db per service.

## 0.4.0

- python 3.12 support

## 0.3.0

- fix `generate_metrics` to handle custom collectors

## 0.2.0

- `kwargs` (keyword arguments) support for the `labels()` method.
   ```python
   metric = Counter("counter", "desc", required_labels=["method"])

   # dict approach
   metric.labels({"method": "POST"})

   # kwargs approach
   metric.labels(method="POST")

   ```

## 0.1.0

- asgi middleware for `FastAPI` support

## 0.0.16

- add `Summary` metric type

## 0.0.15

- add support for python `3.8` & `3.9`

## 0.0.14

- decorator support for async functions

## 0.0.13

- Support for `_generate_samples` in Backend
- MultiProcessRedisBackend:
    - Improved scraping performance via pipelining

## 0.0.12

- Escape `help` & `label_values` during exposition
- MultiProcessRedisBackend:
    - Add `key_prefix` config to specify stored key name prefix.

## 0.0.11

- MultiProcessRedisBackend:
    - handle `get` with unexpected key deletion

## 0.0.10

- MultiProcessRedisBackend:
    - initialize `key` on redis on instantiation
    - update expiry when retrieving a key

## 0.0.9

- The `inf` histogram bucket label will now be exported as `+Inf` in line with the other clients

## 0.0.8

- `Histogram` now passes custom buckets to child instances

## 0.0.7

- fix `MetricType` string representation for python 3.11

## 0.0.6

First release ready to be tested 🎉

Redis multiprocess backend support still experimental.
