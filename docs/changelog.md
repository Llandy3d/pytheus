# Changelog

## Unreleased

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
