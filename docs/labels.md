# Labels

With labels you can differentiate what you are measuring, for example for an `http_request_duration_seconds` metric you might want to differentiate between `GET` or `POST` requests while using the same metric.

!!! warning


    Every new value for a label key represents a new time serie, so you should try to avoid labels that measure things with high cardinality, for example a path that has no specific ending: `/users/{id}` {here id is variable depending on the request}.

    In that case it would be better to observe the metric replacing the last part of the endpoint with a fixed value so that you still get useful information: `/users/:id`
