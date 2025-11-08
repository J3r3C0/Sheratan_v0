"""Tests for FastAPI application endpoints"""
import pytest
import os
from fastapi.testclient import TestClient
from sheratan_gateway.app import app
from sheratan_gateway.auth import create_access_token


# Set test environment
os.environ["JWT_SECRET_KEY"] = "test-secret-key"
os.environ["API_KEYS"] = "test-api-key"
os.environ["DATABASE_URL"] = "postgresql://sheratan:sheratan@localhost:5432/sheratan_test"

client = TestClient(app)


def test_root_endpoint():
    """Test root endpoint"""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "Sheratan Gateway"
    assert data["version"] == "0.1.0"
    assert data["status"] == "running"


def test_health_endpoint():
    """Test health check endpoint"""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "timestamp" in data
    assert "llm_enabled" in data
    assert "embeddings_provider" in data


def test_auth_token_endpoint():
    """Test authentication token endpoint"""
    response = client.post(
        "/auth/token",
        json={"username": "testuser", "password": "testpass"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["expires_in"] == 1800  # 30 minutes


def test_auth_token_endpoint_no_username():
    """Test authentication token endpoint without username"""
    response = client.post(
        "/auth/token",
        json={"username": "", "password": "testpass"}
    )
    assert response.status_code == 400


def test_admin_endpoint_with_jwt():
    """Test admin endpoint with JWT authentication"""
    # Get token first
    token = create_access_token(data={"sub": "testuser"})
    
    response = client.get(
        "/admin",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "Sheratan Gateway"
    assert data["version"] == "0.1.0"
    assert data["status"] == "running"
    assert "database_url" in data
    assert "embeddings_provider" in data
    assert "llm_enabled" in data
    assert "auth_configured" in data
    assert "timestamp" in data
    # Password should be masked
    assert "***" in data["database_url"]


def test_admin_endpoint_with_api_key():
    """Test admin endpoint with API key authentication"""
    response = client.get(
        "/admin",
        headers={"X-API-Key": "test-api-key"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "Sheratan Gateway"


def test_admin_endpoint_no_auth():
    """Test admin endpoint without authentication"""
    # Temporarily clear API keys
    original_keys = os.environ.get("API_KEYS")
    os.environ["API_KEYS"] = ""
    
    # Need to reload app to pick up env change
    from importlib import reload
    from sheratan_gateway import auth
    reload(auth)
    
    response = client.get("/admin")
    # Should fail because JWT_SECRET_KEY is set (not default)
    # So auth is required
    assert response.status_code == 401
    
    # Restore
    if original_keys:
        os.environ["API_KEYS"] = original_keys


def test_ingest_endpoint_with_auth():
    """Test ingest endpoint with authentication"""
    token = create_access_token(data={"sub": "testuser"})
    
    response = client.post(
        "/ingest",
        json={
            "documents": [
                {
                    "content": "Test document content",
                    "metadata": {"source": "test"}
                }
            ]
        },
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 201
    data = response.json()
    assert data["success"] is True
    assert len(data["document_ids"]) == 1
    assert "message" in data


def test_ingest_endpoint_no_auth():
    """Test ingest endpoint without authentication"""
    response = client.post(
        "/ingest",
        json={
            "documents": [
                {
                    "content": "Test document content",
                    "metadata": {"source": "test"}
                }
            ]
        }
    )
    # Should fail because auth is required
    assert response.status_code == 401


def test_search_endpoint_with_auth():
    """Test search endpoint with authentication"""
    token = create_access_token(data={"sub": "testuser"})
    
    response = client.post(
        "/search",
        json={
            "query": "test query",
            "top_k": 5
        },
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["query"] == "test query"
    assert "results" in data
    assert "total" in data


def test_search_endpoint_no_auth():
    """Test search endpoint without authentication"""
    response = client.post(
        "/search",
        json={
            "query": "test query",
            "top_k": 5
        }
    )
    # Should fail because auth is required
    assert response.status_code == 401


def test_answer_endpoint_llm_disabled():
    """Test answer endpoint when LLM is disabled"""
    token = create_access_token(data={"sub": "testuser"})
    
    response = client.post(
        "/answer",
        json={
            "question": "What is this about?",
            "top_k": 5
        },
        headers={"Authorization": f"Bearer {token}"}
    )
    # Should fail because LLM is disabled by default
    assert response.status_code == 503
    data = response.json()
    assert "LLM is not enabled" in data["detail"]


def test_answer_endpoint_no_auth():
    """Test answer endpoint without authentication"""
    response = client.post(
        "/answer",
        json={
            "question": "What is this about?",
            "top_k": 5
        }
    )
    # Should fail because auth is required
    assert response.status_code == 401


def test_openapi_docs():
    """Test that OpenAPI documentation is available"""
    response = client.get("/openapi.json")
    assert response.status_code == 200
    data = response.json()
    assert "openapi" in data
    assert "info" in data
    assert "paths" in data
    # Check that our endpoints are documented
    assert "/ingest" in data["paths"]
    assert "/search" in data["paths"]
    assert "/answer" in data["paths"]
    assert "/admin" in data["paths"]
    assert "/auth/token" in data["paths"]
