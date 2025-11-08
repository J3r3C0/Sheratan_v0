"""Embedding providers with ENV-based switching"""
import os
from abc import ABC, abstractmethod
from typing import List, Optional
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class EmbeddingProvider(ABC):
    """Base class for embedding providers"""
    
    @abstractmethod
    def embed(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for texts"""
        pass
    
    @abstractmethod
    def embed_query(self, query: str) -> List[float]:
        """Generate embedding for a single query"""
        pass


class LocalEmbeddingProvider(EmbeddingProvider):
    """Local CPU-based embeddings using sentence-transformers"""
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.model_name = model_name
        self.model = None
        logger.info(f"Initializing local embeddings with model: {model_name}")
        
    def _load_model(self):
        """Lazy load the model"""
        if self.model is None:
            try:
                from sentence_transformers import SentenceTransformer
                self.model = SentenceTransformer(self.model_name)
                logger.info("Model loaded successfully")
            except ImportError:
                logger.error("sentence-transformers not installed. Install with: pip install sentence-transformers")
                raise
    
    def embed(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts"""
        self._load_model()
        embeddings = self.model.encode(texts, convert_to_tensor=False)
        return embeddings.tolist()
    
    def embed_query(self, query: str) -> List[float]:
        """Generate embedding for a single query"""
        self._load_model()
        embedding = self.model.encode(query, convert_to_tensor=False)
        return embedding.tolist()


class OpenAIEmbeddingProvider(EmbeddingProvider):
    """OpenAI embeddings provider"""
    
    def __init__(self, api_key: Optional[str] = None, model: str = "text-embedding-ada-002"):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.model = model
        
        if not self.api_key:
            raise ValueError("OpenAI API key not provided")
        
        logger.info(f"Initializing OpenAI embeddings with model: {model}")
    
    def embed(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings using OpenAI API"""
        try:
            import openai
            openai.api_key = self.api_key
            
            response = openai.Embedding.create(
                model=self.model,
                input=texts
            )
            
            return [item['embedding'] for item in response['data']]
        except ImportError:
            logger.error("openai package not installed. Install with: pip install openai")
            raise
    
    def embed_query(self, query: str) -> List[float]:
        """Generate embedding for a single query"""
        return self.embed([query])[0]


class HuggingFaceEmbeddingProvider(EmbeddingProvider):
    """HuggingFace embeddings provider"""
    
    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
        self.model_name = model_name
        logger.info(f"Initializing HuggingFace embeddings with model: {model_name}")
        # Similar to LocalEmbeddingProvider but with HF Hub support
        self.provider = LocalEmbeddingProvider(model_name)
    
    def embed(self, texts: List[str]) -> List[List[float]]:
        return self.provider.embed(texts)
    
    def embed_query(self, query: str) -> List[float]:
        return self.provider.embed_query(query)


class OffEmbeddingProvider(EmbeddingProvider):
    """Disabled embeddings provider - returns empty embeddings"""
    
    def __init__(self):
        logger.warning("Embeddings are disabled (provider='off')")
    
    def embed(self, texts: List[str]) -> List[List[float]]:
        """Returns empty embeddings for all texts"""
        logger.warning("Embeddings disabled - returning empty vectors")
        return [[] for _ in texts]
    
    def embed_query(self, query: str) -> List[float]:
        """Returns empty embedding for query"""
        logger.warning("Embeddings disabled - returning empty vector")
        return []


def get_embedding_provider(
    provider: Optional[str] = None,
    model: Optional[str] = None
) -> EmbeddingProvider:
    """
    Factory function to get embedding provider based on ENV or parameters
    
    Args:
        provider: Provider name ('local', 'openai', 'huggingface', 'off'). 
                  Defaults to EMBEDDINGS_PROVIDER env var or 'off'
        model: Model name. Defaults to EMBEDDINGS_MODEL env var or provider default
        
    Returns:
        EmbeddingProvider instance
    """
    provider = provider or os.getenv("EMBEDDINGS_PROVIDER", "off")
    model = model or os.getenv("EMBEDDINGS_MODEL")
    
    logger.info(f"Creating embedding provider: {provider}")
    
    if provider == "off":
        return OffEmbeddingProvider()
    
    elif provider == "local":
        model = model or "all-MiniLM-L6-v2"
        return LocalEmbeddingProvider(model_name=model)
    
    elif provider == "openai":
        model = model or "text-embedding-ada-002"
        return OpenAIEmbeddingProvider(model=model)
    
    elif provider == "huggingface":
        model = model or "sentence-transformers/all-MiniLM-L6-v2"
        return HuggingFaceEmbeddingProvider(model_name=model)
    
    else:
        raise ValueError(f"Unknown embedding provider: {provider}")
