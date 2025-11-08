"""Integration tests for repositories - requires database"""
import pytest
import os
from uuid import uuid4
from datetime import datetime

# Skip all tests in this file if no database is available
pytestmark = pytest.mark.skipif(
    os.getenv("DATABASE_URL") is None,
    reason="DATABASE_URL not set - integration tests skipped"
)

pytest_plugins = ('pytest_asyncio',)


@pytest.fixture
async def db_session():
    """Create a test database session"""
    from sheratan_store.database import AsyncSessionLocal, async_engine, Base
    
    # Create tables
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # Create session
    async with AsyncSessionLocal() as session:
        yield session
        await session.rollback()
    
    # Clean up
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.mark.asyncio
async def test_document_repository_create(db_session):
    """Test creating a document"""
    from sheratan_store.repositories import DocumentRepository
    
    repo = DocumentRepository(db_session)
    doc = await repo.create_document(
        content="Test content",
        metadata={"key": "value"},
        source="test.txt"
    )
    
    assert doc.id is not None
    assert doc.content == "Test content"
    assert doc.metadata == {"key": "value"}
    assert doc.source == "test.txt"


@pytest.mark.asyncio
async def test_document_repository_get(db_session):
    """Test getting a document"""
    from sheratan_store.repositories import DocumentRepository
    
    repo = DocumentRepository(db_session)
    doc = await repo.create_document(content="Test")
    await db_session.commit()
    
    retrieved = await repo.get_document(doc.id)
    assert retrieved is not None
    assert retrieved.id == doc.id
    assert retrieved.content == "Test"


@pytest.mark.asyncio
async def test_document_repository_create_chunk(db_session):
    """Test creating a document chunk"""
    from sheratan_store.repositories import DocumentRepository
    
    repo = DocumentRepository(db_session)
    doc = await repo.create_document(content="Test document")
    await db_session.commit()
    
    embedding = [0.1] * 384
    chunk = await repo.create_chunk(
        document_id=doc.id,
        chunk_index=0,
        content="Test chunk",
        embedding=embedding,
        metadata={"type": "paragraph"}
    )
    
    assert chunk.id is not None
    assert chunk.document_id == doc.id
    assert chunk.chunk_index == 0
    assert chunk.content == "Test chunk"


@pytest.mark.asyncio
async def test_job_repository_create(db_session):
    """Test creating a job"""
    from sheratan_store.repositories import JobRepository
    
    repo = JobRepository(db_session)
    job = await repo.create_job(
        job_type="ingest",
        payload={"url": "http://example.com"},
        priority=5
    )
    
    assert job.id is not None
    assert job.job_type == "ingest"
    assert job.status == "pending"
    assert job.priority == 5


@pytest.mark.asyncio
async def test_job_repository_update_status(db_session):
    """Test updating job status"""
    from sheratan_store.repositories import JobRepository
    
    repo = JobRepository(db_session)
    job = await repo.create_job(
        job_type="ingest",
        payload={"url": "http://example.com"}
    )
    await db_session.commit()
    
    updated = await repo.update_job_status(
        job.id,
        status="running"
    )
    
    assert updated is not None
    assert updated.status == "running"
    assert updated.started_at is not None


@pytest.mark.asyncio
async def test_job_repository_get_pending(db_session):
    """Test getting pending jobs"""
    from sheratan_store.repositories import JobRepository
    
    repo = JobRepository(db_session)
    
    # Create jobs with different priorities
    await repo.create_job(job_type="ingest", payload={}, priority=1)
    await repo.create_job(job_type="ingest", payload={}, priority=5)
    await repo.create_job(job_type="embed", payload={}, priority=3, status="running")
    await db_session.commit()
    
    pending = await repo.get_pending_jobs(limit=10)
    
    assert len(pending) == 2
    # Should be ordered by priority desc
    assert pending[0].priority == 5
    assert pending[1].priority == 1


@pytest.mark.asyncio
async def test_audit_log_repository_create(db_session):
    """Test creating an audit log"""
    from sheratan_store.repositories import AuditLogRepository
    
    repo = AuditLogRepository(db_session)
    log = await repo.create_log(
        event_type="document_access",
        action="read",
        user_id="user123",
        resource_type="document",
        resource_id="doc123",
        ip_address="192.168.1.1"
    )
    
    assert log.id is not None
    assert log.event_type == "document_access"
    assert log.action == "read"
    assert log.user_id == "user123"


@pytest.mark.asyncio
async def test_audit_log_repository_get_by_user(db_session):
    """Test getting audit logs by user"""
    from sheratan_store.repositories import AuditLogRepository
    
    repo = AuditLogRepository(db_session)
    
    await repo.create_log(event_type="test", action="read", user_id="user1")
    await repo.create_log(event_type="test", action="write", user_id="user1")
    await repo.create_log(event_type="test", action="read", user_id="user2")
    await db_session.commit()
    
    logs = await repo.get_logs_by_user("user1")
    
    assert len(logs) == 2
    assert all(log.user_id == "user1" for log in logs)


@pytest.mark.asyncio
async def test_audit_log_repository_search(db_session):
    """Test searching audit logs"""
    from sheratan_store.repositories import AuditLogRepository
    
    repo = AuditLogRepository(db_session)
    
    await repo.create_log(
        event_type="document_access",
        action="read",
        user_id="user1",
        resource_type="document"
    )
    await repo.create_log(
        event_type="search",
        action="execute",
        user_id="user1"
    )
    await db_session.commit()
    
    logs = await repo.search_logs(
        user_id="user1",
        event_type="document_access"
    )
    
    assert len(logs) == 1
    assert logs[0].event_type == "document_access"
