# Sheratan Store - Database Layer

The `sheratan-store` package provides the complete database layer for the Sheratan system, including:
- SQLAlchemy models for all database tables
- Alembic migrations for schema versioning
- Repository pattern for data access
- Pydantic schemas for validation
- pgvector integration for vector similarity search

## Features

### Database Models

All models are defined using SQLAlchemy 2.0 with async support:

1. **Document** - Main document storage
2. **DocumentChunk** - Document chunks with embeddings
3. **Job** - Background job tracking
4. **AuditLog** - Security and compliance audit trail
5. **SearchLog** - Search analytics

### Pydantic Schemas

Validation and serialization schemas for all models with full validation support.

### Repositories

Repository pattern for clean data access:
- `DocumentRepository` - Document and chunk operations, vector search
- `JobRepository` - Job queue management
- `AuditLogRepository` - Audit trail management

## Installation

```bash
cd packages/sheratan-store
pip install -r requirements.txt
```

## Configuration

Set the following environment variables:

```env
# Database connection
DATABASE_URL=postgresql://user:password@localhost:5432/sheratan

# Vector dimensions (must match your embedding model)
VECTOR_DIMENSION=384  # Default for all-MiniLM-L6-v2

# Database pool settings (optional)
DB_POOL_SIZE=5
DB_MAX_OVERFLOW=10
DB_POOL_TIMEOUT=30
DB_POOL_RECYCLE=3600
```

## Database Setup

### 1. Enable pgvector Extension

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

### 2. Run Migrations

```bash
cd packages/sheratan-store
alembic upgrade head
```

## Usage

### Basic Database Operations

```python
from sheratan_store import get_db, DocumentRepository

async def create_document():
    async with get_db() as db:
        repo = DocumentRepository(db)
        doc = await repo.create_document(
            content="Document content",
            metadata={"category": "tutorial"},
            source="https://example.com/doc"
        )
        return doc
```

### Vector Similarity Search

```python
async def search_similar(query_embedding, top_k=5):
    async with get_db() as db:
        repo = DocumentRepository(db)
        results = await repo.search_similar(
            query_embedding=query_embedding,
            top_k=top_k,
            threshold=0.7
        )
        return results
```

### Job Queue Management

```python
from sheratan_store import JobRepository

async def create_job(url):
    async with get_db() as db:
        repo = JobRepository(db)
        job = await repo.create_job(
            job_type="ingest",
            payload={"url": url},
            priority=5
        )
        return job
```

## Testing

```bash
# Unit tests (no database required)
pytest tests/test_models.py tests/test_schemas.py

# Integration tests (requires DATABASE_URL)
export DATABASE_URL=postgresql://sheratan:sheratan@localhost:5432/sheratan_test
pytest tests/test_repositories.py
```

## License

Part of the Sheratan v0 project.
