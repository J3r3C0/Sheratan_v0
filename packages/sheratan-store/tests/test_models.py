"""Tests for database models"""
import pytest
from datetime import datetime
from uuid import uuid4

from sheratan_store.models import Document, DocumentChunk, Job, AuditLog, SearchLog


def test_document_model():
    """Test Document model creation"""
    doc_id = uuid4()
    doc = Document(
        id=doc_id,
        content="Test document content",
        metadata_={"key": "value"},
        source="test.txt"
    )
    
    assert doc.id == doc_id
    assert doc.content == "Test document content"
    assert doc.metadata_ == {"key": "value"}
    assert doc.source == "test.txt"


def test_document_chunk_model():
    """Test DocumentChunk model creation"""
    doc_id = uuid4()
    chunk_id = uuid4()
    embedding = [0.1] * 384  # 384-dimensional vector
    
    chunk = DocumentChunk(
        id=chunk_id,
        document_id=doc_id,
        chunk_index=0,
        content="Test chunk content",
        embedding=embedding,
        metadata_={"chunk_type": "paragraph"}
    )
    
    assert chunk.id == chunk_id
    assert chunk.document_id == doc_id
    assert chunk.chunk_index == 0
    assert chunk.content == "Test chunk content"
    assert chunk.embedding == embedding
    assert chunk.metadata_ == {"chunk_type": "paragraph"}


def test_job_model():
    """Test Job model creation"""
    job_id = uuid4()
    job = Job(
        id=job_id,
        job_type="ingest",
        status="pending",
        payload={"url": "http://example.com"},
        priority=5
    )
    
    assert job.id == job_id
    assert job.job_type == "ingest"
    assert job.status == "pending"
    assert job.payload == {"url": "http://example.com"}
    assert job.priority == 5
    assert job.result is None
    assert job.error_message is None


def test_audit_log_model():
    """Test AuditLog model creation"""
    log_id = uuid4()
    log = AuditLog(
        id=log_id,
        event_type="document_access",
        user_id="user123",
        action="read",
        resource_type="document",
        resource_id="doc123",
        details={"method": "GET"},
        ip_address="192.168.1.1",
        user_agent="Mozilla/5.0"
    )
    
    assert log.id == log_id
    assert log.event_type == "document_access"
    assert log.user_id == "user123"
    assert log.action == "read"
    assert log.resource_type == "document"
    assert log.resource_id == "doc123"
    assert log.details == {"method": "GET"}
    assert log.ip_address == "192.168.1.1"
    assert log.user_agent == "Mozilla/5.0"


def test_search_log_model():
    """Test SearchLog model creation"""
    log_id = uuid4()
    log = SearchLog(
        id=log_id,
        query="test query",
        results_count=5,
        avg_score=0.85,
        metadata_={"filters": {"type": "document"}}
    )
    
    assert log.id == log_id
    assert log.query == "test query"
    assert log.results_count == 5
    assert log.avg_score == 0.85
    assert log.metadata_ == {"filters": {"type": "document"}}


def test_model_defaults():
    """Test that models can be created with minimal fields"""
    doc = Document(content="Test")
    assert doc.content == "Test"
    assert doc.source is None
    
    chunk = DocumentChunk(
        document_id=uuid4(),
        chunk_index=0,
        content="Test"
    )
    assert chunk.content == "Test"
    # JSON defaults are set in database, not in Python
    
    job = Job(
        job_type="test",
        status="pending",
        payload={}
    )
    assert job.job_type == "test"
    assert job.result is None
    # priority default is set in database
    
    log = AuditLog(
        event_type="test",
        action="test"
    )
    assert log.event_type == "test"
    # details default is set in database
