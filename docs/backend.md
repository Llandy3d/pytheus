# Backend / Multiprocessing

This is an important part of the library designed to make the switch from single process to multi process monitoring extremely simple without requiring changes from the user beside a configuration.

`Backend` is a protocol used for each value of a metric, meaning that when you create a `Counter` for example, its actual value will be an instance of a `Backend` that will handle the logic for that value. For single process it could be a mutex based implementation while for multi process it could be a redis backed one.

Regardless of backend used, if you want to increment the `Counter` you would call the same `inc()` method, so that you can easily switch between single and multi process with ease.

!!! note

    One of my goals for this library is to have the interface be the same between single & multi process, meaning that the features supported should always handle both cases.
