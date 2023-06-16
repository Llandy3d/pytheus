# Tutorial / FastAPI

!!! warning

    **[WIP tutorial]**

The library offers a middleware that can be added to a FastAPI project to automatically get some metrics making it dead simple to get useful information at a low effort cost.

## The middleware

The `PytheusMiddlewareASGI` when added to the project will collect three metrics:

- `http_request_duration_seconds`: the duration of the http request
- `http_request_size_bytes`: size in bytes of the request
- `http_response_size_bytes`: size in bytes of the response

These will have three labels: `method`, `path` & `status_code` allowing for a lot of flexibility on observing your system. For example seeing the duration of `GET` requests to the `/api` path with a `status_code` of `200`.

!!! note

    `http_request_size_bytes` for now depends on the availability of the `Content-Length` header in the request.

## Using the middleware

In the file where you are creating your FastAPI application import and add the middleware:

```python
from fastapi import FastAPI
from pytheus.middleware import PytheusMiddlewareASGI


app = FastAPI()
app.add_middleware(PytheusMiddlewareASGI)
```

that will take care of collecting the metrics!

---

Now, we just need to decide where to expose the metrics, this is usually a `/metrics` endpoint:

```python
from fastapi.responses import PlainTextResponse
from pytheus.exposition import generate_metrics


@app.get('/metrics', response_class=PlainTextResponse)
async def pytheus_metrics():
    return generate_metrics()
```

That's it!

---

If you visit the `/metrics` endpoint twice you will able to see metrics for that request:

```
# HELP http_request_duration_seconds duration of the http request
# TYPE http_request_duration_seconds histogram
http_request_duration_seconds_bucket{method="GET",route="/metrics",status_code="200",le="0.005"} 1.0
http_request_duration_seconds_bucket{method="GET",route="/metrics",status_code="200",le="0.01"} 1.0
http_request_duration_seconds_bucket{method="GET",route="/metrics",status_code="200",le="0.025"} 1.0
http_request_duration_seconds_bucket{method="GET",route="/metrics",status_code="200",le="0.05"} 1.0
http_request_duration_seconds_bucket{method="GET",route="/metrics",status_code="200",le="0.1"} 1.0
http_request_duration_seconds_bucket{method="GET",route="/metrics",status_code="200",le="0.25"} 1.0
http_request_duration_seconds_bucket{method="GET",route="/metrics",status_code="200",le="0.5"} 1.0
http_request_duration_seconds_bucket{method="GET",route="/metrics",status_code="200",le="1"} 1.0
http_request_duration_seconds_bucket{method="GET",route="/metrics",status_code="200",le="2.5"} 1.0
http_request_duration_seconds_bucket{method="GET",route="/metrics",status_code="200",le="5"} 1.0
http_request_duration_seconds_bucket{method="GET",route="/metrics",status_code="200",le="10"} 1.0
http_request_duration_seconds_bucket{method="GET",route="/metrics",status_code="200",le="+Inf"} 1.0
http_request_duration_seconds_sum{method="GET",route="/metrics",status_code="200"} 0.0014027919969521463
http_request_duration_seconds_count{method="GET",route="/metrics",status_code="200"} 1.0
# HELP http_request_size_bytes http request size
# TYPE http_request_size_bytes histogram
# HELP http_response_size_bytes http response size
# TYPE http_response_size_bytes histogram
http_response_size_bytes_bucket{method="GET",route="/metrics",status_code="200",le="10.0"} 0.0
http_response_size_bytes_bucket{method="GET",route="/metrics",status_code="200",le="100.0"} 0.0
http_response_size_bytes_bucket{method="GET",route="/metrics",status_code="200",le="1000.0"} 1.0
http_response_size_bytes_bucket{method="GET",route="/metrics",status_code="200",le="10000.0"} 1.0
http_response_size_bytes_bucket{method="GET",route="/metrics",status_code="200",le="100000.0"} 1.0
http_response_size_bytes_bucket{method="GET",route="/metrics",status_code="200",le="1000000.0"} 1.0
http_response_size_bytes_bucket{method="GET",route="/metrics",status_code="200",le="10000000.0"} 1.0
http_response_size_bytes_bucket{method="GET",route="/metrics",status_code="200",le="100000000.0"} 1.0
http_response_size_bytes_bucket{method="GET",route="/metrics",status_code="200",le="+Inf"} 1.0
http_response_size_bytes_sum{method="GET",route="/metrics",status_code="200"} 296.0
http_response_size_bytes_count{method="GET",route="/metrics",status_code="200"} 1.0
```

!!! note

    You will need to hit `/metrics` twice because the first time on a fresh start you won't have metrics. On the second request you will see metrics from the previous request.

## TODO: prometheus scraping target & grafana dashboard
