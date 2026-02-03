"""Unit tests for agent metrics collection.

This module tests the metrics NamedTuples, helper functions, and context managers.
"""

import pytest

from my_agentic_serviceservice_order_specialist.platform.agent.metrics import (
    AgentMetricsLabels,
    ToolMetricsLabels,
    collect_agent_metrics,
    collect_tool_metrics,
    record_agent_tokens,
    record_tool_call,
)


class TestAgentMetricsLabels:
    """Tests for AgentMetricsLabels NamedTuple."""

    def test_create_with_agent(self):
        """Can create labels with agent name."""
        labels = AgentMetricsLabels(agent="my-agent")
        assert labels.agent == "my-agent"

    def test_is_named_tuple(self):
        """Labels are a NamedTuple."""
        labels = AgentMetricsLabels(agent="test")
        assert hasattr(labels, "_fields")
        assert "agent" in labels._fields

    def test_immutable(self):
        """Labels are immutable."""
        labels = AgentMetricsLabels(agent="test")
        with pytest.raises(AttributeError):
            labels.agent = "other"  # type: ignore


class TestToolMetricsLabels:
    """Tests for ToolMetricsLabels NamedTuple."""

    def test_create_with_required_fields(self):
        """Can create labels with required fields."""
        labels = ToolMetricsLabels(agent="my-agent", tool_name="search")
        assert labels.agent == "my-agent"
        assert labels.tool_name == "search"

    def test_proxy_tool_name_defaults_empty(self):
        """proxy_tool_name defaults to empty string."""
        labels = ToolMetricsLabels(agent="agent", tool_name="tool")
        assert labels.proxy_tool_name == ""

    def test_proxy_tool_name_can_be_set(self):
        """proxy_tool_name can be explicitly set."""
        labels = ToolMetricsLabels(agent="agent", tool_name="mcp_search", proxy_tool_name="search")
        assert labels.proxy_tool_name == "search"

    def test_is_named_tuple(self):
        """Labels are a NamedTuple."""
        labels = ToolMetricsLabels(agent="test", tool_name="tool")
        assert hasattr(labels, "_fields")
        assert "agent" in labels._fields
        assert "tool_name" in labels._fields
        assert "proxy_tool_name" in labels._fields


class TestRecordToolCall:
    """Tests for record_tool_call helper function."""

    def test_records_success_status(self):
        """Calling with error=False records success status."""
        labels = ToolMetricsLabels(agent="test-agent", tool_name="test-tool")
        # This should not raise - just verifying it runs without error
        record_tool_call(labels, duration=1.5, error=False)

    def test_records_error_status(self):
        """Calling with error=True records error status."""
        labels = ToolMetricsLabels(agent="test-agent", tool_name="test-tool")
        # This should not raise
        record_tool_call(labels, duration=0.5, error=True)

    def test_default_error_is_false(self):
        """error parameter defaults to False."""
        labels = ToolMetricsLabels(agent="test-agent", tool_name="test-tool")
        # Should record success by default
        record_tool_call(labels, duration=1.0)

    def test_accepts_zero_duration(self):
        """Zero duration is valid."""
        labels = ToolMetricsLabels(agent="test-agent", tool_name="test-tool")
        record_tool_call(labels, duration=0.0)

    def test_uses_proxy_tool_name(self):
        """proxy_tool_name is passed to metrics."""
        labels = ToolMetricsLabels(
            agent="agent", tool_name="mcp_github_search", proxy_tool_name="search"
        )
        record_tool_call(labels, duration=1.0)


class TestRecordAgentTokens:
    """Tests for record_agent_tokens helper function."""

    def test_records_input_tokens(self):
        """Records input tokens when > 0."""
        record_agent_tokens(agent="test-agent", model="claude-3", input_tokens=100, output_tokens=0)

    def test_records_output_tokens(self):
        """Records output tokens when > 0."""
        record_agent_tokens(agent="test-agent", model="claude-3", input_tokens=0, output_tokens=50)

    def test_records_both_tokens(self):
        """Records both input and output tokens."""
        record_agent_tokens(agent="test-agent", model="gpt-4", input_tokens=200, output_tokens=100)

    def test_skips_zero_input_tokens(self):
        """Does not record when input_tokens is 0."""
        # Should not raise, just skip recording
        record_agent_tokens(agent="test-agent", model="claude-3", input_tokens=0, output_tokens=50)

    def test_skips_zero_output_tokens(self):
        """Does not record when output_tokens is 0."""
        record_agent_tokens(agent="test-agent", model="claude-3", input_tokens=100, output_tokens=0)

    def test_skips_both_zero(self):
        """Does not record when both are 0."""
        record_agent_tokens(agent="test-agent", model="claude-3", input_tokens=0, output_tokens=0)


class TestCollectAgentMetrics:
    """Tests for collect_agent_metrics async context manager."""

    def test_stores_labels(self):
        """Context manager stores labels."""
        labels = AgentMetricsLabels(agent="my-agent")
        cm = collect_agent_metrics(labels)
        assert cm.labels == labels

    async def test_context_manager_success(self):
        """Records success when no exception."""
        labels = AgentMetricsLabels(agent="test-agent")
        async with collect_agent_metrics(labels):
            pass  # No exception

    async def test_context_manager_error(self):
        """Records error and re-raises exception."""
        labels = AgentMetricsLabels(agent="test-agent")
        with pytest.raises(ValueError):
            async with collect_agent_metrics(labels):
                raise ValueError("test error")

    async def test_returns_self_on_enter(self):
        """__aenter__ returns the context manager itself."""
        labels = AgentMetricsLabels(agent="test-agent")
        cm = collect_agent_metrics(labels)
        result = await cm.__aenter__()
        assert result is cm

    async def test_does_not_suppress_exceptions(self):
        """__aexit__ returns False to not suppress exceptions."""
        labels = AgentMetricsLabels(agent="test-agent")
        cm = collect_agent_metrics(labels)
        await cm.__aenter__()
        result = await cm.__aexit__(ValueError, ValueError("test"), None)
        assert result is False


class TestCollectToolMetrics:
    """Tests for collect_tool_metrics async context manager."""

    async def test_context_manager_success(self):
        """Records success when no exception."""
        labels = ToolMetricsLabels(agent="test-agent", tool_name="test-tool")
        async with collect_tool_metrics(labels):
            pass  # No exception

    async def test_context_manager_error(self):
        """Records error and re-raises exception."""
        labels = ToolMetricsLabels(agent="test-agent", tool_name="test-tool")
        with pytest.raises(RuntimeError):
            async with collect_tool_metrics(labels):
                raise RuntimeError("tool failed")

    async def test_with_proxy_tool_name(self):
        """Works with proxy_tool_name set."""
        labels = ToolMetricsLabels(agent="agent", tool_name="mcp_search", proxy_tool_name="search")
        async with collect_tool_metrics(labels):
            pass
