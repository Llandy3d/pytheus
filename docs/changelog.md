# Changelog

## Unreleased

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
