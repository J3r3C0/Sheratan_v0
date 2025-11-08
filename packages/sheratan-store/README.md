# Sheratan Store

Database layer with PostgreSQL 16 + pgvector for vector embeddings.

## Features

- **Models**: SQLAlchemy models for documents, chunks, and search logs
- **Repositories**: Clean data access patterns
- **Migrations**: Alembic for database schema management
- **Vector Search**: pgvector integration for semantic search

## Setup

### Install pgvector extension

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

### Run migrations

```bash
# Install dependencies
pip install -r requirements.txt

# Create initial migration
alembic revision --autogenerate -m "initial schema"

# Apply migrations
alembic upgrade head
```

## Models

- `Document`: Main document storage
- `DocumentChunk`: Chunks with vector embeddings (384 dimensions)
- `SearchLog`: Search analytics

## Usage

```python
from sheratan_store.database import get_db
from sheratan_store.repositories.document_repo import DocumentRepository

async def example():
    async for db in get_db():
        repo = DocumentRepository(db)
        
        # Create document
        doc = await repo.create_document(
            content="Some text",
            metadata={"source": "web"}
        )
        
        # Create chunk with embedding
        chunk = await repo.create_chunk(
            document_id=doc.id,
            chunk_index=0,
            content="Some text",
            embedding=[0.1, 0.2, ...]  # 384 dimensions
        )
        
        # Search similar
        results = await repo.search_similar(
            query_embedding=[0.1, 0.2, ...],
            top_k=5
        )
```

## Environment Variables

- `DATABASE_URL` - PostgreSQL connection string
- `PGVECTOR_ENABLED` - Enable pgvector (default: true)
