"""Sheratan Embeddings - Local CPU embeddings with provider switch"""
__version__ = "0.1.0"
"""
Sheratan Embeddings provider package.
Provides ENV-switchable providers: local (sentence-transformers), openai, huggingface, off.
"""

__version__ = "0.1.0"

from .providers import (  # noqa: F401
    EmbeddingProvider,
    LocalEmbeddingProvider,
    OpenAIEmbeddingProvider,
    HuggingFaceEmbeddingProvider,
    OffEmbeddingProvider,
    get_embedding_provider,
)

__all__ = [
    "EmbeddingProvider",
    "LocalEmbeddingProvider",
    "OpenAIEmbeddingProvider",
    "HuggingFaceEmbeddingProvider",
    "OffEmbeddingProvider",
    "get_embedding_provider",
]