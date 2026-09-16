"""
API Endpoint Tests with Asynchronous Mocking.
Tests FastAPI controllers, Pydantic request validation, and status codes
without incurring real LLM API costs or network latency.
"""

import os
import sys
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.main import app

# Initialize synchronous TestClient for FastAPI
client = TestClient(app)

def test_health_check_endpoint():
    """Verify that the GET /health endpoint returns 200 OK and expected status message."""
    response = client.get("/health")
    
    assert response.status_code == 200, "Health check must return HTTP 200"
    data = response.json()
    assert data["status"] == "ok"
    assert "Server is running" in data["message"]

def test_ask_endpoint_invalid_model_validation():
    """Verify that POST /ask rejects unauthorized/unsupported LLM model names."""
    invalid_payload = {
        "model_name": "unsupported-gpt-model-v1",
        "query": "What is the status of Project P185602?",
        "system_prompt": "You are a test assistant.",
        "allow_search": False,
        "thread_id": "test_session_invalid"
    }
    
    response = client.post("/ask", json=invalid_payload)
    
    assert response.status_code == 200
    data = response.json()
    assert "error" in data, "API must return an error field for invalid model names"
    assert "invalid Model Name" in data["error"]

@patch("src.routes.ask.get_response_from_ai_agent", new_callable=AsyncMock)
def test_ask_endpoint_successful_mocked_response(mock_agent_call):
    """
    Test POST /ask end-to-end using an asynchronous mock for the LLM Agent.
    Validates payload serialization and response contract with zero external API calls.
    """
    # Configure the mock stunt-double response
    mock_agent_call.return_value = {
        "answer": "The status for Project P185602 is: Open",
        "metrics": {
            "total_latency_ms": 120.5,
            "total_accumulated_tokens": 450,
            "node_latencies": [
                {"node": "agent_node", "latency_ms": 80.0},
                {"node": "tool_node", "tool": "search_project_database", "latency_ms": 40.5}
            ]
        }
    }

    valid_payload = {
        "model_name": "gemini-2.5-flash",
        "query": "What is the status of Project P185602?",
        "system_prompt": "You are an intelligent database assistant.",
        "allow_search": False,
        "thread_id": "mock_test_session_101"
    }

    # Execute HTTP POST request against FastAPI
    response = client.post("/ask", json=valid_payload)

    # Assertions
    assert response.status_code == 200, "Valid request must return HTTP 200"
    data = response.json()
    
    assert "answer" in data, "Response must contain 'answer' key"
    assert "Project P185602 is: Open" in data["answer"]
    assert "metrics" in data, "Response must contain 'metrics' telemetry"
    assert data["metrics"]["total_accumulated_tokens"] == 450

    # Verify that the mocked agent function was called exactly once with expected arguments
    mock_agent_call.assert_called_once_with(
        "gemini-2.5-flash",
        "What is the status of Project P185602?",
        False,
        "You are an intelligent database assistant.",
        "mock_test_session_101"
    )