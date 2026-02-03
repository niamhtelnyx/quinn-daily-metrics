"""Prometheus metrics collection and HTTP middleware.

This module provides Prometheus metrics integration including HTTP request
duration histograms and custom timing metrics for internal operations.
"""

from collections import namedtuple
from time import monotonic
from typing import NamedTuple

import prometheus_client


class HTTPLabels(NamedTuple):
    method: str
    path: str
    http_status: str


# Maybe kinda optimized. Better than templating a string at least.
_NXX_LUT = ["1XX", "2XX", "3XX", "4XX", "5XX"]


def http_status_nxx(status: int) -> str:
    """A coarser 2XX, 4XX, 5XX"""
    return _NXX_LUT[status // 100 - 1]


SpamLabels = namedtuple("SpamLabels", ["method", "path", "spam_name"])
CounterLabels = namedtuple("CounterLabels", ["endpoint"])

BUCKETS = (
    # these are log spaced with 1 sig-fig rounding so there are 3 per decade
    # 2 div/decade = 1,       3.16,       10
    # 3 div/decade = 1,   2.15,   4.64,   10
    # 4 div/decade = 1, 1.78, 3.16, 5.62, 10
    0.0002,  # 200 μs
    0.0005,
    0.001,  # 1 ms
    0.002,
    0.005,
    0.01,
    0.02,
    0.05,
    0.1,
    0.2,
    0.5,
    1,
    2,
    5,
    10,
    20,  # default envoy timeout is 15 seconds, bin up to that time
    float("inf"),
)


def get_path(routes, scope) -> str:
    """Extract the matched route path from a request scope.

    Args:
        routes: List of FastAPI/Starlette route objects
        scope: ASGI request scope dictionary

    Returns:
        The matched route path template, or "path-not-found" if no match
    """
    path = "path-not-found"
    for route in routes:
        _, matches = route.matches(scope)
        if len(matches) > 0:
            path = route.path
    return path


async def prometheus_middleware(request, call_next):
    """HTTP middleware that records request duration metrics.

    Measures the time taken to process each request and records it
    in a Prometheus histogram with method, path, and status labels.

    Args:
        request: The incoming HTTP request
        call_next: The next middleware/handler in the chain

    Returns:
        The HTTP response from the downstream handler
    """
    start_time = monotonic()
    response = await call_next(request)
    elapsed_sec = monotonic() - start_time
    path = get_path(request.app.routes, request.scope)

    labels = HTTPLabels(
        method=request.method,
        path=path,
        http_status=http_status_nxx(response.status_code),
    )
    http_histogram.labels(*labels).observe(elapsed_sec)

    return response


def setup_metrics_factory(registry, name, documentation, labelnames):
    """Create a Prometheus histogram with standard bucket configuration.

    Args:
        registry: Prometheus registry to register the metric with
        name: Metric name (e.g., "http_request_duration_seconds")
        documentation: Human-readable metric description
        labelnames: Tuple of label names for the histogram

    Returns:
        Configured Prometheus Histogram instance
    """
    prom_histogram = prometheus_client.Histogram(
        name=name,
        documentation=documentation,
        labelnames=labelnames,
        registry=registry,
        buckets=BUCKETS,
    )

    return prom_histogram


def setup_http_metrics(registry):
    """Create the HTTP request duration histogram.

    Args:
        registry: Prometheus registry to register the metric with

    Returns:
        Histogram for tracking HTTP request durations by method, path, and status
    """
    prom_histogram = setup_metrics_factory(
        registry,
        name="http_request_duration_seconds",
        documentation="Request duration (seconds)",
        labelnames=HTTPLabels._fields,
    )

    return prom_histogram


def setup_spam_metrics(registry):
    """Create the internal function duration histogram.

    Args:
        registry: Prometheus registry to register the metric with

    Returns:
        Histogram for tracking internal function durations
    """
    prom_histogram = setup_metrics_factory(
        registry,
        name="internal_function_duration_seconds",
        documentation="internal function duration (seconds)",
        labelnames=SpamLabels._fields,
    )
    return prom_histogram


def ctx_histogram_timer(labels: HTTPLabels | SpamLabels):
    """
    Context manager for methods timer
    Usage:
        Context manager
        ```
        labels = SpamLabels(method="GET", path="/abc", spam_name="abc")
        with ctx_histogram_timer(labels):
            abc()
            ...
        ```
        Decorator:
        ```
            labels = SpamLabels(method="GET", path="/abc", spam_name="abc")
            @ctx_histogram_timer(labels)
            def meh():
                abc()
        ```
    See more:
    # pylint: disable=line-too-long
     - https://github.com/prometheus/client_python#histogram
    """
    return spam_histogram.labels(*labels).time()


def timing_metrics(request, spam_name):
    """Handy proxy to ctx_histogram_timer to be used with a request
    Usage:
        ```
        with timing_metrics(request, "my_method_to_be_instrumented"):
            abc()
            ...
        ```
    """

    method = request.method
    path = get_path(request.app.routes, request.scope)

    labels = SpamLabels(method=method, path=path, spam_name=spam_name)
    return ctx_histogram_timer(labels)


http_histogram = setup_http_metrics(registry=prometheus_client.REGISTRY)
spam_histogram = setup_spam_metrics(registry=prometheus_client.REGISTRY)


def metrics() -> tuple[bytes, str]:
    """Generate Prometheus metrics output for the /metrics endpoint.

    Returns:
        Tuple of (metrics_body, content_type) for the HTTP response
    """
    return (
        prometheus_client.generate_latest(prometheus_client.REGISTRY),
        prometheus_client.CONTENT_TYPE_LATEST,
    )
