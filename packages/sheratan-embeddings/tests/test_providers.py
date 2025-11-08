"""Tests for embedding providers"""
import pytest
import os
from unittest.mock import Mock, patch, MagicMock
from sheratan_embeddings.providers import (
    EmbeddingProvider,
    LocalEmbeddingProvider,
    OpenAIEmbeddingProvider,
    HuggingFaceEmbeddingProvider,
    OffEmbeddingProvider,
    get_embedding_provider
)


class TestOffEmbeddingProvider:
    """Tests for OffEmbeddingProvider"""
    
    def test_init(self):
        """Test initialization"""
        provider = OffEmbeddingProvider()
        assert provider is not None
    
    def test_embed_returns_empty_lists(self):
        """Test that embed returns empty embeddings"""
        provider = OffEmbeddingProvider()
        texts = ["text1", "text2", "text3"]
        embeddings = provider.embed(texts)
        
        assert len(embeddings) == 3
        assert all(emb == [] for emb in embeddings)
    
    def test_embed_query_returns_empty_list(self):
        """Test that embed_query returns empty embedding"""
        provider = OffEmbeddingProvider()
        embedding = provider.embed_query("test query")
        
        assert embedding == []


class TestLocalEmbeddingProvider:
    """Tests for LocalEmbeddingProvider"""
    
    def test_init(self):
        """Test initialization without loading model"""
        provider = LocalEmbeddingProvider(model_name="all-MiniLM-L6-v2")
        assert provider.model_name == "all-MiniLM-L6-v2"
        assert provider.model is None  # Lazy loading
    
    def test_embed_loads_model_and_encodes(self):
        """Test that embed loads model and generates embeddings"""
        # Setup mock - patch at the point of import, not globally
        mock_model = Mock()
        mock_model.encode.return_value = MagicMock()
        mock_model.encode.return_value.tolist.return_value = [[0.1, 0.2], [0.3, 0.4]]
        
        provider = LocalEmbeddingProvider(model_name="test-model")
        
        # Mock the import within _load_model
        with patch('sheratan_embeddings.providers.LocalEmbeddingProvider._load_model') as mock_load:
            provider.model = mock_model  # Set the model directly
            texts = ["text1", "text2"]
            embeddings = provider.embed(texts)
            
            # Verify encode was called
            mock_model.encode.assert_called_once_with(texts, convert_to_tensor=False)
            
            # Verify embeddings
            assert embeddings == [[0.1, 0.2], [0.3, 0.4]]
    
    def test_embed_query(self):
        """Test embed_query for single text"""
        mock_model = Mock()
        mock_model.encode.return_value = MagicMock()
        mock_model.encode.return_value.tolist.return_value = [0.1, 0.2, 0.3]
        
        provider = LocalEmbeddingProvider()
        provider.model = mock_model  # Set the model directly
        
        embedding = provider.embed_query("test query")
        
        mock_model.encode.assert_called_once_with("test query", convert_to_tensor=False)
        assert embedding == [0.1, 0.2, 0.3]
    
    def test_embed_raises_on_missing_import(self):
        """Test that missing sentence-transformers raises ImportError"""
        provider = LocalEmbeddingProvider()
        
        # Mock the import to fail
        import sys
        with patch.dict(sys.modules, {'sentence_transformers': None}):
            with pytest.raises((ImportError, AttributeError)):
                provider.embed(["test"])


class TestOpenAIEmbeddingProvider:
    """Tests for OpenAIEmbeddingProvider"""
    
    def test_init_with_api_key(self):
        """Test initialization with API key"""
        provider = OpenAIEmbeddingProvider(api_key="test-key")
        assert provider.api_key == "test-key"
        assert provider.model == "text-embedding-ada-002"
    
    def test_init_from_env(self):
        """Test initialization from environment variable"""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "env-key"}):
            provider = OpenAIEmbeddingProvider()
            assert provider.api_key == "env-key"
    
    def test_init_without_api_key_raises(self):
        """Test that missing API key raises ValueError"""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="OpenAI API key not provided"):
                OpenAIEmbeddingProvider()
    
    def test_embed(self):
        """Test embed with mocked OpenAI API"""
        mock_openai = MagicMock()
        mock_openai.Embedding.create.return_value = {
            'data': [
                {'embedding': [0.1, 0.2]},
                {'embedding': [0.3, 0.4]}
            ]
        }
        
        with patch.dict('sys.modules', {'openai': mock_openai}):
            provider = OpenAIEmbeddingProvider(api_key="test-key", model="test-model")
            embeddings = provider.embed(["text1", "text2"])
            
            mock_openai.Embedding.create.assert_called_once_with(
                model="test-model",
                input=["text1", "text2"]
            )
            assert embeddings == [[0.1, 0.2], [0.3, 0.4]]
    
    def test_embed_query(self):
        """Test embed_query"""
        mock_openai = MagicMock()
        mock_openai.Embedding.create.return_value = {
            'data': [{'embedding': [0.1, 0.2, 0.3]}]
        }
        
        with patch.dict('sys.modules', {'openai': mock_openai}):
            provider = OpenAIEmbeddingProvider(api_key="test-key")
            embedding = provider.embed_query("test query")
            
            assert embedding == [0.1, 0.2, 0.3]


class TestHuggingFaceEmbeddingProvider:
    """Tests for HuggingFaceEmbeddingProvider"""
    
    @patch('sheratan_embeddings.providers.LocalEmbeddingProvider')
    def test_init(self, mock_local):
        """Test initialization delegates to LocalEmbeddingProvider"""
        provider = HuggingFaceEmbeddingProvider(model_name="test-model")
        
        mock_local.assert_called_once_with("test-model")
        assert provider.model_name == "test-model"
    
    @patch('sheratan_embeddings.providers.LocalEmbeddingProvider')
    def test_embed_delegates_to_local(self, mock_local):
        """Test that embed delegates to LocalEmbeddingProvider"""
        mock_instance = Mock()
        mock_instance.embed.return_value = [[0.1, 0.2]]
        mock_local.return_value = mock_instance
        
        provider = HuggingFaceEmbeddingProvider()
        embeddings = provider.embed(["text1"])
        
        mock_instance.embed.assert_called_once_with(["text1"])
        assert embeddings == [[0.1, 0.2]]


class TestGetEmbeddingProvider:
    """Tests for get_embedding_provider factory function"""
    
    def test_default_provider_is_off(self):
        """Test that default provider is 'off'"""
        with patch.dict(os.environ, {}, clear=True):
            provider = get_embedding_provider()
            assert isinstance(provider, OffEmbeddingProvider)
    
    def test_off_provider_from_env(self):
        """Test 'off' provider from environment"""
        with patch.dict(os.environ, {"EMBEDDINGS_PROVIDER": "off"}):
            provider = get_embedding_provider()
            assert isinstance(provider, OffEmbeddingProvider)
    
    def test_local_provider_from_env(self):
        """Test 'local' provider from environment"""
        with patch.dict(os.environ, {"EMBEDDINGS_PROVIDER": "local"}):
            provider = get_embedding_provider()
            assert isinstance(provider, LocalEmbeddingProvider)
    
    def test_local_provider_with_custom_model(self):
        """Test local provider with custom model"""
        with patch.dict(os.environ, {
            "EMBEDDINGS_PROVIDER": "local",
            "EMBEDDINGS_MODEL": "custom-model"
        }):
            provider = get_embedding_provider()
            assert isinstance(provider, LocalEmbeddingProvider)
            assert provider.model_name == "custom-model"
    
    def test_openai_provider_from_env(self):
        """Test OpenAI provider from environment"""
        with patch.dict(os.environ, {
            "EMBEDDINGS_PROVIDER": "openai",
            "OPENAI_API_KEY": "test-key"
        }):
            provider = get_embedding_provider()
            assert isinstance(provider, OpenAIEmbeddingProvider)
    
    def test_huggingface_provider_from_env(self):
        """Test HuggingFace provider from environment"""
        with patch.dict(os.environ, {"EMBEDDINGS_PROVIDER": "huggingface"}):
            provider = get_embedding_provider()
            assert isinstance(provider, HuggingFaceEmbeddingProvider)
    
    def test_provider_parameter_overrides_env(self):
        """Test that provider parameter overrides environment"""
        with patch.dict(os.environ, {"EMBEDDINGS_PROVIDER": "local"}):
            provider = get_embedding_provider(provider="off")
            assert isinstance(provider, OffEmbeddingProvider)
    
    def test_model_parameter_overrides_env(self):
        """Test that model parameter overrides environment"""
        with patch.dict(os.environ, {
            "EMBEDDINGS_PROVIDER": "local",
            "EMBEDDINGS_MODEL": "env-model"
        }):
            provider = get_embedding_provider(model="param-model")
            assert provider.model_name == "param-model"
    
    def test_unknown_provider_raises(self):
        """Test that unknown provider raises ValueError"""
        with pytest.raises(ValueError, match="Unknown embedding provider: invalid"):
            get_embedding_provider(provider="invalid")
