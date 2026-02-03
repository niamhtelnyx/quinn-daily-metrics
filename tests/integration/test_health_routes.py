"""Integration tests for health check endpoints.

Tests the /health, /info, and /metrics endpoints.
"""

from fastapi.testclient import TestClient


class TestHealthEndpoint:
    """Tests for GET /health endpoint."""

    def test_health_returns_ok_when_enabled(self, client_with_health_enabled: TestClient):
        """Health check returns OK when enabled."""
        response = client_with_health_enabled.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "OK"

    def test_health_returns_404_when_disabled(self, client_with_health_disabled: TestClient):
        """Health check returns 404 when disabled (graceful shutdown)."""
        response = client_with_health_disabled.get("/health")

        assert response.status_code == 404


class TestInfoEndpoint:
    """Tests for GET /info endpoint."""

    def test_info_returns_200(self, client: TestClient):
        """Info endpoint returns 200."""
        response = client.get("/info")

        assert response.status_code == 200

    def test_info_contains_metadata(self, client: TestClient):
        """Info endpoint contains service metadata."""
        response = client.get("/info")

        data = response.json()
        # MetadataManager provides these fields
        assert "started" in data
        assert "uptime_seconds" in data
        assert "hostname" in data

    def test_info_contains_uptime(self, client: TestClient):
        """Info endpoint shows uptime in seconds."""
        response = client.get("/info")

        data = response.json()
        assert isinstance(data["uptime_seconds"], (int, float))
        assert data["uptime_seconds"] >= 0

    def test_info_started_is_iso_format(self, client: TestClient):
        """Info started timestamp is in ISO format."""
        response = client.get("/info")

        data = response.json()
        # ISO format contains 'T' separator
        assert "T" in data["started"]


class TestMetricsEndpoint:
    """Tests for GET /metrics endpoint."""

    def test_metrics_returns_200(self, client: TestClient):
        """Metrics endpoint returns 200."""
        response = client.get("/metrics")

        assert response.status_code == 200

    def test_metrics_prometheus_format(self, client: TestClient):
        """Metrics endpoint returns Prometheus format."""
        response = client.get("/metrics")

        # Prometheus metrics have specific content type
        content_type = response.headers["content-type"]
        assert "text/plain" in content_type or "text/plain" in content_type

    def test_metrics_contains_python_info(self, client: TestClient):
        """Metrics contains Python runtime info (from prometheus_client)."""
        response = client.get("/metrics")

        # prometheus_client includes python_info by default
        assert "python_info" in response.text or "process_" in response.text
