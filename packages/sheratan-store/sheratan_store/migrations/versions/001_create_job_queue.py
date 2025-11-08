"""Create job queue table

Revision ID: 001_job_queue
Revises: 
Create Date: 2025-11-08 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001_job_queue'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create jobs table"""
    op.create_table(
        'jobs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('job_type', sa.String(50), nullable=False),
        sa.Column('status', sa.String(50), nullable=False),
        sa.Column('input_data', postgresql.JSON, nullable=False),
        sa.Column('output_data', postgresql.JSON),
        sa.Column('retry_count', sa.Integer, default=0),
        sa.Column('max_retries', sa.Integer, default=3),
        sa.Column('error_message', sa.Text),
        sa.Column('priority', sa.Integer, default=0),
        sa.Column('scheduled_at', sa.DateTime(timezone=True)),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('started_at', sa.DateTime(timezone=True)),
        sa.Column('completed_at', sa.DateTime(timezone=True)),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now()),
        sa.Column('metadata', postgresql.JSON, default={}),
    )
    
    # Create indexes for efficient querying
    op.create_index('idx_jobs_status', 'jobs', ['status'])
    op.create_index('idx_jobs_type', 'jobs', ['job_type'])
    op.create_index('idx_jobs_created', 'jobs', ['created_at'])
    op.create_index('idx_jobs_priority', 'jobs', ['priority', 'created_at'])
    op.create_index('idx_jobs_scheduled', 'jobs', ['scheduled_at'])


def downgrade() -> None:
    """Drop jobs table"""
    op.drop_index('idx_jobs_scheduled')
    op.drop_index('idx_jobs_priority')
    op.drop_index('idx_jobs_created')
    op.drop_index('idx_jobs_type')
    op.drop_index('idx_jobs_status')
    op.drop_table('jobs')
