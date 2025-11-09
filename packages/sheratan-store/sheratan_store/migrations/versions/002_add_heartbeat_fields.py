"""Add heartbeat and worker tracking fields

Revision ID: 002_heartbeat
Revises: 001_job_queue
Create Date: 2025-11-08 21:45:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '002_heartbeat'
down_revision = '001_job_queue'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add worker tracking and heartbeat fields to jobs table"""
    op.add_column('jobs', sa.Column('worker_id', sa.String(255)))
    op.add_column('jobs', sa.Column('heartbeat_at', sa.DateTime(timezone=True)))
    op.add_column('jobs', sa.Column('lease_expires_at', sa.DateTime(timezone=True)))
    
    # Create indexes for efficient zombie job detection
    op.create_index('idx_jobs_worker_id', 'jobs', ['worker_id'])
    op.create_index('idx_jobs_heartbeat', 'jobs', ['heartbeat_at'])
    op.create_index('idx_jobs_lease_expires', 'jobs', ['lease_expires_at'])


def downgrade() -> None:
    """Remove worker tracking and heartbeat fields from jobs table"""
    op.drop_index('idx_jobs_lease_expires')
    op.drop_index('idx_jobs_heartbeat')
    op.drop_index('idx_jobs_worker_id')
    op.drop_column('jobs', 'lease_expires_at')
    op.drop_column('jobs', 'heartbeat_at')
    op.drop_column('jobs', 'worker_id')
