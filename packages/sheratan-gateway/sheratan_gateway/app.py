"""FastAPI Application for Sheratan Gateway"""
import os
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Environment variables
LLM_ENABLED = os.getenv("LLM_ENABLED", "false").lower() == "true"
EMBEDDINGS_PROVIDER = os.getenv("EMBEDDINGS_PROVIDER", "off")

# Lazy-loaded embedding provider
_embedding_provider = None


def get_embedding_provider():
    """Get embedding provider (lazy-loaded)"""
    global _embedding_provider
    if _embedding_provider is None:
        try:
            from sheratan_embeddings.providers import get_embedding_provider as _get_provider
            _embedding_provider = _get_provider()
            logger.info(f"Embedding provider initialized: {EMBEDDINGS_PROVIDER}")
        except ImportError:
            logger.warning("sheratan-embeddings not available")
            _embedding_provider = None
    return _embedding_provider

app = FastAPI(
    title="Sheratan Gateway",
    version="0.1.0",
    description="REST API for document ingestion, search, and RAG-based answers"
)


# Models
class Document(BaseModel):
    """Document to be ingested"""
    id: Optional[str] = None
    content: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    source: Optional[str] = None


class IngestRequest(BaseModel):
    """Request for document ingestion"""
    documents: List[Document]


class IngestResponse(BaseModel):
    """Response for document ingestion"""
    success: bool
    document_ids: List[str]
    message: str


class SearchRequest(BaseModel):
    """Request for semantic search"""
    query: str
    top_k: int = Field(default=5, ge=1, le=100)
    filters: Optional[Dict[str, Any]] = None


class SearchResult(BaseModel):
    """Single search result"""
    document_id: str
    content: str
    score: float
    metadata: Dict[str, Any] = Field(default_factory=dict)


class SearchResponse(BaseModel):
    """Response for search"""
    query: str
    results: List[SearchResult]
    total: int


class AnswerRequest(BaseModel):
    """Request for RAG-based answer"""
    question: str
    top_k: int = Field(default=5, ge=1, le=100)
    context_filters: Optional[Dict[str, Any]] = None


class AnswerResponse(BaseModel):
    """Response for RAG-based answer"""
    question: str
    answer: str
    sources: List[SearchResult]
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)


# Endpoints
@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "Sheratan Gateway",
        "version": "0.1.0",
        "status": "running"
    }


@app.get("/health")
async def health():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "llm_enabled": LLM_ENABLED,
        "embeddings_provider": EMBEDDINGS_PROVIDER
    }


@app.post("/ingest", response_model=IngestResponse, status_code=status.HTTP_201_CREATED)
async def ingest_documents(request: IngestRequest):
    """
    Ingest documents for indexing
    
    Documents will be processed by the orchestrator:
    - Chunking
    - Embedding generation
    - Storage in vector database
    """
    # TODO: Send to orchestrator queue
    # For now, return mock response
    document_ids = [f"doc_{i}" for i in range(len(request.documents))]
    
    return IngestResponse(
        success=True,
        document_ids=document_ids,
        message=f"Successfully queued {len(request.documents)} documents for ingestion"
    )


@app.post("/search", response_model=SearchResponse)
async def search_documents(request: SearchRequest):
    """
    Perform semantic search across indexed documents
    
    Uses embeddings to find most relevant documents
    """
    # Get embedding provider
    provider = get_embedding_provider()
    embeddings_provider = os.getenv("EMBEDDINGS_PROVIDER", "off")
    
    if provider is None or embeddings_provider == "off":
        logger.warning("Embeddings not available or disabled")
        return SearchResponse(
            query=request.query,
            results=[],
            total=0
        )
    
    try:
        # Generate query embedding
        query_embedding = provider.embed_query(request.query)
        logger.info(f"Generated query embedding with {len(query_embedding)} dimensions")
        
        # TODO: Query vector store via sheratan-store using query_embedding
        # For now, return mock response
        
        return SearchResponse(
            query=request.query,
            results=[],
            total=0
        )
    except Exception as e:
        logger.error(f"Error during search: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Search failed: {str(e)}"
        )


@app.post("/answer", response_model=AnswerResponse)
async def answer_question(request: AnswerRequest):
    """
    Generate RAG-based answer to a question
    
    Requires LLM to be enabled (LLM_ENABLED=true)
    """
    if not LLM_ENABLED:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="LLM is not enabled. Set LLM_ENABLED=true to use this endpoint."
        )
    
    # TODO: 
    # 1. Search for relevant context
    # 2. Call LLM with context
    # 3. Return answer with sources
    
    return AnswerResponse(
        question=request.question,
        answer="LLM integration pending",
        sources=[],
        confidence=0.0
    )


if __name__ == "__main__":
    import uvicorn
    host = os.getenv("GATEWAY_HOST", "0.0.0.0")
    port = int(os.getenv("GATEWAY_PORT", "8000"))
    uvicorn.run(app, host=host, port=port)
