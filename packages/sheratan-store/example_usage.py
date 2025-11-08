"""Example usage of sheratan-store package"""
import asyncio
import os
from uuid import uuid4

# Set environment variables for demo
os.environ['DATABASE_URL'] = 'postgresql://sheratan:sheratan@localhost:5432/sheratan'
os.environ['VECTOR_DIMENSION'] = '384'

async def demo():
    """Demonstrate basic usage of sheratan-store"""
    print("=" * 60)
    print("Sheratan Store - Usage Examples")
    print("=" * 60)
    
    # Import the package
    from sheratan_store import (
        Document, DocumentChunk, Job, AuditLog, SearchLog,
        DocumentRepository, JobRepository, AuditLogRepository,
        schemas
    )
    
    print("\n1. Creating model instances:")
    print("-" * 60)
    
    # Create a document
    doc = Document(
        id=uuid4(),
        content="This is a test document about machine learning.",
        metadata_={"category": "AI", "author": "Test User"},
        source="https://example.com/ml-article"
    )
    print(f"✓ Document: {doc.id}")
    print(f"  Content: {doc.content[:50]}...")
    print(f"  Source: {doc.source}")
    
    # Create a chunk
    chunk = DocumentChunk(
        id=uuid4(),
        document_id=doc.id,
        chunk_index=0,
        content="Machine learning is a subset of AI.",
        embedding=[0.1] * 384,  # Simulated embedding
        metadata_={"type": "paragraph"}
    )
    print(f"\n✓ Chunk: {chunk.id}")
    print(f"  Document: {chunk.document_id}")
    print(f"  Index: {chunk.chunk_index}")
    print(f"  Embedding dims: {len(chunk.embedding)}")
    
    # Create a job
    job = Job(
        id=uuid4(),
        job_type="ingest",
        status="pending",
        payload={"url": "https://example.com/article"},
        priority=5
    )
    print(f"\n✓ Job: {job.id}")
    print(f"  Type: {job.job_type}")
    print(f"  Status: {job.status}")
    print(f"  Priority: {job.priority}")
    
    # Create an audit log
    audit = AuditLog(
        id=uuid4(),
        event_type="document_access",
        action="read",
        user_id="user123",
        resource_type="document",
        resource_id=str(doc.id),
        details={"method": "GET", "path": "/api/documents"},
        ip_address="192.168.1.100"
    )
    print(f"\n✓ Audit Log: {audit.id}")
    print(f"  Event: {audit.event_type}")
    print(f"  User: {audit.user_id}")
    print(f"  Resource: {audit.resource_type}/{audit.resource_id[:8]}...")
    
    print("\n2. Using Pydantic schemas for validation:")
    print("-" * 60)
    
    # Create document with validation
    doc_create = schemas.DocumentCreate(
        content="New document content",
        metadata={"tags": ["test", "demo"]},
        source="internal"
    )
    print(f"✓ DocumentCreate validated:")
    print(f"  Content: {doc_create.content}")
    print(f"  Metadata: {doc_create.metadata}")
    
    # Create vector search request
    search_req = schemas.VectorSearchRequest(
        query="machine learning tutorial",
        top_k=5,
        threshold=0.7
    )
    print(f"\n✓ VectorSearchRequest validated:")
    print(f"  Query: {search_req.query}")
    print(f"  Top K: {search_req.top_k}")
    print(f"  Threshold: {search_req.threshold}")
    
    # Create job with validation
    job_create = schemas.JobCreate(
        job_type="embed",
        status="pending",
        payload={"document_id": str(uuid4())},
        priority=10
    )
    print(f"\n✓ JobCreate validated:")
    print(f"  Type: {job_create.job_type}")
    print(f"  Priority: {job_create.priority}")
    
    print("\n3. Schema validation examples:")
    print("-" * 60)
    
    # Test validation constraints
    try:
        invalid = schemas.VectorSearchRequest(
            query="test",
            top_k=150  # Should fail - max is 100
        )
    except Exception as e:
        print(f"✓ Validation caught: top_k > 100")
    
    try:
        invalid = schemas.DocumentCreate(content="")  # Should fail - min_length=1
    except Exception as e:
        print(f"✓ Validation caught: empty content")
    
    print("\n" + "=" * 60)
    print("Demo completed successfully!")
    print("=" * 60)
    print("\nNote: To actually interact with the database, you need:")
    print("1. PostgreSQL 16 with pgvector extension")
    print("2. Run migrations: alembic upgrade head")
    print("3. Use async context: async with get_db() as db:")
    print("4. Create repositories: repo = DocumentRepository(db)")
    print("\nSee README.md for more examples.")


if __name__ == "__main__":
    asyncio.run(demo())
