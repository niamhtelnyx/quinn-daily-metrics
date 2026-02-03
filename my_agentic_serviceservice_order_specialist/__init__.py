"""my-agentic-serviceservice-order-specialist - An agentic service with LangGraph orchestration and MCP tool integration."""

from .platform.server.app import create_app
from .platform.settings import Settings


def app():
    """Create the FastAPI application instance."""
    settings = Settings()
    return create_app(settings)
