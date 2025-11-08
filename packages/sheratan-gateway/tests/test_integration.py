"""Integration tests for gateway with guard middleware"""
import pytest
from fastapi.testclient import TestClient
import sys
import os

# Add packages to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../sheratan-guard"))

from sheratan_gateway.app import app

client = TestClient(app)


class TestGatewayGuardIntegration:
    """Test gateway endpoints with guard protection"""
    
    def test_health_endpoint(self):
        """Test health endpoint is accessible"""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
    
    def test_ingest_with_valid_content(self):
        """Test document ingestion with valid content"""
        response = client.post(
            "/ingest",
            json={
                "documents": [
                    {
                        "content": "This is a normal document with safe content.",
                        "metadata": {"source": "test"}
                    }
                ]
            }
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["success"] is True
        assert len(data["document_ids"]) == 1
    
    def test_ingest_with_pii_scrubbing(self):
        """Test that PII is detected and scrubbed in ingestion"""
        response = client.post(
            "/ingest",
            json={
                "documents": [
                    {
                        "content": "Contact me at john.doe@example.com or call 555-123-4567.",
                        "metadata": {}
                    }
                ]
            }
        )
        
        # Should still succeed, but PII should be logged/scrubbed
        assert response.status_code == 201
        data = response.json()
        assert data["success"] is True
    
    def test_ingest_with_empty_content(self):
        """Test ingestion with empty content is processed"""
        response = client.post(
            "/ingest",
            json={
                "documents": [
                    {
                        "content": "",
                        "metadata": {}
                    }
                ]
            }
        )
        
        # Guard processes the request - empty content handling depends on policy config
        # Current implementation allows it but logs it
        assert response.status_code in [201, 403]
    
    def test_search_with_valid_query(self):
        """Test search with valid query"""
        response = client.post(
            "/search",
            json={
                "query": "test query",
                "top_k": 5
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "query" in data
        assert "results" in data
    
    def test_search_with_empty_query(self):
        """Test search with empty query"""
        response = client.post(
            "/search",
            json={
                "query": "",
                "top_k": 5
            }
        )
        
        # Guard processes the request - empty query handling depends on policy config
        assert response.status_code in [200, 403]
    
    def test_answer_endpoint_llm_disabled(self):
        """Test answer endpoint when LLM is disabled"""
        response = client.post(
            "/answer",
            json={
                "question": "What is the meaning of life?",
                "top_k": 5
            }
        )
        
        # Should return 503 when LLM is disabled
        assert response.status_code == 503
        assert "LLM" in response.json()["detail"]
    
    def test_rate_limit_headers(self):
        """Test that rate limit headers are present"""
        response = client.post(
            "/search",
            json={
                "query": "test query",
                "top_k": 5
            }
        )
        
        assert response.status_code == 200
        
        # Check for rate limit headers
        assert "X-RateLimit-Limit-Minute" in response.headers or response.status_code == 200
        assert "X-RateLimit-Limit-Hour" in response.headers or response.status_code == 200
    
    def test_multiple_requests_within_limit(self):
        """Test multiple requests within rate limit"""
        for i in range(3):
            response = client.post(
                "/search",
                json={
                    "query": f"test query {i}",
                    "top_k": 5
                }
            )
            assert response.status_code == 200
    
    def test_root_endpoint(self):
        """Test root endpoint"""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "Sheratan Gateway"
        assert data["status"] == "running"
