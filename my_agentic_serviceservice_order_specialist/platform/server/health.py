"""
HTTP health check.
"""

import datetime
import json
import os
import platform
import socket
import threading
import time
from typing import Any

import attr
from aiohttp import web

__all__ = ["health_check", "info", "HealthCheck"]


class HealthCheck:
    """Thread-safe health check state manager.

    Uses a threading.Event to manage health check state, allowing
    the service to be gracefully drained during shutdown.
    """

    _health_check_enabled = threading.Event()

    @staticmethod
    def enable() -> None:
        """Enable health checks (mark service as healthy)."""
        HealthCheck._health_check_enabled.set()

    @staticmethod
    def disable() -> None:
        """Disable health checks (mark service as unhealthy for graceful shutdown)."""
        HealthCheck._health_check_enabled.clear()

    @staticmethod
    def status() -> bool:
        """Check if health checks are currently enabled.

        Returns:
            True if the service is marked as healthy, False otherwise
        """
        return HealthCheck._health_check_enabled.is_set()


async def health_check(request):
    return web.json_response({"status": "OK"}, dumps=dumps)


def serialize(obj):
    """Handle serialization of attrs objects.

    If an as_dict method is defined, use that instead of the attrs asdict function.
    """
    if isinstance(obj, datetime.datetime):
        return obj.isoformat()
    if hasattr(obj, "as_dict"):
        return obj.as_dict()
    return attr.asdict(obj)


def dumps(obj, compact=False, **kwargs):
    """Replacement for json.dumps."""
    defaults: dict[str, Any] = {
        "ensure_ascii": False,
        "indent": 2,
        "default": serialize,
    }
    if compact:
        defaults["indent"] = None
        defaults["separators"] = (",", ":")
    defaults.update(kwargs)

    return json.dumps(obj, **defaults)  # type: ignore


class MetadataManager:
    """
    Metadata manager thing. One is automatically created on import, feel free to use
    that. Also to modify the ``metadata`` dictionary attribute of it to add any other
    other useful (static) data.
    """

    # keys to read from the environment
    ENV_INFO_KEYS = [
        "BUILD_DATE",
        "BUILD_URL",
        "BUILD_VERSION",
        "GIT_COMMIT",
        "GIT_COMMIT_DATE",
        "IMAGE_NAME",
        "SERVICE_ID",
        "SERVICE_NAME",
        "PYTHON_VERSION",
    ]
    HTTP_PORT_KEY = "HTTP_PORT"
    HOSTNAME_KEY = "HOSTNAME"
    OS_VERSION_KEY = "OS_VERSION"
    SERVICE_NAME_KEY = "SERVICE_NAME"
    SERVICE_NAME_TEMPLATE_KEY = "SERVICE_{}_NAME"
    SERVICE_ID_KEY = "SERVICE_ID"
    SERVICE_ID_TEMPLATE_KEY = "SERVICE_{}_ID"
    BUILD_VERSION_KEY = "BUILD_VERSION"
    BUILD_VERSION_TEMPLATE_KEY = "SERVICE_{}_VERSION"

    def __init__(self):
        self._started_at = datetime.datetime.now(tz=datetime.UTC).isoformat()
        self._started_ts = time.monotonic()
        port = os.environ.get(self.HTTP_PORT_KEY)

        metadata = {key: os.environ.get(key) for key in self.ENV_INFO_KEYS}
        metadata[self.HOSTNAME_KEY] = socket.gethostname()
        metadata[self.OS_VERSION_KEY] = platform.platform()
        metadata[self.SERVICE_NAME_KEY] = metadata[self.SERVICE_NAME_KEY] or os.environ.get(
            self.SERVICE_NAME_TEMPLATE_KEY.format(port)
        )
        metadata[self.SERVICE_ID_KEY] = metadata[self.SERVICE_ID_KEY] or os.environ.get(
            self.SERVICE_ID_TEMPLATE_KEY.format(port)
        )
        metadata[self.BUILD_VERSION_KEY] = metadata[self.BUILD_VERSION_KEY] or os.environ.get(
            self.BUILD_VERSION_TEMPLATE_KEY.format(port)
        )
        self.metadata = {key.lower(): value for key, value in metadata.items()}

    def info(self):
        """
        Return metadata about the container and some basic stats
        """
        return {
            **self.metadata,
            "started": self._started_at,
            "uptime_seconds": round(time.monotonic() - self._started_ts, 3),
        }

    async def handler(self, _request: web.Request) -> web.Response:
        return web.json_response(self.info(), dumps=dumps)


metadata = MetadataManager()

info = metadata.handler
