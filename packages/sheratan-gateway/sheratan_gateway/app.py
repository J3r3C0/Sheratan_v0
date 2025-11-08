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
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, status, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta, timezone
from sqlalchemy.ext.asyncio import AsyncSession

from .auth import (
    get_current_active_user, 
    User, 
    create_access_token,
    JWT_SECRET_KEY,
    API_KEYS
)
from .db import get_db, init_db, close_db

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
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://sheratan:sheratan@localhost:5432/sheratan")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    # Startup
    try:
        await init_db()
        print("Database initialized successfully")
    except Exception as e:
        print(f"Warning: Database initialization failed: {e}")
    
    yield
    
    # Shutdown
    await close_db()

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
    description="REST API for document ingestion, search, and RAG-based answers",
    lifespan=lifespan
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


class TokenRequest(BaseModel):
    """Request for authentication token"""
    username: str
    password: str = Field(default="")  # Simplified for now


class TokenResponse(BaseModel):
    """Response with access token"""
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class AdminInfo(BaseModel):
    """Admin endpoint information"""
    service: str
    version: str
    status: str
    database_url: str
    embeddings_provider: str
    llm_enabled: bool
    auth_configured: bool
    api_keys_count: int
    timestamp: str


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
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "llm_enabled": LLM_ENABLED,
        "embeddings_provider": EMBEDDINGS_PROVIDER
    }


@app.post("/auth/token", response_model=TokenResponse)
async def login(request: TokenRequest):
    """
    Get JWT access token
    
    Simple authentication endpoint that generates a JWT token.
    In production, validate credentials against a user database.
    
    Args:
        request: Username and password
    
    Returns:
        JWT access token
    """
    # TODO: Validate credentials against database
    # For now, accept any username
    if not request.username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username is required"
        )
    
    access_token_expires = timedelta(minutes=30)
    access_token = create_access_token(
        data={"sub": request.username},
        expires_delta=access_token_expires
    )
    
    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=30 * 60  # 30 minutes in seconds
    )


@app.get("/admin", response_model=AdminInfo)
async def admin_info(
    current_user: User = Depends(get_current_active_user)
):
    """
    Admin endpoint with system information
    
    Provides system status, configuration, and health information.
    Requires authentication.
    
    Returns:
        System information and status
    """
    # Mask sensitive parts of DATABASE_URL
    db_url_masked = DATABASE_URL
    if "@" in db_url_masked:
        # Hide password in DATABASE_URL
        parts = db_url_masked.split("@")
        credentials_part = parts[0]
        if ":" in credentials_part:
            user_pass = credentials_part.split("://")[1]
            user = user_pass.split(":")[0]
            db_url_masked = f"postgresql://{user}:***@{parts[1]}"
    
    auth_configured = bool(API_KEYS) or JWT_SECRET_KEY != "dev-secret-key-change-in-production"
    
    return AdminInfo(
        service="Sheratan Gateway",
        version="0.1.0",
        status="running",
        database_url=db_url_masked,
        embeddings_provider=EMBEDDINGS_PROVIDER,
        llm_enabled=LLM_ENABLED,
        auth_configured=auth_configured,
        api_keys_count=len(API_KEYS) if API_KEYS else 0,
        timestamp=datetime.now(timezone.utc).isoformat()
    )


@app.post("/ingest", response_model=IngestResponse, status_code=status.HTTP_201_CREATED)
async def ingest_documents(request: IngestRequest, http_request: Request):
async def ingest_documents(
    request: IngestRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Ingest documents for indexing
    
    Documents will be processed by the orchestrator:
    - Chunking
    - Embedding generation
    - Storage in vector database
    
    Requires authentication.
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
async def search_documents(
    request: SearchRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Perform semantic search across indexed documents
    
    Uses embeddings to find most relevant documents
    
    Requires authentication.
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
async def answer_question(
    request: AnswerRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Generate RAG-based answer to a question
    
    Requires LLM to be enabled (LLM_ENABLED=true)
    Requires authentication.
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
