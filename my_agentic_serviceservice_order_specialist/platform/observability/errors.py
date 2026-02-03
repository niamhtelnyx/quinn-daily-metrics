"""Bugsnag error reporting integration.

This module provides initialization for Bugsnag error tracking,
automatically capturing and reporting unhandled exceptions.
"""

import logging

import bugsnag
from bugsnag.handlers import BugsnagHandler


async def initialize_bugsnag(api_key: str, release_stage: str) -> None:
    """Initialize Bugsnag error reporting.

    Configures Bugsnag with the provided API key and attaches a handler
    to the root logger to automatically report ERROR-level log entries.

    Args:
        api_key: Bugsnag project API key
        release_stage: Environment identifier (e.g., "production", "development", "local")

    Note:
        No-op when release_stage is "local" to avoid reporting during local development.
    """
    if release_stage == "local":
        return
    logger = logging.getLogger()
    bugsnag.configure(
        api_key=api_key,
        release_stage=release_stage,
        auto_notify=True,
    )
    handler = BugsnagHandler()
    handler.setLevel(logging.ERROR)
    logger.addHandler(handler)
