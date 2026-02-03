"""Middleware for request correlation ID propagation."""

import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from my_agentic_serviceservice_order_specialist.platform.observability.logging import correlation_id_ctx

REQUEST_ID_HEADER = "X-Request-ID"


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """Middleware that extracts or generates correlation IDs for request tracing.

    Extracts X-Request-ID from incoming request headers or generates a new UUID
    if not present. The correlation ID is stored in a context variable for use
    by the structured logging system and echoed back in the response headers.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        # Extract from header or generate new
        correlation_id = request.headers.get(REQUEST_ID_HEADER) or str(uuid.uuid4())

        # Store in context for logging
        token = correlation_id_ctx.set(correlation_id)

        try:
            response = await call_next(request)
            # Echo correlation ID in response
            response.headers[REQUEST_ID_HEADER] = correlation_id
            return response
        finally:
            correlation_id_ctx.reset(token)
