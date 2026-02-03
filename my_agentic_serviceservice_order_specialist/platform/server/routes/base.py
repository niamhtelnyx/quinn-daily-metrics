"""Base HTTP endpoints for health checks, metrics, and service info.

This module provides infrastructure endpoints that are typically used
by load balancers, monitoring systems, and service discovery.
"""

import logging
from enum import Enum

from fastapi import APIRouter, Response

from my_agentic_serviceservice_order_specialist.platform.observability.metrics import metrics as prom_metrics
from my_agentic_serviceservice_order_specialist.platform.server.health import HealthCheck, metadata

logger = logging.getLogger(__name__)

base_router = APIRouter()
base_tags: list[Enum | str] = ["base"]


@base_router.get("/health", tags=base_tags)
async def health():
    """Health check endpoint for load balancers and orchestrators.

    Returns:
        200 OK with status if healthy, 404 if unhealthy
    """
    if is_healthy():
        return {"status": "OK"}
    else:
        return Response(status_code=404)


def is_healthy() -> bool:
    """Check if the service is currently healthy.

    Returns:
        True if HealthCheck is enabled, False otherwise
    """
    if not HealthCheck.status():
        logger.info("health-check: fail. disabled")
        return False

    return True


@base_router.get("/info", tags=base_tags)
async def info():
    return metadata.info()


@base_router.get("/metrics", tags=base_tags)
async def metrics():
    body, media_type = prom_metrics()
    return Response(body, media_type=media_type)
