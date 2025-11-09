"""Job Queue models for orchestrator"""
from sqlalchemy import Column, String, Text, DateTime, Integer, JSON, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import uuid
from datetime import datetime
from enum import Enum

from ..database import Base


class JobStatus(str, Enum):
    """Job status enumeration"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"
    CANCELLED = "cancelled"


class JobType(str, Enum):
    """Job type enumeration"""
    CRAWL = "crawl"
    PARSE = "parse"
    CHUNK = "chunk"
    EMBED = "embed"
    FULL_ETL = "full_etl"  # Complete pipeline


class Job(Base):
    """Job queue table for ETL pipeline"""
    __tablename__ = "jobs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_type = Column(SQLEnum(JobType), nullable=False)
    status = Column(SQLEnum(JobStatus), nullable=False, default=JobStatus.PENDING)
    
    # Job data
    input_data = Column(JSON, nullable=False)  # Input parameters (URL, content, etc.)
    output_data = Column(JSON)  # Results after completion
    
    # Retry and error handling
    retry_count = Column(Integer, default=0)
    max_retries = Column(Integer, default=3)
    error_message = Column(Text)
    
    # Scheduling
    priority = Column(Integer, default=0)  # Higher = more priority
    scheduled_at = Column(DateTime(timezone=True))  # For future scheduling
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Worker tracking and heartbeat for zombie detection
    worker_id = Column(String(255))  # Unique identifier of the worker processing this job
    heartbeat_at = Column(DateTime(timezone=True))  # Last heartbeat timestamp
    lease_expires_at = Column(DateTime(timezone=True))  # When the job lease expires
    
    # Metadata - renamed to avoid SQLAlchemy reserved attribute
    job_metadata = Column(JSON, default={})
    
    def __repr__(self):
        return f"<Job {self.id} {self.job_type} {self.status}>"
    
    def can_retry(self) -> bool:
        """Check if job can be retried"""
        return self.retry_count < self.max_retries
    
    def mark_failed(self, error: str):
        """Mark job as failed"""
        self.status = JobStatus.FAILED
        self.error_message = error
        self.completed_at = datetime.utcnow()
    
    def mark_completed(self, output: dict):
        """Mark job as completed"""
        self.status = JobStatus.COMPLETED
        self.output_data = output
        self.completed_at = datetime.utcnow()
    
    def mark_retrying(self):
        """Mark job for retry"""
        self.status = JobStatus.RETRYING
        self.retry_count += 1
    
    def is_lease_expired(self) -> bool:
        """
        Check if the job lease has expired
        
        Returns:
            True if lease has expired, False otherwise
        """
        if not self.lease_expires_at:
            return False
        return datetime.utcnow() >= self.lease_expires_at
    
    def can_be_cancelled(self) -> bool:
        """
        Check if job can be cancelled
        
        Returns:
            True if job is in a cancellable state
        """
        return self.status in [JobStatus.PENDING, JobStatus.RUNNING]
