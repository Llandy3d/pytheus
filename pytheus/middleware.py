import time
from typing import Any, Dict, Optional

from pytheus.metrics import Histogram


class PytheusMiddlewareASGI:
    def __init__(self, app) -> None:  # type: ignore
        self.app = app

        labels = ["method", "route", "status_code"]

        # 10 bytes -> 100 megabytes
        size_bytes_buckets = (
            10.0,
            100.0,
            1_000.0,
            10_000.0,
            100_000.0,
            1_000_000.0,
            10_000_000.0,
            100_000_000.0,
        )

        self.http_request_duration_seconds = Histogram(
            name="http_request_duration_seconds",
            description="duration of the http request",
            required_labels=labels,
        )
        self.http_request_size_bytes = Histogram(
            name="http_request_size_bytes",
            description="http request size",
            buckets=size_bytes_buckets,
            required_labels=labels,
        )
        self.http_response_size_bytes = Histogram(
            name="http_response_size_bytes",
            description="http response size",
            buckets=size_bytes_buckets,
            required_labels=labels,
        )

    async def __call__(self, scope, receive, send) -> None:  # type: ignore
        if scope["type"] == "http":
            start_request_duration = time.perf_counter()
            status_code: Optional[str]

            async def observed_send(event: Dict[str, Any]):  # type: ignore
                nonlocal status_code
                method = scope["method"]

                # get the generic route to reduce cardinality
                # for example from `/item/5` -> retrieves `/item/{item_id}`

                # `route` is added to the scope specifically by FastAPI, this won't be available
                # in other frameworks but it will be fine like this for now
                if "route" in scope:
                    route = scope["route"].path
                else:
                    # if it is not present, in FastAPI it means it is a 404
                    route = "404"

                if event["type"] == "http.response.start":
                    status_code = event["status"]
                    labels = {
                        "method": method,
                        "route": route,
                        "status_code": str(status_code),
                    }

                    # observe response size if we have a `content-length`
                    for name, value in event["headers"]:
                        if name.lower() == b"content-length":
                            try:
                                response_size = float(value)
                                self.http_response_size_bytes.labels(labels).observe(  # type:ignore
                                    response_size
                                )
                            except ValueError:
                                pass

                    # observe request size if we have a `content-length`
                    for name, value in scope["headers"]:
                        if name.lower() == b"content-length":
                            try:
                                request_size = float(value)
                                self.http_request_size_bytes.labels(labels).observe(  # type: ignore
                                    request_size
                                )
                            except ValueError:
                                pass

                    return await send(event)
                elif event["type"] == "http.response.body":
                    result = await send(event)
                    if not event.get("more_body"):
                        request_duration = time.perf_counter() - start_request_duration

                        labels = {
                            "method": method,
                            "route": route,
                            "status_code": str(status_code),
                        }
                        self.http_request_duration_seconds.labels(labels).observe(  # type: ignore
                            request_duration
                        )

                    return result
                else:
                    return await send(event)

            return await self.app(scope, receive, observed_send)
        else:
            return await self.app(scope, receive, send)
