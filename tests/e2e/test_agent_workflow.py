"""E2E tests for agent workflow with real database.

Tests the complete agent workflow with:
- Real PostgreSQL database (via testcontainers)
- Fake LLM responses (predictable, no API costs)
- Real conversation persistence

Run with: pytest tests/e2e/ -m e2e
Skip with: pytest -m "not e2e"
"""

from typing import Any
from unittest.mock import AsyncMock

import pytest
from langchain_core.callbacks import CallbackManagerForLLMRun
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

from my_agentic_serviceservice_order_specialist.agents.knowledge.agent import KnowledgeAgentBuilder
from my_agentic_serviceservice_order_specialist.platform.agent.config import (
    AgentConfig,
    AgentIdentity,
    LlmConfig,
)
from my_agentic_serviceservice_order_specialist.platform.database.engine import DbEngine


class FakeChatModelForTests(BaseChatModel):
    """Fake chat model for E2E tests that returns predictable responses."""

    response_content: str = "This is a test response."
    model: str = "fake-test-model"

    @property
    def _llm_type(self) -> str:
        return "fake-test-model"

    def _generate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: CallbackManagerForLLMRun | None = None,
        **kwargs: Any,
    ) -> ChatResult:
        """Generate a fake response."""
        ai_message = AIMessage(
            content=self.response_content,
            response_metadata={"usage": {"input_tokens": 100, "output_tokens": 50}},
        )
        # Set usage_metadata for token tracking
        ai_message.usage_metadata = {"input_tokens": 100, "output_tokens": 50}  # type: ignore[assignment]
        return ChatResult(generations=[ChatGeneration(message=ai_message)])

    def bind_tools(self, tools: Any, **kwargs: Any) -> "FakeChatModelForTests":
        """Bind tools - returns self since we don't actually use tools."""
        return self


@pytest.fixture
async def db_checkpointer(postgres_db: DbEngine) -> AsyncPostgresSaver:
    """Create a real AsyncPostgresSaver connected to test database."""
    pool = postgres_db.get_pool()
    checkpointer = AsyncPostgresSaver(pool)  # type: ignore[arg-type]
    await checkpointer.setup()
    return checkpointer


@pytest.fixture
def fake_llm() -> FakeChatModelForTests:
    """Create a fake LLM for testing."""
    return FakeChatModelForTests()


@pytest.fixture
def test_identity() -> AgentIdentity:
    """Create a test agent identity."""
    return AgentIdentity(
        name="Test Knowledge",
        slug="test-knowledge",
        description="Test agent for E2E tests",
        squad="test-squad",
        origin="test-e2e",
    )


@pytest.fixture
def test_agent_config() -> AgentConfig:
    """Create a test agent config."""
    return AgentConfig(
        max_reasoning_steps=5,
        artifact_threshold=5000,
        always_visible_tools=frozenset({"inspect_artifact"}),
        recursion_limit=25,
    )


@pytest.fixture
def test_llm_config() -> LlmConfig:
    """Create a test LLM config."""
    return LlmConfig(
        model="test-model",
        base_url="http://localhost:8080",
        api_key="test-key",
        temperature=0.5,
    )


@pytest.mark.e2e
class TestAgentWorkflowWithRealDB:
    """E2E tests for agent workflow with real PostgreSQL."""

    async def test_invoke_stores_conversation(
        self,
        db_checkpointer: AsyncPostgresSaver,
        test_identity: AgentIdentity,
        test_agent_config: AgentConfig,
        test_llm_config: LlmConfig,
        fake_llm: FakeChatModelForTests,
    ):
        """Agent invoke stores conversation in real database."""
        # Build agent with fake LLM
        builder = KnowledgeAgentBuilder(
            agent_config=test_agent_config,
            llm_config=test_llm_config,
            mcp_configs=[],  # No MCP tools for this test
            checkpointer=db_checkpointer,
            identity=test_identity,
            tool_fetcher=AsyncMock(return_value=[]),  # No tools
        )

        # Patch ChatLiteLLM to return our fake model
        with pytest.MonkeyPatch().context() as mp:
            mp.setattr(
                "my_agentic_serviceservice_order_specialist.platform.agent.llm_client.ChatLiteLLM",
                lambda **kwargs: fake_llm,
            )
            agent = await builder.build()

            # Run the agent
            thread_id = "test-thread-e2e-001"
            result = await agent.run(
                message="What is Python?",
                thread_id=thread_id,
            )

        # Verify we got a response
        assert result.response is not None
        assert result.thread_id == thread_id

        # Verify conversation was stored in database
        config = {"configurable": {"thread_id": thread_id}}
        checkpoint_tuple = await db_checkpointer.aget_tuple(config)  # type: ignore[arg-type]

        assert checkpoint_tuple is not None
        assert checkpoint_tuple.checkpoint is not None

        # Verify messages are in the checkpoint
        channel_values = checkpoint_tuple.checkpoint.get("channel_values", {})
        messages = channel_values.get("messages", [])
        assert len(messages) >= 2  # At least system + user messages

    async def test_invoke_with_same_thread_continues_conversation(
        self,
        db_checkpointer: AsyncPostgresSaver,
        test_identity: AgentIdentity,
        test_agent_config: AgentConfig,
        test_llm_config: LlmConfig,
        fake_llm: FakeChatModelForTests,
    ):
        """Multiple invokes on same thread continue the conversation."""
        builder = KnowledgeAgentBuilder(
            agent_config=test_agent_config,
            llm_config=test_llm_config,
            mcp_configs=[],
            checkpointer=db_checkpointer,
            identity=test_identity,
            tool_fetcher=AsyncMock(return_value=[]),
        )

        with pytest.MonkeyPatch().context() as mp:
            mp.setattr(
                "my_agentic_serviceservice_order_specialist.platform.agent.llm_client.ChatLiteLLM",
                lambda **kwargs: fake_llm,
            )
            agent = await builder.build()
            thread_id = "test-thread-e2e-002"

            # First invoke
            result1 = await agent.run(
                message="First question",
                thread_id=thread_id,
            )

            # Second invoke on same thread
            result2 = await agent.run(
                message="Follow up question",
                thread_id=thread_id,
            )

        # Verify both invokes returned responses
        assert result1.response is not None
        assert result2.response is not None
        assert result1.thread_id == thread_id
        assert result2.thread_id == thread_id

        # Verify conversation history grew
        config = {"configurable": {"thread_id": thread_id}}
        checkpoint_tuple = await db_checkpointer.aget_tuple(config)  # type: ignore[arg-type]

        assert checkpoint_tuple is not None
        channel_values = checkpoint_tuple.checkpoint.get("channel_values", {})
        messages = channel_values.get("messages", [])

        # Should have: system + user1 + ai1 + user2 + ai2 = 5+ messages
        assert len(messages) >= 4

    async def test_different_threads_are_isolated(
        self,
        db_checkpointer: AsyncPostgresSaver,
        test_identity: AgentIdentity,
        test_agent_config: AgentConfig,
        test_llm_config: LlmConfig,
        fake_llm: FakeChatModelForTests,
    ):
        """Different thread_ids have isolated conversations."""
        builder = KnowledgeAgentBuilder(
            agent_config=test_agent_config,
            llm_config=test_llm_config,
            mcp_configs=[],
            checkpointer=db_checkpointer,
            identity=test_identity,
            tool_fetcher=AsyncMock(return_value=[]),
        )

        with pytest.MonkeyPatch().context() as mp:
            mp.setattr(
                "my_agentic_serviceservice_order_specialist.platform.agent.llm_client.ChatLiteLLM",
                lambda **kwargs: fake_llm,
            )
            agent = await builder.build()

            thread_id_a = "test-thread-e2e-003a"
            thread_id_b = "test-thread-e2e-003b"

            # Invoke on thread A
            await agent.run(message="Question for A", thread_id=thread_id_a)

            # Invoke on thread B
            await agent.run(message="Question for B", thread_id=thread_id_b)

        # Verify both threads have separate conversations
        config_a = {"configurable": {"thread_id": thread_id_a}}
        config_b = {"configurable": {"thread_id": thread_id_b}}

        checkpoint_a = await db_checkpointer.aget_tuple(config_a)  # type: ignore[arg-type]
        checkpoint_b = await db_checkpointer.aget_tuple(config_b)  # type: ignore[arg-type]

        assert checkpoint_a is not None
        assert checkpoint_b is not None

        # Each should have their own messages
        messages_a = checkpoint_a.checkpoint.get("channel_values", {}).get("messages", [])
        messages_b = checkpoint_b.checkpoint.get("channel_values", {}).get("messages", [])

        # Find user messages and verify they're different
        user_content_a = None
        user_content_b = None

        for msg in messages_a:
            if hasattr(msg, "type") and msg.type == "human":
                user_content_a = msg.content
                break

        for msg in messages_b:
            if hasattr(msg, "type") and msg.type == "human":
                user_content_b = msg.content
                break

        assert user_content_a is not None
        assert user_content_b is not None
        assert "Question for A" in user_content_a
        assert "Question for B" in user_content_b
