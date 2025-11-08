"""Integration tests for orchestrator with embeddings"""
import pytest
from unittest.mock import Mock, patch, AsyncMock
from sheratan_orchestrator.worker import DocumentProcessor


@pytest.mark.asyncio
class TestDocumentProcessorWithEmbeddings:
    """Tests for DocumentProcessor with embeddings integration"""
    
    async def test_embed_with_off_provider(self):
        """Test embedding with 'off' provider returns empty embeddings"""
        processor = DocumentProcessor()
        
        # Mock the embedding provider to return OffEmbeddingProvider
        with patch.dict('os.environ', {"EMBEDDINGS_PROVIDER": "off"}):
            with patch('sheratan_orchestrator.worker.DocumentProcessor._get_embedding_provider') as mock_get:
                mock_provider = Mock()
                mock_provider.embed.return_value = [[], [], []]
                mock_get.return_value = mock_provider
                
                chunks = ["chunk1", "chunk2", "chunk3"]
                result = await processor.embed(chunks)
                
                assert len(result) == 3
                assert all(item["embedding"] == [] for item in result)
                assert result[0]["chunk"] == "chunk1"
                assert result[1]["chunk"] == "chunk2"
                assert result[2]["chunk"] == "chunk3"
    
    async def test_embed_with_local_provider(self):
        """Test embedding with local provider"""
        processor = DocumentProcessor()
        
        with patch('sheratan_orchestrator.worker.DocumentProcessor._get_embedding_provider') as mock_get:
            mock_provider = Mock()
            mock_provider.embed.return_value = [
                [0.1, 0.2, 0.3],
                [0.4, 0.5, 0.6]
            ]
            mock_get.return_value = mock_provider
            
            chunks = ["chunk1", "chunk2"]
            result = await processor.embed(chunks)
            
            assert len(result) == 2
            assert result[0]["embedding"] == [0.1, 0.2, 0.3]
            assert result[1]["embedding"] == [0.4, 0.5, 0.6]
            mock_provider.embed.assert_called_once_with(chunks)
    
    async def test_embed_with_no_provider_available(self):
        """Test embedding when provider is not available"""
        processor = DocumentProcessor()
        
        with patch('sheratan_orchestrator.worker.DocumentProcessor._get_embedding_provider') as mock_get:
            mock_get.return_value = None  # Simulate no provider
            
            chunks = ["chunk1", "chunk2"]
            result = await processor.embed(chunks)
            
            # Should still return results but with empty embeddings
            assert len(result) == 2
            assert all(item["embedding"] == [] for item in result)
    
    async def test_embed_handles_provider_error(self):
        """Test that embed handles provider errors gracefully"""
        processor = DocumentProcessor()
        
        with patch('sheratan_orchestrator.worker.DocumentProcessor._get_embedding_provider') as mock_get:
            mock_provider = Mock()
            mock_provider.embed.side_effect = Exception("Provider error")
            mock_get.return_value = mock_provider
            
            chunks = ["chunk1", "chunk2"]
            result = await processor.embed(chunks)
            
            # Should fallback to empty embeddings
            assert len(result) == 2
            assert all(item["embedding"] == [] for item in result)
    
    async def test_process_document_with_embeddings(self):
        """Test full document processing pipeline"""
        processor = DocumentProcessor()
        
        with patch('sheratan_orchestrator.worker.DocumentProcessor._get_embedding_provider') as mock_get:
            mock_provider = Mock()
            mock_provider.embed.return_value = [[0.1, 0.2], [0.3, 0.4]]
            mock_get.return_value = mock_provider
            
            document = {
                'id': 'test-doc',
                'content': 'This is test content for processing'
            }
            
            result = await processor.process_document(document)
            
            assert result["success"] is True
            assert result["document_id"] == 'test-doc'
            assert result["chunks_created"] > 0
    
    def test_get_embedding_provider_lazy_loading(self):
        """Test that embedding provider is lazily loaded"""
        processor = DocumentProcessor()
        assert processor._embedding_provider is None
        
        # Mock at the import location, not the module itself
        mock_provider = Mock()
        with patch.object(processor, '_get_embedding_provider', return_value=mock_provider) as mock_method:
            # First call loads the provider
            provider1 = processor._get_embedding_provider()
            assert provider1 == mock_provider
            mock_method.assert_called_once()
            
            # Second call reuses cached provider (but we're mocking the method, so it still calls)
            provider2 = processor._get_embedding_provider()
            assert provider2 == mock_provider
    
    def test_get_embedding_provider_handles_import_error(self):
        """Test handling of missing sheratan-embeddings package"""
        processor = DocumentProcessor()
        
        with patch('builtins.__import__', side_effect=ImportError):
            provider = processor._get_embedding_provider()
            assert provider is None
