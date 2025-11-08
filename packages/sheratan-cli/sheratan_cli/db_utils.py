"""Database utilities for CLI"""
import os
import sys
from pathlib import Path
from typing import Dict, Any
import asyncio


def get_database_url() -> str:
    """Get database URL from environment"""
    url = os.getenv(
        "DATABASE_URL",
        "postgresql://sheratan:sheratan@localhost:5432/sheratan"
    )
    return url


def get_async_database_url() -> str:
    """Get async database URL"""
    url = get_database_url()
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+asyncpg://")
    return url


async def init_database():
    """Initialize database (create tables)"""
    # Add sheratan-store to path
    store_path = Path(__file__).parent.parent.parent / "sheratan-store"
    if store_path.exists():
        sys.path.insert(0, str(store_path))
    
    from sheratan_store.database import init_db
    await init_db()


async def drop_all_tables():
    """Drop all tables (destructive)"""
    from sqlalchemy import create_engine, text
    from sheratan_store.database import Base, sync_engine
    
    # Drop all tables
    Base.metadata.drop_all(sync_engine)


async def get_database_stats() -> Dict[str, Any]:
    """Get database statistics"""
    from sqlalchemy import select, func
    from sheratan_store.database import AsyncSessionLocal
    from sheratan_store.models.documents import Document, DocumentChunk, SearchLog
    
    async with AsyncSessionLocal() as session:
        # Count documents
        doc_result = await session.execute(select(func.count(Document.id)))
        doc_count = doc_result.scalar()
        
        # Count chunks
        chunk_result = await session.execute(select(func.count(DocumentChunk.id)))
        chunk_count = chunk_result.scalar()
        
        # Count searches
        search_result = await session.execute(select(func.count(SearchLog.id)))
        search_count = search_result.scalar()
        
        return {
            "documents": doc_count or 0,
            "chunks": chunk_count or 0,
            "searches": search_count or 0
        }


async def cleanup_orphaned_chunks():
    """Remove chunks without parent documents"""
    from sqlalchemy import select, delete
    from sheratan_store.database import AsyncSessionLocal
    from sheratan_store.models.documents import Document, DocumentChunk
    
    async with AsyncSessionLocal() as session:
        # Find orphaned chunks
        subquery = select(Document.id)
        delete_stmt = delete(DocumentChunk).where(
            DocumentChunk.document_id.notin_(subquery)
        )
        
        result = await session.execute(delete_stmt)
        await session.commit()
        
        return result.rowcount


async def vacuum_database():
    """Run database vacuum (PostgreSQL)"""
    from sqlalchemy import text
    from sheratan_store.database import sync_engine
    
    # Vacuum must be run outside transaction
    with sync_engine.connect() as conn:
        conn.execution_options(isolation_level="AUTOCOMMIT")
        conn.execute(text("VACUUM ANALYZE"))


async def get_document_list(limit: int = 10, offset: int = 0) -> list:
    """Get list of documents"""
    from sqlalchemy import select
    from sheratan_store.database import AsyncSessionLocal
    from sheratan_store.models.documents import Document
    
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Document)
            .order_by(Document.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        
        documents = result.scalars().all()
        
        return [
            {
                "id": str(doc.id),
                "source": doc.source,
                "content_preview": doc.content[:100] + "..." if len(doc.content) > 100 else doc.content,
                "created_at": doc.created_at.isoformat() if doc.created_at else None,
                "metadata": doc.metadata
            }
            for doc in documents
        ]


async def clear_seed_data():
    """Clear all data from database"""
    from sqlalchemy import delete
    from sheratan_store.database import AsyncSessionLocal
    from sheratan_store.models.documents import Document, DocumentChunk, SearchLog
    
    async with AsyncSessionLocal() as session:
        # Delete in correct order (chunks first due to foreign key)
        await session.execute(delete(DocumentChunk))
        await session.execute(delete(SearchLog))
        await session.execute(delete(Document))
        await session.commit()


async def backfill_embeddings():
    """Re-generate embeddings for all chunks"""
    from sheratan_store.database import AsyncSessionLocal
    from sheratan_store.models.documents import DocumentChunk
    from sheratan_embeddings.providers import get_embedding_provider
    from sqlalchemy import select
    
    provider = get_embedding_provider()
    
    async with AsyncSessionLocal() as session:
        # Get all chunks
        result = await session.execute(select(DocumentChunk))
        chunks = result.scalars().all()
        
        if not chunks:
            return 0
        
        # Process in batches
        batch_size = 100
        total_updated = 0
        
        for i in range(0, len(chunks), batch_size):
            batch = chunks[i:i + batch_size]
            
            # Generate embeddings
            contents = [chunk.content for chunk in batch]
            embeddings = provider.embed(contents)
            
            # Update chunks
            for chunk, embedding in zip(batch, embeddings):
                chunk.embedding = embedding
                total_updated += 1
            
            await session.commit()
        
        return total_updated


def run_alembic_command(command: str, *args):
    """Run alembic command"""
    from alembic.config import Config
    from alembic import command as alembic_command
    
    # Find alembic.ini
    store_path = Path(__file__).parent.parent.parent / "sheratan-store"
    alembic_ini = store_path / "alembic.ini"
    
    if not alembic_ini.exists():
        raise FileNotFoundError(f"alembic.ini not found at {alembic_ini}")
    
    # Create config
    alembic_cfg = Config(str(alembic_ini))
    
    # Run command
    if command == "upgrade":
        alembic_command.upgrade(alembic_cfg, args[0] if args else "head")
    elif command == "downgrade":
        alembic_command.downgrade(alembic_cfg, args[0] if args else "-1")
    elif command == "current":
        alembic_command.current(alembic_cfg)
    elif command == "history":
        alembic_command.history(alembic_cfg)
    else:
        raise ValueError(f"Unknown alembic command: {command}")
