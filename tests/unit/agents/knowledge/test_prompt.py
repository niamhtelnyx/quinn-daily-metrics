"""Unit tests for system prompt builder.

This module tests the build_system_prompt function.
"""

from my_agentic_serviceservice_order_specialist.agents.knowledge.prompt import build_system_prompt


class TestBuildSystemPrompt:
    """Tests for build_system_prompt function."""

    def test_returns_string(self):
        """Function returns a string."""
        result = build_system_prompt()
        assert isinstance(result, str)

    def test_default_no_custom_instructions(self):
        """Returns base prompt when called without arguments."""
        result = build_system_prompt()
        assert len(result) > 0
        assert "Telnyx" in result

    def test_none_custom_instructions(self):
        """Returns base prompt when custom_instructions is None."""
        result = build_system_prompt(custom_instructions=None)
        assert "Telnyx" in result

    def test_base_prompt_contains_telnyx_context(self):
        """Base prompt establishes Telnyx context."""
        result = build_system_prompt()
        assert "Telnyx" in result
        assert "expert assistant" in result

    def test_base_prompt_contains_tool_instructions(self):
        """Base prompt includes MCP Proxy pattern instructions."""
        result = build_system_prompt()
        assert "MCP Proxy" in result
        assert "fetch_relevant_tools" in result
        assert "execute_tool" in result

    def test_base_prompt_contains_rules(self):
        """Base prompt includes general rules."""
        result = build_system_prompt()
        assert "General Rules" in result
        assert "Minimize tool calls" in result
        assert "Use concrete values" in result
        assert "Stay factual" in result

    def test_custom_instructions_appended(self):
        """Custom instructions are appended to base prompt."""
        custom = "Always respond in Spanish."
        result = build_system_prompt(custom_instructions=custom)
        assert custom in result
        assert result.endswith(custom)

    def test_custom_instructions_separated_by_double_newline(self):
        """Custom instructions are separated from base by double newline."""
        custom = "Custom instruction here."
        result = build_system_prompt(custom_instructions=custom)
        assert f"\n\n{custom}" in result

    def test_base_prompt_unchanged_with_custom(self):
        """Base prompt content is preserved when custom instructions added."""
        base_result = build_system_prompt()
        custom_result = build_system_prompt(custom_instructions="Extra info")

        # Custom result should start with the base prompt
        assert custom_result.startswith(base_result[:100])
        assert "Telnyx" in custom_result
        assert "MCP Proxy" in custom_result

    def test_empty_string_custom_instructions(self):
        """Empty string custom_instructions is falsy, returns base only."""
        result = build_system_prompt(custom_instructions="")
        # Empty string is falsy, so should return base prompt only
        base_result = build_system_prompt()
        assert result == base_result
