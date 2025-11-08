"""FastAPI Application for Sheratan Gateway"""
import os
from fastapi import FastAPI, HTTPException, status, Request
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Environment variables
LLM_ENABLED = os.getenv("LLM_ENABLED", "false").lower() == "true"
EMBEDDINGS_PROVIDER = os.getenv("EMBEDDINGS_PROVIDER", "local")
GUARD_ENABLED = os.getenv("GUARD_ENABLED", "true").lower() == "true"

# Initialize Guard (import conditionally to avoid errors if not installed)
guard_middleware = None
audit_logger = None
rate_limit_middleware = None

if GUARD_ENABLED:
    try:
        import sys
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../sheratan-guard"))
        from sheratan_guard import GuardMiddleware, AuditEventType
        
        guard_middleware = GuardMiddleware(enabled=True)
        audit_logger = guard_middleware.audit_logger
        rate_limit_middleware = guard_middleware.create_rate_limit_middleware()
        
        logger.info("Guard middleware enabled")
    except Exception as e:
        logger.warning(f"Failed to initialize guard middleware: {e}")
        GUARD_ENABLED = False

app = FastAPI(
    title="Sheratan Gateway",
    version="0.1.0",
    description="REST API for document ingestion, search, and RAG-based answers"
)

# Add rate limiting middleware if enabled
if rate_limit_middleware:
    app.middleware("http")(rate_limit_middleware)


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
async def ingest_documents(request: IngestRequest, http_request: Request):
    """
    Ingest documents for indexing
    
    Documents will be processed by the orchestrator:
    - Chunking
    - Embedding generation
    - Storage in vector database
    """
    document_ids = []
    
    # Apply guard checks to each document
    if guard_middleware:
        for doc in request.documents:
            # Check document content
            check_result = await guard_middleware.check_request(
                http_request,
                content=doc.content,
                endpoint="/ingest"
            )
            
            if not check_result["allowed"]:
                error_msg = "Document rejected: "
                if check_result["policy_violations"]:
                    error_msg += f"Policy violations: {', '.join(check_result['policy_violations'])}. "
                if check_result["blocked_terms"]:
                    error_msg += f"Blocked terms detected: {', '.join(check_result['blocked_terms'])}. "
                
                # Log the rejection
                if audit_logger:
                    audit_logger.log(
                        event_type=AuditEventType.ACCESS_DENIED,
                        user_id=guard_middleware._get_client_id(http_request),
                        action="ingest",
                        result="denied",
                        metadata={"reason": error_msg}
                    )
                
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=error_msg
                )
            
            # Scrub PII from content before processing
            if check_result["pii_detected"]:
                logger.warning(f"PII detected in document, scrubbing: {check_result['pii_types']}")
                doc.content = guard_middleware.scrub_pii(doc.content)
    
    # TODO: Send to orchestrator queue
    # For now, return mock response
    document_ids = [f"doc_{i}" for i in range(len(request.documents))]
    
    # Log successful ingestion
    if audit_logger:
        for doc_id in document_ids:
            audit_logger.log_document_ingest(
                document_id=doc_id,
                user_id=guard_middleware._get_client_id(http_request) if guard_middleware else None,
                success=True,
                metadata={"document_count": len(request.documents)}
            )
    
    return IngestResponse(
        success=True,
        document_ids=document_ids,
        message=f"Successfully queued {len(request.documents)} documents for ingestion"
    )


@app.post("/search", response_model=SearchResponse)
async def search_documents(request: SearchRequest, http_request: Request):
    """
    Perform semantic search across indexed documents
    
    Uses embeddings to find most relevant documents
    """
    # Apply guard checks
    if guard_middleware:
        check_result = await guard_middleware.check_request(
            http_request,
            content=request.query,
            endpoint="/search"
        )
        
        if not check_result["allowed"]:
            error_msg = "Search rejected: "
            if check_result["policy_violations"]:
                error_msg += f"Policy violations: {', '.join(check_result['policy_violations'])}. "
            if check_result["blocked_terms"]:
                error_msg += f"Blocked terms detected. "
            
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=error_msg
            )
    
    # TODO: Query vector store via sheratan-store
    # For now, return mock response
    results = []
    
    # Log search
    if audit_logger:
        audit_logger.log_search(
            query=request.query,
            user_id=guard_middleware._get_client_id(http_request) if guard_middleware else None,
            results_count=len(results),
            metadata={"top_k": request.top_k}
        )
    
    return SearchResponse(
        query=request.query,
        results=results,
        total=len(results)
    )


@app.post("/answer", response_model=AnswerResponse)
async def answer_question(request: AnswerRequest, http_request: Request):
    """
    Generate RAG-based answer to a question
    
    Requires LLM to be enabled (LLM_ENABLED=true)
    """
    if not LLM_ENABLED:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="LLM is not enabled. Set LLM_ENABLED=true to use this endpoint."
        )
    
    # Apply guard checks
    if guard_middleware:
        check_result = await guard_middleware.check_request(
            http_request,
            content=request.question,
            endpoint="/answer"
        )
        
        if not check_result["allowed"]:
            error_msg = "Question rejected: "
            if check_result["policy_violations"]:
                error_msg += f"Policy violations: {', '.join(check_result['policy_violations'])}. "
            if check_result["blocked_terms"]:
                error_msg += f"Blocked terms detected. "
            
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=error_msg
            )
    
    # TODO: 
    # 1. Search for relevant context
    # 2. Call LLM with context
    # 3. Return answer with sources
    
    answer = "LLM integration pending"
    sources = []
    
    # Log answer request
    if audit_logger:
        audit_logger.log(
            event_type=AuditEventType.ANSWER_REQUEST,
            user_id=guard_middleware._get_client_id(http_request) if guard_middleware else None,
            action="answer",
            result="success",
            metadata={"question": request.question, "sources_count": len(sources)}
        )
    
    return AnswerResponse(
        question=request.question,
        answer=answer,
        sources=sources,
        confidence=0.0
    )


if __name__ == "__main__":
    import uvicorn
    host = os.getenv("GATEWAY_HOST", "0.0.0.0")
    port = int(os.getenv("GATEWAY_PORT", "8000"))
    uvicorn.run(app, host=host, port=port)
