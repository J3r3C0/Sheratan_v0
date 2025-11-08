"""Sheratan Store - Database migrations and repositories"""
__version__ = "0.1.0"

from .database import (
    Base,
    get_db,
    init_db,
    close_db,
    check_pgvector_extension,
    async_engine,
    sync_engine,
)

from .models import (
    Document,
    DocumentChunk,
    Job,
    AuditLog,
    SearchLog,
)

from .repositories import (
    DocumentRepository,
    JobRepository,
    AuditLogRepository,
)

from . import schemas

__all__ = [
    # Database
    "Base",
    "get_db",
    "init_db",
    "close_db",
    "check_pgvector_extension",
    "async_engine",
    "sync_engine",
    # Models
    "Document",
    "DocumentChunk",
    "Job",
    "AuditLog",
    "SearchLog",
    # Repositories
    "DocumentRepository",
    "JobRepository",
    "AuditLogRepository",
    # Schemas
    "schemas",
]

