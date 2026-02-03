"""Structured logging configuration using structlog.

This module provides structured logging with JSON output for production
and colored console output for local development, plus correlation ID
propagation across async boundaries.
"""

import logging
import sys
from contextvars import ContextVar

import structlog

# Context variable for request correlation ID - propagates across async boundaries
correlation_id_ctx: ContextVar[str | None] = ContextVar("correlation_id", default=None)


def add_correlation_id(
    logger: structlog.types.WrappedLogger,
    method_name: str,
    event_dict: structlog.types.EventDict,
) -> structlog.types.EventDict:
    """Processor that adds correlation_id to every log entry."""
    correlation_id = correlation_id_ctx.get()
    if correlation_id:
        event_dict["correlation_id"] = correlation_id
    return event_dict


def configure_logging(log_level: str, json_output: bool = True) -> None:
    """Configure structlog with appropriate processors and renderer.

    Args:
        log_level: Logging level (INFO, DEBUG, etc.)
        json_output: True for JSON output (prod/dev), False for console (local)
    """
    shared_processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        add_correlation_id,
        structlog.processors.UnicodeDecoder(),
    ]

    if json_output:
        # JSON output for prod/dev
        renderer: structlog.types.Processor = structlog.processors.JSONRenderer()
    else:
        # Human-readable console output for local
        renderer = structlog.dev.ConsoleRenderer(colors=True)

    structlog.configure(
        processors=shared_processors
        + [
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    formatter = structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=shared_processors,
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            renderer,
        ],
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(log_level)

    # Quiet noisy loggers
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    """Get a structlog logger instance.

    Args:
        name: Logger name, typically __name__ of the calling module

    Returns:
        A bound structlog logger
    """
    return structlog.get_logger(name)
