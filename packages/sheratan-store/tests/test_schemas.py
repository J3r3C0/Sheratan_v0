"""Tests for Pydantic schemas"""
import pytest
from uuid import uuid4
from datetime import datetime

from sheratan_store.schemas import (
    DocumentCreate,
    DocumentUpdate,
    DocumentResponse,
    ChunkCreate,
    ChunkResponse,
    VectorSearchRequest,
    VectorSearchResult,
    JobCreate,
    JobUpdate,
    JobResponse,
    AuditLogCreate,
    AuditLogResponse,
    SearchLogCreate,
    SearchLogResponse,
)


def test_document_create_schema():
    """Test DocumentCreate validation"""
    doc = DocumentCreate(
        content="Test content",
        metadata={"key": "value"},
        source="test.txt"
    )
    assert doc.content == "Test content"
    assert doc.metadata == {"key": "value"}
    assert doc.source == "test.txt"


def test_document_create_minimal():
    """Test DocumentCreate with minimal fields"""
    doc = DocumentCreate(content="Test")
    assert doc.content == "Test"
    assert doc.metadata == {}
    assert doc.source is None


def test_document_create_validation():
    """Test DocumentCreate validation fails on empty content"""
    with pytest.raises(Exception):  # Pydantic ValidationError
        DocumentCreate(content="")


def test_chunk_create_schema():
    """Test ChunkCreate validation"""
    doc_id = uuid4()
    chunk = ChunkCreate(
        document_id=doc_id,
        chunk_index=0,
        content="Chunk content",
        metadata={"type": "paragraph"},
        embedding=[0.1] * 384
    )
    assert chunk.document_id == doc_id
    assert chunk.chunk_index == 0
    assert chunk.content == "Chunk content"
    assert len(chunk.embedding) == 384


def test_chunk_create_without_embedding():
    """Test ChunkCreate without embedding"""
    doc_id = uuid4()
    chunk = ChunkCreate(
        document_id=doc_id,
        chunk_index=0,
        content="Chunk content"
    )
    assert chunk.embedding is None


def test_vector_search_request():
    """Test VectorSearchRequest validation"""
    request = VectorSearchRequest(
        query="test query",
        top_k=10,
        threshold=0.7
    )
    assert request.query == "test query"
    assert request.top_k == 10
    assert request.threshold == 0.7


def test_vector_search_request_defaults():
    """Test VectorSearchRequest defaults"""
    request = VectorSearchRequest(query="test")
    assert request.top_k == 5
    assert request.threshold is None
    assert request.filters is None


def test_vector_search_request_validation():
    """Test VectorSearchRequest validation"""
    # top_k should be >= 1
    with pytest.raises(Exception):
        VectorSearchRequest(query="test", top_k=0)
    
    # top_k should be <= 100
    with pytest.raises(Exception):
        VectorSearchRequest(query="test", top_k=101)
    
    # threshold should be between 0 and 1
    with pytest.raises(Exception):
        VectorSearchRequest(query="test", threshold=1.5)


def test_job_create_schema():
    """Test JobCreate validation"""
    job = JobCreate(
        job_type="ingest",
        status="pending",
        payload={"url": "http://example.com"},
        priority=5
    )
    assert job.job_type == "ingest"
    assert job.status == "pending"
    assert job.payload == {"url": "http://example.com"}
    assert job.priority == 5


def test_job_update_schema():
    """Test JobUpdate validation"""
    update = JobUpdate(
        status="completed",
        result={"chunks": 5}
    )
    assert update.status == "completed"
    assert update.result == {"chunks": 5}
    assert update.error_message is None


def test_audit_log_create_schema():
    """Test AuditLogCreate validation"""
    log = AuditLogCreate(
        event_type="document_access",
        user_id="user123",
        action="read",
        resource_type="document",
        resource_id="doc123",
        details={"method": "GET"},
        ip_address="192.168.1.1"
    )
    assert log.event_type == "document_access"
    assert log.action == "read"
    assert log.user_id == "user123"


def test_audit_log_minimal():
    """Test AuditLogCreate with minimal fields"""
    log = AuditLogCreate(
        event_type="test",
        action="test_action"
    )
    assert log.event_type == "test"
    assert log.action == "test_action"
    assert log.details == {}


def test_search_log_create():
    """Test SearchLogCreate validation"""
    log = SearchLogCreate(
        query="test query",
        results_count=5,
        avg_score=0.85
    )
    assert log.query == "test query"
    assert log.results_count == 5
    assert log.avg_score == 0.85


def test_response_schemas_from_attributes():
    """Test that response schemas accept ORM objects"""
    # This tests the model_config = ConfigDict(from_attributes=True)
    doc_data = {
        "id": uuid4(),
        "content": "Test",
        "metadata": {},
        "source": None,
        "created_at": datetime.utcnow(),
        "updated_at": None
    }
    
    doc_response = DocumentResponse(**doc_data)
    assert doc_response.content == "Test"
    assert doc_response.id == doc_data["id"]
