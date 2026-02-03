"""Unit tests for A2A LangGraph node factories."""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from my_agentic_serviceservice_order_specialist.platform.clients.a2a.config import A2AClientConfig, AuthConfig
from my_agentic_serviceservice_order_specialist.platform.clients.a2a.langgraph.nodes import (
    A2ANodeConfig,
    _default_input_transform,
    _default_output_transform,
    create_a2a_node,
    create_multi_agent_router,
)
from my_agentic_serviceservice_order_specialist.platform.clients.a2a.strategies.base import ExecutionResult


class TestA2ANodeConfig:
    """Tests for A2ANodeConfig dataclass."""

    def test_required_base_url(self):
        """A2ANodeConfig requires base_url."""
        config = A2ANodeConfig(base_url="http://agent.example.com")
        assert config.base_url == "http://agent.example.com"

    def test_default_values(self):
        """A2ANodeConfig has correct defaults."""
        config = A2ANodeConfig(base_url="http://example.com")
        assert config.input_key == "messages"
        assert config.output_key == "a2a_response"
        assert config.task_id_key == "a2a_task_id"
        assert config.context_id_key == "a2a_context_id"
        assert config.client_config is None
        assert config.auth is None
        assert config.transform_input is None
        assert config.transform_output is None

    def test_full_config(self):
        """A2ANodeConfig accepts all values."""
        client_config = A2AClientConfig(timeout_seconds=30.0)
        auth = AuthConfig(api_key="test-key")

        def custom_input(state):
            return state["query"]

        def custom_output(result, state):
            return {"answer": result.response_text}

        config = A2ANodeConfig(
            base_url="http://agent.example.com",
            input_key="query",
            output_key="answer",
            task_id_key="task_id",
            context_id_key="context_id",
            client_config=client_config,
            auth=auth,
            transform_input=custom_input,
            transform_output=custom_output,
        )

        assert config.input_key == "query"
        assert config.output_key == "answer"
        assert config.transform_input is custom_input
        assert config.transform_output is custom_output


class TestDefaultInputTransform:
    """Tests for _default_input_transform()."""

    def test_extracts_content_from_message_object(self):
        """Extracts content from message with content attribute."""
        message = Mock()
        message.content = "Hello, agent!"
        state = {"messages": [message]}

        result = _default_input_transform(state)

        assert result == "Hello, agent!"

    def test_extracts_content_from_dict_message(self):
        """Extracts content from dict message."""
        state = {"messages": [{"role": "user", "content": "Hello"}]}

        result = _default_input_transform(state)

        assert result == "Hello"

    def test_converts_non_dict_message_to_string(self):
        """Converts non-dict message to string."""
        state = {"messages": ["plain text message"]}

        result = _default_input_transform(state)

        assert result == "plain text message"

    def test_uses_last_message(self):
        """Uses the last message in the list."""
        msg1 = Mock()
        msg1.content = "First"
        msg2 = Mock()
        msg2.content = "Last"
        state = {"messages": [msg1, msg2]}

        result = _default_input_transform(state)

        assert result == "Last"

    def test_raises_on_empty_messages(self):
        """Raises ValueError when no messages."""
        state = {"messages": []}

        with pytest.raises(ValueError, match="No messages"):
            _default_input_transform(state)

    def test_raises_on_missing_messages_key(self):
        """Raises ValueError when messages key is missing."""
        state = {}

        with pytest.raises(ValueError, match="No messages"):
            _default_input_transform(state)


class TestDefaultOutputTransform:
    """Tests for _default_output_transform()."""

    def test_creates_state_update(self):
        """Creates state update with response values."""
        task = Mock()
        result = ExecutionResult(
            task=task,
            response_text="Agent response",
            task_id="task-123",
            context_id="ctx-456",
            state=Mock(),
            artifacts=[],
        )
        state = {}

        output = _default_output_transform(result, state)

        assert output["a2a_response"] == "Agent response"
        assert output["a2a_task_id"] == "task-123"
        assert output["a2a_context_id"] == "ctx-456"


class TestCreateA2ANode:
    """Tests for create_a2a_node()."""

    @pytest.fixture
    def mock_result(self):
        """Create a mock ExecutionResult."""
        task = Mock()
        return ExecutionResult(
            task=task,
            response_text="Agent response",
            task_id="task-123",
            context_id="ctx-456",
            state=Mock(),
            artifacts=[],
        )

    async def test_creates_callable_node(self):
        """create_a2a_node returns an async callable."""
        config = A2ANodeConfig(base_url="http://example.com")

        node = create_a2a_node(config)

        assert callable(node)

    async def test_node_calls_a2a_client(self, mock_result):
        """Node calls A2A client with input from state."""
        config = A2ANodeConfig(base_url="http://example.com")

        with patch(
            "my_agentic_serviceservice_order_specialist.platform.clients.a2a.langgraph.nodes.A2AClientWrapper"
        ) as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.send_text = AsyncMock(return_value=mock_result)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock()
            mock_client_cls.return_value = mock_client

            node = create_a2a_node(config)
            msg = Mock()
            msg.content = "Hello"
            state = {"messages": [msg]}

            result = await node(state)

            mock_client.send_text.assert_called_once()
            assert result["a2a_response"] == "Agent response"

    async def test_node_uses_task_id_from_state(self, mock_result):
        """Node includes task_id from state if available."""
        config = A2ANodeConfig(base_url="http://example.com")

        with patch(
            "my_agentic_serviceservice_order_specialist.platform.clients.a2a.langgraph.nodes.A2AClientWrapper"
        ) as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.send_text = AsyncMock(return_value=mock_result)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock()
            mock_client_cls.return_value = mock_client

            node = create_a2a_node(config)
            msg = Mock()
            msg.content = "Continue"
            state = {
                "messages": [msg],
                "a2a_task_id": "existing-task",
            }

            await node(state)

            call_args = mock_client.send_text.call_args
            assert call_args.kwargs["task_id"] == "existing-task"

    async def test_node_uses_custom_input_transform(self, mock_result):
        """Node uses custom input transform when provided."""

        def custom_input(state):
            return state["custom_query"]

        config = A2ANodeConfig(
            base_url="http://example.com",
            transform_input=custom_input,
        )

        with patch(
            "my_agentic_serviceservice_order_specialist.platform.clients.a2a.langgraph.nodes.A2AClientWrapper"
        ) as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.send_text = AsyncMock(return_value=mock_result)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock()
            mock_client_cls.return_value = mock_client

            node = create_a2a_node(config)
            state = {"custom_query": "Custom input"}

            await node(state)

            call_args = mock_client.send_text.call_args
            assert call_args[0][0] == "Custom input"

    async def test_node_uses_custom_output_transform(self, mock_result):
        """Node uses custom output transform when provided."""

        def custom_output(result, state):
            return {"answer": result.response_text.upper()}

        config = A2ANodeConfig(
            base_url="http://example.com",
            transform_output=custom_output,
        )

        with patch(
            "my_agentic_serviceservice_order_specialist.platform.clients.a2a.langgraph.nodes.A2AClientWrapper"
        ) as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.send_text = AsyncMock(return_value=mock_result)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock()
            mock_client_cls.return_value = mock_client

            node = create_a2a_node(config)
            msg = Mock()
            msg.content = "Hello"
            state = {"messages": [msg]}

            result = await node(state)

            assert result["answer"] == "AGENT RESPONSE"


class TestCreateMultiAgentRouter:
    """Tests for create_multi_agent_router()."""

    @pytest.fixture
    def mock_result(self):
        """Create a mock ExecutionResult."""
        task = Mock()
        return ExecutionResult(
            task=task,
            response_text="Response from agent",
            task_id="task-123",
            context_id="ctx-456",
            state=Mock(),
            artifacts=[],
        )

    async def test_routes_to_correct_agent(self, mock_result):
        """Router calls the agent selected by router_fn."""
        agents = {
            "search": A2ANodeConfig(base_url="http://search.example.com"),
            "math": A2ANodeConfig(base_url="http://math.example.com"),
        }

        def router_fn(state):
            return state["agent_type"]

        with patch(
            "my_agentic_serviceservice_order_specialist.platform.clients.a2a.langgraph.nodes.A2AClientWrapper"
        ) as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.send_text = AsyncMock(return_value=mock_result)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock()
            mock_client_cls.return_value = mock_client

            router = create_multi_agent_router(agents, router_fn)
            msg = Mock()
            msg.content = "2 + 2"
            state = {"agent_type": "math", "messages": [msg]}

            result = await router(state)

            assert result["a2a_response"] == "Response from agent"
            mock_client_cls.assert_called_with(
                base_url="http://math.example.com",
                config=None,
                auth=None,
            )

    async def test_raises_on_unknown_agent(self, mock_result):
        """Router raises ValueError for unknown agent."""
        agents = {
            "search": A2ANodeConfig(base_url="http://search.example.com"),
        }

        def router_fn(state):
            return "unknown_agent"

        router = create_multi_agent_router(agents, router_fn)
        state = {"messages": []}

        with pytest.raises(ValueError, match="Unknown agent"):
            await router(state)

    async def test_router_passes_correct_config(self, mock_result):
        """Router passes agent-specific config."""
        client_config = A2AClientConfig(timeout_seconds=60.0)
        auth = AuthConfig(api_key="agent-key")

        agents = {
            "special": A2ANodeConfig(
                base_url="http://special.example.com",
                client_config=client_config,
                auth=auth,
            ),
        }

        def router_fn(state):
            return "special"

        with patch(
            "my_agentic_serviceservice_order_specialist.platform.clients.a2a.langgraph.nodes.A2AClientWrapper"
        ) as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.send_text = AsyncMock(return_value=mock_result)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock()
            mock_client_cls.return_value = mock_client

            router = create_multi_agent_router(agents, router_fn)
            msg = Mock()
            msg.content = "Query"
            state = {"messages": [msg]}

            await router(state)

            mock_client_cls.assert_called_with(
                base_url="http://special.example.com",
                config=client_config,
                auth=auth,
            )
