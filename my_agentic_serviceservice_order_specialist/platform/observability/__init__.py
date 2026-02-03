"""Observability infrastructure module.

This module provides monitoring and error tracking:
- Structured logging with correlation IDs
- Prometheus metrics
- Bugsnag error reporting
"""

from my_agentic_serviceservice_order_specialist.platform.observability.logging import (
    configure_logging,
    correlation_id_ctx,
    get_logger,
)
from my_agentic_serviceservice_order_specialist.platform.observability.metrics import (
    BUCKETS,
    prometheus_middleware,
)

__all__ = [
    "BUCKETS",
    "configure_logging",
    "correlation_id_ctx",
    "get_logger",
    "prometheus_middleware",
]
