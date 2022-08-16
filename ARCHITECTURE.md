# Architecture

## Metrics

For the metrics we have a `MetricCollector` class that is the core logic for a specific named metric.
It will do label validation, it will have the metric name and most importantly it will keep track of all the Child instances so that when `collect()` is called it will retrieve all the correct samples from all the possible observable Childrens.

Subclasses of `Metric` (ex. `Counter`) are what prometheus calls Child, a cacheable instance that provides access to a labeled dimension metric.
This means that you can have as many instances of `Metric` as you want for any combination of labels value. Getting one of this instances is achieved by calling `labels()`.
Beside giving you access to labeled dimensions:
  - it will add them automatically to the `MetricCollector`
  - it will know if itself is observable
  - it will provide a `collect()` to retrieve its `Sample`

*Note*: this class checkes all the boxes to be a `Protocol`, currently is not done for testing purposes but should be considered as a `Metric` shouldn't be instantiated directly.

## Registry

The `CollectorRegistry` class is the default global collector that will keep track of all the created metrics and it's the object that will work on collecting all the samples that possibly can be used for exposing those metrics.
A `MetricCollector` should be able to `register()` itself into it.
The `collect()` method will hold the logic for collecting all the metrics samples and should combine each metric name with the samples `suffixes` if present before exposing them. (This last bit might not be part of the registry directly, but of the piece that will actually work on formatting the metrics for exposure)