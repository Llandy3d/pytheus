# Rust powered Backend 🦀

🧪 An experimental backend written in Rust is available for multiprocess support for both sync & async applications.

This removes the need for the `redis` library dependency & allows the library to offer the same interface to either synchronous applications or asyncio based ones.

Under the hood a different thread will handle the change of values & pipeline requests, this makes it extremely fast to do operations like `inc()` on a metric in your application since it will always be handled asynchronously & in parallel.

---

## Usage

Installation:

```python
pip install pytheus-backend-rs
```

---

then just load it like you would do with any other backends:

```python
from pytheus_backend_rs import RedisBackend

load_backend(
    backend_class=RedisBackend,
    backend_config={"host": "127.0.0.1", "port": 6379},
)
```

!!! tip

    When calling `generate_metrics` it should be done in a `ThreadPool` for async applications.
    A framework like `FastAPI` does this automatically if your endpoint is defined as `def`.
    ```python
    @app.get('/metrics')
    def pytheus_metrics():
        return generate_metrics()
    ```

    The `GIL` gets released while waiting for the result so that other operations can run in parallel.

---

## Logs

Logs will be emitted about threads initialization and errors if they happen. (ex. impossible to connect to redis)

To see them just configure the python `logging` library, for example:

```python
import logging
logging.basicConfig(level=logging.INFO)
```

!!! note

    The logging needs to be setup before loading the backend with the `load_backend` function.

```
INFO:pytheus_backend_rs:Starting pipeline thread....0
INFO:pytheus_backend_rs:Starting pipeline thread....1
INFO:pytheus_backend_rs:Starting pipeline thread....2
INFO:pytheus_backend_rs:Starting pipeline thread....3
INFO:pytheus_backend_rs:Starting BackendAction thread....
INFO:pytheus_backend_rs:RedisBackend initialized
```

---

## Async

The Rust powered `RedisBackend` is safe to be used in `async` applications!

The only detail is that for now it is preferable to use the `generate_metrics` function inside a `ThreadPool` for such applications.
