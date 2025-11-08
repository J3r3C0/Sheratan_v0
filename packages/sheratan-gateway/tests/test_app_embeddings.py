"""Integration tests for gateway with embeddings"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch
import sheratan_gateway.app as gateway_app


client = TestClient(gateway_app.app)


class TestGatewayEmbeddingsIntegration:
    """Tests for gateway embeddings integration"""
    
    def setup_method(self):
        """Reset global provider before each test"""
        gateway_app._embedding_provider = None
    
    def test_health_endpoint_shows_embeddings_provider(self):
        """Test that health endpoint reports embeddings provider"""
        with patch.dict('os.environ', {"EMBEDDINGS_PROVIDER": "local"}):
            response = client.get("/health")
            assert response.status_code == 200
            data = response.json()
            assert "embeddings_provider" in data
    
    def test_search_with_off_provider(self):
        """Test search endpoint with embeddings disabled"""
        with patch.dict('os.environ', {"EMBEDDINGS_PROVIDER": "off"}):
            gateway_app._embedding_provider = None  # Reset cache
            
            response = client.post("/search", json={
                "query": "test query",
                "top_k": 5
            })
            
            assert response.status_code == 200
            data = response.json()
            assert data["query"] == "test query"
            assert data["results"] == []
            assert data["total"] == 0
    
    def test_search_with_local_provider(self):
        """Test search endpoint with local embeddings"""
        mock_provider = Mock()
        mock_provider.embed_query.return_value = [0.1, 0.2, 0.3]
        
        with patch.dict('os.environ', {"EMBEDDINGS_PROVIDER": "local"}):
            gateway_app._embedding_provider = mock_provider  # Set mock directly
            
            response = client.post("/search", json={
                "query": "test query",
                "top_k": 5
            })
            
            assert response.status_code == 200
            data = response.json()
            assert data["query"] == "test query"
            mock_provider.embed_query.assert_called_once_with("test query")
    
    def test_search_handles_provider_error(self):
        """Test that search handles provider errors gracefully"""
        mock_provider = Mock()
        mock_provider.embed_query.side_effect = Exception("Provider error")
        
        with patch.dict('os.environ', {"EMBEDDINGS_PROVIDER": "local"}):
            gateway_app._embedding_provider = mock_provider  # Set mock directly
            
            response = client.post("/search", json={
                "query": "test query",
                "top_k": 5
            })
            
            assert response.status_code == 500
            assert "Search failed" in response.json()["detail"]
    
    def test_ingest_endpoint(self):
        """Test ingest endpoint"""
        response = client.post("/ingest", json={
            "documents": [
                {"content": "Test document 1"},
                {"content": "Test document 2"}
            ]
        })
        
        assert response.status_code == 201
        data = response.json()
        assert data["success"] is True
        assert len(data["document_ids"]) == 2
    
    def test_answer_endpoint_requires_llm(self):
        """Test that answer endpoint requires LLM to be enabled"""
        with patch.dict('os.environ', {"LLM_ENABLED": "false"}):
            response = client.post("/answer", json={
                "question": "What is this about?"
            })
            
            assert response.status_code == 503
            assert "LLM is not enabled" in response.json()["detail"]
    
    def test_search_validates_top_k(self):
        """Test that search validates top_k parameter"""
        # Test with invalid top_k (too high)
        response = client.post("/search", json={
            "query": "test",
            "top_k": 101
        })
        assert response.status_code == 422  # Validation error
        
        # Test with invalid top_k (too low)
        response = client.post("/search", json={
            "query": "test",
            "top_k": 0
        })
        assert response.status_code == 422  # Validation error
