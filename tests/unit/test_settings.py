"""Unit tests for application settings.

This module tests all Pydantic settings classes and their validators.
"""

import pytest
from pydantic import ValidationError

from my_agentic_serviceservice_order_specialist.platform.settings import (
    A2ASettings,
    AgentRegistrySettings,
    AgentsMCPSettings,
    AppHTTPSettings,
    BugsnagSettings,
    DBConnectionSettings,
    LitellmSettings,
    MCPServerSettings,
    OpenTelemetrySettings,
    Settings,
)


class TestAppHTTPSettings:
    """Tests for AppHTTPSettings configuration."""

    def test_default_values(self):
        """Settings should have sensible defaults."""
        settings = AppHTTPSettings()
        assert settings.host == "0.0.0.0"
        assert settings.port == 8000
        assert settings.log_level == "INFO"

    def test_log_level_validation_valid(self):
        """Valid log levels should be accepted."""
        for level in ["DEBUG", "INFO", "WARNING", "ERROR", "debug", "info"]:
            settings = AppHTTPSettings(log_level=level)
            assert settings.log_level == level.upper()

    def test_log_level_validation_invalid(self):
        """Invalid log levels should raise ValidationError."""
        with pytest.raises(ValidationError):
            AppHTTPSettings(log_level="INVALID")


class TestBugsnagSettings:
    """Tests for BugsnagSettings configuration."""

    def test_valid_release_stages(self):
        """Valid release stages should be accepted."""
        for stage in ["development", "production", "local"]:
            settings = BugsnagSettings(api_key="test-key", release_stage=stage)
            assert settings.release_stage == stage

    def test_invalid_release_stage(self):
        """Invalid release stage should raise ValidationError."""
        with pytest.raises(ValidationError):
            BugsnagSettings(api_key="test-key", release_stage="staging")


class TestDBConnectionSettings:
    """Tests for database connection settings."""

    def test_all_fields_required(self):
        """All connection fields should be required."""
        with pytest.raises(ValidationError):
            DBConnectionSettings()  # type: ignore

    def test_valid_connection(self):
        """Valid connection settings should be accepted."""
        settings = DBConnectionSettings(
            host="localhost",
            port=5432,
            user="postgres",
            password="secret",
            database="testdb",
        )
        assert settings.host == "localhost"
        assert settings.port == 5432
        assert settings.echo is False  # Default value

    def test_echo_can_be_enabled(self):
        """Echo setting can be explicitly enabled."""
        settings = DBConnectionSettings(
            host="localhost",
            port=5432,
            user="postgres",
            password="secret",
            database="testdb",
            echo=True,
        )
        assert settings.echo is True


class TestOpenTelemetrySettings:
    """Tests for OpenTelemetry configuration."""

    def test_default_values(self):
        """OpenTelemetry settings should have sensible defaults."""
        settings = OpenTelemetrySettings()
        assert settings.host == ""
        assert settings.port == 4317
        assert settings.enabled is True
        assert settings.excluded_urls == "metrics,health,info"

    def test_custom_values(self):
        """Custom values should override defaults."""
        settings = OpenTelemetrySettings(
            host="otel-collector",
            port=4318,
            enabled=False,
            excluded_urls="health",
        )
        assert settings.host == "otel-collector"
        assert settings.port == 4318
        assert settings.enabled is False
        assert settings.excluded_urls == "health"


class TestLitellmSettings:
    """Tests for LiteLLM proxy configuration."""

    def test_all_fields_required(self):
        """Both proxy fields are required."""
        with pytest.raises(ValidationError):
            LitellmSettings()  # type: ignore

    def test_missing_api_base(self):
        """Missing api_base should raise ValidationError."""
        with pytest.raises(ValidationError):
            LitellmSettings(proxy_api_key="key")  # type: ignore

    def test_missing_api_key(self):
        """Missing api_key should raise ValidationError."""
        with pytest.raises(ValidationError):
            LitellmSettings(proxy_api_base="http://localhost")  # type: ignore

    def test_valid_settings(self):
        """Valid LiteLLM settings should be accepted."""
        settings = LitellmSettings(
            proxy_api_base="http://litellm:4000",
            proxy_api_key="sk-test-key",
        )
        assert settings.proxy_api_base == "http://litellm:4000"
        assert settings.proxy_api_key == "sk-test-key"


class TestMCPServerSettings:
    """Tests for MCP server configuration."""

    def test_url_required(self):
        """URL is required for MCP server."""
        with pytest.raises(ValidationError):
            MCPServerSettings()  # type: ignore

    def test_default_values(self):
        """MCP server settings should have sensible defaults."""
        settings = MCPServerSettings(url="http://mcp-server:8080")
        assert settings.url == "http://mcp-server:8080"
        assert settings.prefix is None
        assert settings.timeout == 60.0
        assert settings.sse_read_timeout == 300.0
        assert settings.read_timeout == 120.0

    def test_custom_values(self):
        """Custom values should override defaults."""
        settings = MCPServerSettings(
            url="http://custom:9000",
            prefix="tools",
            timeout=30.0,
            sse_read_timeout=600.0,
            read_timeout=60.0,
        )
        assert settings.url == "http://custom:9000"
        assert settings.prefix == "tools"
        assert settings.timeout == 30.0
        assert settings.sse_read_timeout == 600.0
        assert settings.read_timeout == 60.0


class TestAgentsMCPSettings:
    """Tests for per-agent MCP configurations."""

    def test_default_empty_list(self):
        """Knowledge MCP servers default to empty list."""
        settings = AgentsMCPSettings()
        assert settings.knowledge == []

    def test_single_server(self):
        """Single MCP server can be configured."""
        server = MCPServerSettings(url="http://mcp:8080")
        settings = AgentsMCPSettings(knowledge=[server])
        assert len(settings.knowledge) == 1
        assert settings.knowledge[0].url == "http://mcp:8080"

    def test_multiple_servers(self):
        """Multiple MCP servers can be configured."""
        servers = [
            MCPServerSettings(url="http://mcp1:8080", prefix="mcp1"),
            MCPServerSettings(url="http://mcp2:8080", prefix="mcp2"),
        ]
        settings = AgentsMCPSettings(knowledge=servers)
        assert len(settings.knowledge) == 2
        assert settings.knowledge[0].prefix == "mcp1"
        assert settings.knowledge[1].prefix == "mcp2"


class TestA2ASettings:
    """Tests for A2A protocol configuration."""

    def test_default_values(self):
        """A2A settings should have sensible defaults."""
        settings = A2ASettings()
        assert settings.protocol_version == "0.3.0"
        assert settings.path == "/a2a"
        assert settings.agent_card_path == ".well-known/agent-card.json"

    def test_custom_values(self):
        """Custom values should override defaults."""
        settings = A2ASettings(
            protocol_version="1.0.0",
            path="/agent",
            agent_card_path="agent-card.json",
        )
        assert settings.protocol_version == "1.0.0"
        assert settings.path == "/agent"
        assert settings.agent_card_path == "agent-card.json"


class TestAgentRegistrySettings:
    """Tests for agent registry configuration."""

    def test_default_values(self):
        """Registry settings should have sensible defaults."""
        settings = AgentRegistrySettings()
        assert settings.url == ""
        assert settings.enabled is True

    def test_should_register_when_url_and_enabled(self):
        """should_register is True when URL is set and enabled."""
        settings = AgentRegistrySettings(url="http://registry:8080", enabled=True)
        assert settings.should_register is True

    def test_should_not_register_when_disabled(self):
        """should_register is False when disabled."""
        settings = AgentRegistrySettings(url="http://registry:8080", enabled=False)
        assert settings.should_register is False

    def test_should_not_register_when_url_empty(self):
        """should_register is False when URL is empty."""
        settings = AgentRegistrySettings(url="", enabled=True)
        assert settings.should_register is False

    def test_should_not_register_when_both_missing(self):
        """should_register is False with defaults."""
        settings = AgentRegistrySettings()
        assert settings.should_register is False


class TestAppHTTPSettingsExtended:
    """Extended tests for AppHTTPSettings edge cases."""

    def test_url_default_empty(self):
        """URL defaults to empty string."""
        settings = AppHTTPSettings()
        assert settings.url == ""

    def test_log_json_default_none(self):
        """log_json defaults to None (auto-detect)."""
        settings = AppHTTPSettings()
        assert settings.log_json is None

    def test_log_json_explicit_true(self):
        """log_json can be set to True for JSON format."""
        settings = AppHTTPSettings(log_json=True)
        assert settings.log_json is True

    def test_log_json_explicit_false(self):
        """log_json can be set to False for console format."""
        settings = AppHTTPSettings(log_json=False)
        assert settings.log_json is False

    def test_log_level_critical(self):
        """CRITICAL log level should be accepted."""
        settings = AppHTTPSettings(log_level="CRITICAL")
        assert settings.log_level == "CRITICAL"

    def test_log_level_notset(self):
        """NOTSET log level should be accepted."""
        settings = AppHTTPSettings(log_level="NOTSET")
        assert settings.log_level == "NOTSET"

    def test_custom_port(self):
        """Custom port should be accepted."""
        settings = AppHTTPSettings(port=3000)
        assert settings.port == 3000


class TestSettings:
    """Tests for the main Settings class."""

    @pytest.fixture
    def valid_settings(self) -> Settings:
        """Create a valid Settings instance with all required fields."""
        return Settings(
            app_http=AppHTTPSettings(url="http://localhost", port=8000),
            opentelemetry=OpenTelemetrySettings(),
            bugsnag=BugsnagSettings(api_key="test-key"),
            primary_db=DBConnectionSettings(
                host="localhost",
                port=5432,
                user="postgres",
                password="secret",
                database="primary",
            ),
            replica_db=DBConnectionSettings(
                host="localhost",
                port=5432,
                user="postgres",
                password="secret",
                database="replica",
            ),
            litellm=LitellmSettings(
                proxy_api_base="http://litellm:4000",
                proxy_api_key="sk-test",
            ),
            a2a=A2ASettings(),
        )

    def test_a2a_base_url_default_path(self, valid_settings: Settings):
        """a2a_base_url combines app_http url, port, and a2a path."""
        assert valid_settings.a2a_base_url == "http://localhost:8000/a2a"

    def test_a2a_base_url_custom_path(self):
        """a2a_base_url uses custom a2a path when configured."""
        settings = Settings(
            app_http=AppHTTPSettings(url="https://api.example.com", port=443),
            opentelemetry=OpenTelemetrySettings(),
            bugsnag=BugsnagSettings(api_key="test-key"),
            primary_db=DBConnectionSettings(
                host="localhost",
                port=5432,
                user="postgres",
                password="secret",
                database="primary",
            ),
            replica_db=DBConnectionSettings(
                host="localhost",
                port=5432,
                user="postgres",
                password="secret",
                database="replica",
            ),
            litellm=LitellmSettings(
                proxy_api_base="http://litellm:4000",
                proxy_api_key="sk-test",
            ),
            a2a=A2ASettings(path="/agent/v1"),
        )
        assert settings.a2a_base_url == "https://api.example.com:443/agent/v1"

    def test_settings_defaults_for_optional_fields(self, valid_settings: Settings):
        """Optional fields should have sensible defaults."""
        assert valid_settings.agent_registry.url == ""
        assert valid_settings.agent_registry.enabled is True
        assert valid_settings.agents_mcp.knowledge == []
