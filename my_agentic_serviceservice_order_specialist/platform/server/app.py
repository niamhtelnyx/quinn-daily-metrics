# ruff: noqa: E402
"""FastAPI application factory and server configuration.

This module creates and configures the FastAPI application with all middleware,
routes, and lifecycle management.
"""

import asyncio
import logging
import os
import signal
import warnings
from contextlib import asynccontextmanager

# Suppress Pydantic serializer warnings from LangChain/LangGraph checkpointer
# These occur due to type mismatches between langchain-litellm and Pydantic's
# expected schemas, but don't affect functionality
warnings.filterwarnings("ignore", message="Pydantic serializer warnings")

import httpx
from fastapi import FastAPI
from openinference.instrumentation.langchain import LangChainInstrumentor
from openinference.semconv.resource import ResourceAttributes
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.logging import LoggingInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from telnyx.metrics.opentelemetry.initializer import jaeger_initialize

from my_agentic_serviceservice_order_specialist.agents.service_order.routes import service_order_router
from my_agentic_serviceservice_order_specialist.agents.service_order.agent import A2A_SKILLS
from my_agentic_serviceservice_order_specialist.platform.constants import SERVICE_NAME
from my_agentic_serviceservice_order_specialist.platform.database.setup import close_db, setup_db
from my_agentic_serviceservice_order_specialist.platform.observability import errors as bugsnag
from my_agentic_serviceservice_order_specialist.platform.observability.logging import configure_logging
from my_agentic_serviceservice_order_specialist.platform.observability.metrics import prometheus_middleware
from my_agentic_serviceservice_order_specialist.platform.server.health import HealthCheck
from my_agentic_serviceservice_order_specialist.platform.server.middlewares import CorrelationIdMiddleware
from my_agentic_serviceservice_order_specialist.platform.server.routes import root as root_router
from my_agentic_serviceservice_order_specialist.platform.server.routes.a2a import (
    add_a2a_routes_to_app,
    register_agent_card,
)
from my_agentic_serviceservice_order_specialist.platform.server.routes.conversations import conversations_router
from my_agentic_serviceservice_order_specialist.platform.settings import Settings


def lifespan_closure(settings):
    @asynccontextmanager
    async def lifespan(app):
        """
        Use this to initialize all of the singleton dependencies and shared
        objects.  i.e. db, reporters, bugsnag, etc
        """
        if settings.bugsnag.release_stage in ["production", "development"]:
            signal_handler = SignalHandler(app)
            signal_handler.register_signal_handler()
        await bugsnag.initialize_bugsnag(
            settings.bugsnag.api_key,
            settings.bugsnag.release_stage,
        )

        # Configure structured logging (JSON in prod/dev, console in local)
        if settings.app_http.log_json is not None:
            json_output = settings.app_http.log_json
        else:
            json_output = settings.bugsnag.release_stage != "local"
        configure_logging(settings.app_http.log_level, json_output=json_output)

        # Store settings in app.state for setup_db to access
        app.state.settings = settings

        # Initialize shared HTTP client for external services
        app.state.http_client = httpx.AsyncClient(
            timeout=30.0,  # Default timeout, can be overridden per-request
            limits=httpx.Limits(max_keepalive_connections=20, max_connections=100),
        )

        # Initialize databases
        await setup_db(app)

        if settings.opentelemetry.enabled:
            jaeger_initialize(
                app_name=SERVICE_NAME,
                host=settings.opentelemetry.host,
                port=settings.opentelemetry.port,
                instrumentors={  # type: ignore
                    LoggingInstrumentor(): {"set_logging_format": True},
                    LangChainInstrumentor(): {},
                },
                extra_resource_attributes={
                    ResourceAttributes.PROJECT_NAME: SERVICE_NAME,
                },
            )

            SQLAlchemyInstrumentor().instrument(  # type: ignore
                engine=app.state.db_engine.get_engine().sync_engine
            )

        agent_registrations = await add_a2a_routes_to_app(app)

        # Register agent cards with external registry if configured
        if settings.agent_registry.should_register:
            async with asyncio.TaskGroup() as tg:
                for agent_card, identity, tools in agent_registrations:
                    tg.create_task(
                        register_agent_card(
                            app.state.http_client,
                            settings.agent_registry.url,
                            agent_card,
                            identity,
                            tools,
                        )
                    )

        HealthCheck.enable()
        yield

    return lifespan


def create_app(settings: Settings):
    """Create and configure the FastAPI application.

    Args:
        settings: Application settings instance

    Returns:
        Configured FastAPI application
    """
    # Create main FastAPI application
    app = FastAPI(lifespan=lifespan_closure(settings))
    app.add_middleware(CorrelationIdMiddleware)
    app.middleware("http")(prometheus_middleware)
    if settings.opentelemetry.enabled:
        FastAPIInstrumentor.instrument_app(app)

    # Include platform routes (health, metrics)
    app.include_router(root_router)

    # Include agent routes
    app.include_router(service_order_router)

    # Include platform routes for debugging/inspection
    app.include_router(conversations_router)

    return app


class SignalHandler:
    def __init__(self, app: FastAPI):
        self.app = app

    async def handle_exit(self):
        """
        Handle the exit of the server
        Do NOT use FastAPI @app.on_event("shutdown") or lifespan
        The problem with this method is, it is invoked *after* server
        stops accepting request, so it does not give us any time to
        drain requests in progress and DNS cache to refresh
        """
        HealthCheck.disable()
        for i in range(20):
            logging.info("Shutting down...")
            await asyncio.sleep(1)

        # Close HTTP client
        if hasattr(self.app.state, "http_client"):
            await self.app.state.http_client.aclose()

        # Disconnect all databases
        await close_db(self.app)

        # stop service successfully
        os.kill(os.getpid(), signal.SIGUSR1)

    def signal_handler(self):
        """
        Signal handler function
        """
        asyncio.create_task(self.handle_exit())

    def register_signal_handler(self) -> None:
        """
        Register signal handlers for the server
        """
        loop = asyncio.get_running_loop()
        for sig in [signal.SIGINT, signal.SIGTERM]:
            loop.add_signal_handler(sig, self.signal_handler)
