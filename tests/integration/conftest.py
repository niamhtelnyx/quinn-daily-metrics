"""Integration test fixtures.

This module provides shared fixtures for integration tests including:
- Route/handler tests with mocked dependencies (shallow app setup)
- LangGraphAgent tests with stubbed graphs
- Component interaction tests

For true end-to-end tests with real database, see tests/e2e/.
"""

from collections.abc import AsyncIterator, Generator
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any
from unittest.mock import AsyncMock, Mock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage, HumanMessage

from my_agentic_serviceservice_order_specialist.agents.knowledge.agent import KnowledgeAgentBuilder
from my_agentic_serviceservice_order_specialist.agents.knowledge.routes import knowledge_router
from my_agentic_serviceservice_order_specialist.platform.agent.config import AgentIdentity, Audience
from my_agentic_serviceservice_order_specialist.platform.agent.messages import (
    ExecutionResult,
    Message,
    StreamEvent,
)
from my_agentic_serviceservice_order_specialist.platform.server.health import HealthCheck
from my_agentic_serviceservice_order_specialist.platform.server.routes import root as root_router

# =============================================================================
# Agent Fixtures
# =============================================================================


@pytest.fixture
def stub_agent_identity() -> AgentIdentity:
    """Create a stub agent identity with canned test data."""
    return AgentIdentity(
        name="Test Agent",
        slug="test-agent",
        description="A test agent for integration tests",
        squad="test-squad",
        origin="test-origin",
        audience=Audience.INTERNAL,
    )


@pytest.fixture
def stub_identity(stub_agent_identity: AgentIdentity) -> AgentIdentity:
    """Alias for stub_agent_identity for backward compatibility."""
    return stub_agent_identity


@pytest.fixture
def initial_state_builder():
    """Create a simple initial state builder for LangGraphAgent tests."""

    def builder(message: str, thread_id: str, utc_now: datetime | None = None) -> dict[str, Any]:
        return {
            "messages": [HumanMessage(content=message)],
            "reasoning_steps": 0,
            "thread_id": thread_id,
            "input_tokens_by_model": {},
            "output_tokens_by_model": {},
        }

    return builder


@pytest.fixture
def stub_stream_events_data() -> list[dict[str, Any]]:
    """Create stub stream events data with canned values."""
    return [
        {"reasoner": {"messages": [AIMessage(content="Thinking...")]}},
        {"reasoner": {"messages": [AIMessage(content="Processing...")]}},
        {"reasoner": {"messages": [AIMessage(content="Final answer.")]}},
    ]


@pytest.fixture
def stub_streaming_graph(stub_stream_events_data: list[dict[str, Any]]) -> Mock:
    """Create a stub graph that yields canned streaming responses."""
    graph = Mock()

    async def stream_generator(*args, **kwargs):
        for event in stub_stream_events_data:
            yield event

    graph.astream = stream_generator
    return graph


@pytest.fixture
def stub_execution_result() -> ExecutionResult:
    """Create a stub execution result with canned test data."""
    return ExecutionResult(
        response="This is a test response",
        messages=[
            Message(role="user", content="Test question"),
            Message(role="assistant", content="This is a test response"),
        ],
        reasoning_steps=1,
        thread_id="test-thread-123",
        metadata={"model": "test-model"},
    )


@pytest.fixture
def stub_stream_events() -> list[StreamEvent]:
    """Create stub stream events with canned test data."""
    return [
        StreamEvent(
            event_type="message",
            data={"reasoner": {"messages": [Mock(content="Thinking...", tool_calls=[])]}},
        ),
        StreamEvent(
            event_type="message",
            data={"reasoner": {"messages": [Mock(content="Final answer", tool_calls=[])]}},
        ),
    ]


@pytest.fixture
def stub_agent(
    stub_agent_identity: AgentIdentity,
    stub_execution_result: ExecutionResult,
    stub_stream_events: list[StreamEvent],
) -> Mock:
    """Create a stub agent that provides canned responses.

    This is a stub (not a mock) because it primarily provides predetermined
    return values rather than verifying interactions.
    """
    agent = Mock()
    agent.identity = stub_agent_identity
    agent.name = stub_agent_identity.name
    agent.description = stub_agent_identity.description
    agent.slug = stub_agent_identity.slug

    # Stub run() to return canned ExecutionResult
    agent.run = AsyncMock(return_value=stub_execution_result)

    # Stub run_stream() to return canned async generator
    async def stream_generator(
        message: str, thread_id: str, utc_now: datetime | None = None
    ) -> AsyncIterator[StreamEvent]:
        for event in stub_stream_events:
            yield event

    agent.run_stream = stream_generator

    return agent


# =============================================================================
# FastAPI App Fixtures (Shallow - no middleware, minimal lifespan)
# =============================================================================


@pytest.fixture
def test_app(stub_agent: Mock) -> FastAPI:
    """Create a minimal test FastAPI app for integration tests.

    This is intentionally SHALLOW - no middleware, no full lifespan.
    Tests route handlers and their interaction with dependencies.

    For full-stack testing with middleware, see e2e tests.
    """
    app = FastAPI()

    # Register stub agent directly in app.state
    app.state.agents = {KnowledgeAgentBuilder: stub_agent}

    # Include only the routers being tested
    app.include_router(root_router)
    app.include_router(knowledge_router)

    return app


@pytest.fixture
def client(test_app: FastAPI) -> TestClient:
    """Create a test client for the test app.

    No context manager needed since we're not using lifespan.
    """
    return TestClient(test_app)


@pytest.fixture
def client_with_health_enabled(test_app: FastAPI) -> Generator[TestClient]:
    """Create a test client with health checks enabled."""
    HealthCheck.enable()
    yield TestClient(test_app)
    HealthCheck.disable()


@pytest.fixture
def client_with_health_disabled(test_app: FastAPI) -> Generator[TestClient]:
    """Create a test client with health checks disabled."""
    HealthCheck.disable()
    yield TestClient(test_app)


@pytest.fixture
def stub_settings() -> Mock:
    """Create stub settings with canned configuration values."""
    settings = Mock()
    settings.a2a.base_url = "http://localhost:8000/a2a"
    settings.a2a.protocol_version = "0.3.0"
    return settings


@pytest.fixture
def fake_db() -> Mock:
    """Create a fake database engine for tests.

    This is a fake (not a mock) because it provides a simplified but
    working implementation of the database interface, suitable for
    testing without a real database connection.

    Example:
        async def test_with_db(fake_db):
            async with fake_db.get_session() as session:
                # ... test code
    """
    db = Mock()
    db.instance_name = "test-db"
    db.is_connected = Mock(return_value=True)

    # Fake session
    fake_session = AsyncMock()

    @asynccontextmanager
    async def fake_get_session():
        yield fake_session

    db.get_session = fake_get_session

    # Fake transaction
    @asynccontextmanager
    async def fake_transaction():
        yield fake_session

    db.transaction = fake_transaction

    # Fake engine
    fake_engine = Mock()
    db.get_engine = Mock(return_value=fake_engine)

    return db
