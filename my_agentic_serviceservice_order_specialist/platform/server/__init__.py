"""HTTP server infrastructure module.

This module provides the FastAPI application factory and HTTP-related utilities:
- Application factory
- Route handlers
- FastAPI dependencies
- Health checks
"""

from my_agentic_serviceservice_order_specialist.platform.server.app import create_app
from my_agentic_serviceservice_order_specialist.platform.server.health import HealthCheck

__all__ = [
    "create_app",
    "HealthCheck",
]
