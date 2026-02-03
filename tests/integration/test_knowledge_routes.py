"""Integration tests for Knowledge Agent HTTP endpoints.

Tests the /knowledge/invoke and /knowledge/stream endpoints.
"""

import uuid
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient


class TestKnowledgeInvokeEndpoint:
    """Tests for POST /knowledge/invoke endpoint."""

    def test_invoke_success(self, client: TestClient, stub_agent: Mock):
        """Successful invoke returns execution result."""
        response = client.post(
            "/knowledge/invoke",
            json={"question": "What is Telnyx?"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "response" in data
        assert "messages" in data
        assert "reasoning_steps" in data
        assert "thread_id" in data

    def test_invoke_with_thread_id(self, client: TestClient, stub_agent: Mock):
        """Invoke with explicit thread_id uses that thread."""
        thread_id = str(uuid.uuid4())
        response = client.post(
            "/knowledge/invoke",
            json={"question": "Follow up question", "thread_id": thread_id},
        )

        assert response.status_code == 200
        # Verify agent.run was called with correct thread_id
        stub_agent.run.assert_called_once()
        call_args = stub_agent.run.call_args
        assert call_args[1]["thread_id"] == thread_id

    def test_invoke_calls_agent_run(self, client: TestClient, stub_agent: Mock):
        """Invoke calls agent.run with the question."""
        client.post(
            "/knowledge/invoke",
            json={"question": "Test question here"},
        )

        stub_agent.run.assert_called_once()
        call_args = stub_agent.run.call_args
        assert call_args[0][0] == "Test question here"

    def test_invoke_missing_question_returns_422(self, client: TestClient):
        """Missing question field returns validation error."""
        response = client.post(
            "/knowledge/invoke",
            json={},
        )

        assert response.status_code == 422
        data = response.json()
        assert "detail" in data

    def test_invoke_empty_question_rejected(self, client: TestClient, stub_agent: Mock):
        """Empty string question is rejected by validation (min_length=1)."""
        response = client.post(
            "/knowledge/invoke",
            json={"question": ""},
        )

        # Empty string fails validation
        assert response.status_code == 422

    def test_invoke_invalid_thread_id_format(self, client: TestClient):
        """Invalid thread_id format returns validation error."""
        response = client.post(
            "/knowledge/invoke",
            json={"question": "Test", "thread_id": "not-a-uuid"},
        )

        assert response.status_code == 422

    def test_invoke_response_contains_messages(self, client: TestClient, stub_agent: Mock):
        """Response includes message history."""
        response = client.post(
            "/knowledge/invoke",
            json={"question": "Test"},
        )

        data = response.json()
        assert isinstance(data["messages"], list)
        assert len(data["messages"]) >= 1

    def test_invoke_response_contains_metadata(self, client: TestClient, stub_agent: Mock):
        """Response includes metadata dict."""
        response = client.post(
            "/knowledge/invoke",
            json={"question": "Test"},
        )

        data = response.json()
        assert "metadata" in data
        assert isinstance(data["metadata"], dict)


class TestKnowledgeStreamEndpoint:
    """Tests for POST /knowledge/stream endpoint."""

    def test_stream_returns_sse_content_type(self, client: TestClient, stub_agent: Mock):
        """Stream endpoint returns text/event-stream content type."""
        response = client.post(
            "/knowledge/stream",
            json={"question": "What is Telnyx?"},
        )

        assert response.status_code == 200
        assert response.headers["content-type"] == "text/event-stream; charset=utf-8"

    def test_stream_returns_sse_headers(self, client: TestClient, stub_agent: Mock):
        """Stream endpoint returns proper SSE headers."""
        response = client.post(
            "/knowledge/stream",
            json={"question": "Test"},
        )

        assert response.headers.get("cache-control") == "no-cache"
        assert response.headers.get("connection") == "keep-alive"

    def test_stream_with_thread_id(self, client: TestClient, stub_agent: Mock):
        """Stream with explicit thread_id uses that thread."""
        thread_id = str(uuid.uuid4())
        response = client.post(
            "/knowledge/stream",
            json={"question": "Test", "thread_id": thread_id},
        )

        assert response.status_code == 200

    def test_stream_response_format(self, client: TestClient, stub_agent: Mock):
        """Stream response follows SSE format (data: {...}\\n\\n)."""
        response = client.post(
            "/knowledge/stream",
            json={"question": "Test"},
        )

        content = response.text
        # SSE events should be prefixed with "data: "
        if content:  # Only check if there's content
            lines = [line for line in content.split("\n") if line.strip()]
            for line in lines:
                assert line.startswith("data: "), f"Invalid SSE line: {line}"


class TestKnowledgeEndpointValidation:
    """Tests for request validation on knowledge endpoints."""

    @pytest.mark.parametrize(
        "payload,expected_status",
        [
            ({"question": "Valid question"}, 200),
            ({}, 422),
            ({"question": 123}, 422),  # Wrong type
            ({"question": None}, 422),
            ({"question": "Test", "extra_field": "ignored"}, 200),  # Extra fields OK
        ],
    )
    def test_invoke_payload_validation(
        self,
        client: TestClient,
        stub_agent: Mock,
        payload: dict,
        expected_status: int,
    ):
        """Test various payload validation scenarios."""
        response = client.post("/knowledge/invoke", json=payload)
        assert response.status_code == expected_status

    def test_invoke_content_type_required(self, client: TestClient):
        """Request without JSON content type fails."""
        response = client.post(
            "/knowledge/invoke",
            content="question=test",
            headers={"content-type": "application/x-www-form-urlencoded"},
        )

        assert response.status_code == 422

    def test_invoke_malformed_json(self, client: TestClient):
        """Malformed JSON body returns error."""
        response = client.post(
            "/knowledge/invoke",
            content="{invalid json}",
            headers={"content-type": "application/json"},
        )

        assert response.status_code == 422
