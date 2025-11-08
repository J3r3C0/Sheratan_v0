"""Initial schema with all tables

Revision ID: 001_initial_schema
Revises: 
Create Date: 2024-11-08 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from pgvector.sqlalchemy import Vector
import os

# revision identifiers, used by Alembic.
revision = '001_initial_schema'
down_revision = None
branch_labels = None
depends_on = None

# Get vector dimension from environment or use default
VECTOR_DIMENSION = int(os.getenv("VECTOR_DIMENSION", "384"))


def upgrade() -> None:
    """Create all tables and enable pgvector extension"""
    
    # Enable pgvector extension
    op.execute('CREATE EXTENSION IF NOT EXISTS vector')
    
    # Create documents table
    op.create_table(
        'documents',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, primary_key=True),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('metadata', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('source', sa.String(length=500), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_documents_created', 'documents', ['created_at'])
    op.create_index('idx_documents_source', 'documents', ['source'])
    
    # Create document_chunks table
    op.create_table(
        'document_chunks',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, primary_key=True),
        sa.Column('document_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('chunk_index', sa.Integer(), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('embedding', Vector(VECTOR_DIMENSION), nullable=True),
        sa.Column('metadata', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['document_id'], ['documents.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_chunks_document', 'document_chunks', ['document_id'])
    
    # Create vector index for similarity search
    # Note: IVFFlat index requires data to be present, so we create it after initial data load
    # or use the following command when data is available:
    op.execute(
        f"CREATE INDEX IF NOT EXISTS idx_chunks_embedding "
        f"ON document_chunks USING ivfflat (embedding vector_cosine_ops)"
    )
    
    # Create jobs table
    op.create_table(
        'jobs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, primary_key=True),
        sa.Column('job_type', sa.String(length=50), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('payload', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('result', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('priority', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_jobs_status', 'jobs', ['status'])
    op.create_index('idx_jobs_type', 'jobs', ['job_type'])
    op.create_index('idx_jobs_created', 'jobs', ['created_at'])
    op.create_index('idx_jobs_priority', 'jobs', ['priority', 'created_at'])
    
    # Create audit_logs table
    op.create_table(
        'audit_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, primary_key=True),
        sa.Column('event_type', sa.String(length=50), nullable=False),
        sa.Column('user_id', sa.String(length=255), nullable=True),
        sa.Column('action', sa.String(length=100), nullable=False),
        sa.Column('resource_type', sa.String(length=50), nullable=True),
        sa.Column('resource_id', sa.String(length=255), nullable=True),
        sa.Column('details', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('user_agent', sa.String(length=500), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_audit_created', 'audit_logs', ['created_at'])
    op.create_index('idx_audit_event_type', 'audit_logs', ['event_type'])
    op.create_index('idx_audit_user', 'audit_logs', ['user_id'])
    op.create_index('idx_audit_resource', 'audit_logs', ['resource_type', 'resource_id'])
    
    # Create search_logs table
    op.create_table(
        'search_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, primary_key=True),
        sa.Column('query', sa.Text(), nullable=False),
        sa.Column('results_count', sa.Integer(), nullable=True),
        sa.Column('avg_score', sa.Float(), nullable=True),
        sa.Column('metadata', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_search_logs_created', 'search_logs', ['created_at'])


def downgrade() -> None:
    """Drop all tables and extension"""
    
    # Drop all tables
    op.drop_table('search_logs')
    op.drop_table('audit_logs')
    op.drop_table('jobs')
    op.drop_table('document_chunks')
    op.drop_table('documents')
    
    # Optionally drop extension (commented out to be safe)
    # op.execute('DROP EXTENSION IF EXISTS vector')
