"""Repository for job queue operations"""
from typing import List, Optional
from datetime import datetime, timedelta
from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
import uuid

from ..models.jobs import Job, JobStatus, JobType


class JobRepository:
    """Repository for job queue operations"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create_job(
        self,
        job_type: JobType,
        input_data: dict,
        priority: int = 0,
        scheduled_at: Optional[datetime] = None,
        max_retries: int = 3,
        metadata: Optional[dict] = None
    ) -> Job:
        """
        Create a new job
        
        Args:
            job_type: Type of job to create
            input_data: Input parameters for the job
            priority: Job priority (higher = more important)
            scheduled_at: When to run the job (None = immediately)
            max_retries: Maximum number of retry attempts
            metadata: Additional metadata
            
        Returns:
            Created Job instance
        """
        job = Job(
            id=uuid.uuid4(),
            job_type=job_type,
            status=JobStatus.PENDING,
            input_data=input_data,
            priority=priority,
            scheduled_at=scheduled_at,
            max_retries=max_retries,
            job_metadata=metadata or {}
        )
        
        self.session.add(job)
        await self.session.flush()
        return job
    
    async def get_job(self, job_id: uuid.UUID) -> Optional[Job]:
        """Get job by ID"""
        result = await self.session.execute(
            select(Job).where(Job.id == job_id)
        )
        return result.scalar_one_or_none()
    
    async def get_next_pending_job(self) -> Optional[Job]:
        """
        Get the next pending job to process
        
        Returns jobs by:
        1. Priority (higher first)
        2. Creation time (older first)
        3. Only jobs that are scheduled or not scheduled at all
        """
        now = datetime.utcnow()
        
        result = await self.session.execute(
            select(Job)
            .where(
                and_(
                    Job.status == JobStatus.PENDING,
                    or_(
                        Job.scheduled_at.is_(None),
                        Job.scheduled_at <= now
                    )
                )
            )
            .order_by(Job.priority.desc(), Job.created_at.asc())
            .limit(1)
            .with_for_update(skip_locked=True)  # PostgreSQL row-level locking
        )
        
        return result.scalar_one_or_none()
    
    async def update_job_status(
        self,
        job: Job,
        status: JobStatus,
        error_message: Optional[str] = None,
        output_data: Optional[dict] = None
    ) -> Job:
        """
        Update job status
        
        Args:
            job: Job to update
            status: New status
            error_message: Error message (if failed)
            output_data: Output data (if completed)
        """
        job.status = status
        
        if status == JobStatus.RUNNING:
            job.started_at = datetime.utcnow()
        
        elif status == JobStatus.COMPLETED:
            job.completed_at = datetime.utcnow()
            if output_data:
                job.output_data = output_data
        
        elif status == JobStatus.FAILED:
            job.completed_at = datetime.utcnow()
            if error_message:
                job.error_message = error_message
        
        elif status == JobStatus.RETRYING:
            job.retry_count += 1
        
        await self.session.flush()
        return job
    
    async def get_jobs_by_status(
        self,
        status: JobStatus,
        limit: int = 100,
        offset: int = 0
    ) -> List[Job]:
        """Get jobs by status"""
        result = await self.session.execute(
            select(Job)
            .where(Job.status == status)
            .order_by(Job.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())
    
    async def get_jobs_by_type(
        self,
        job_type: str,
        limit: int = 100
    ) -> List[Job]:
        """Get jobs by type"""
        result = await self.session.execute(
            select(Job)
            .where(Job.job_type == job_type)
            .offset(offset)
        )
        return list(result.scalars().all())
    
    async def get_failed_jobs(self, limit: int = 100) -> List[Job]:
        """Get failed jobs that can be retried"""
        result = await self.session.execute(
            select(Job)
            .where(
                and_(
                    Job.status == JobStatus.FAILED,
                    Job.retry_count < Job.max_retries
                )
            )
            .order_by(Job.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())
    
    async def retry_job(self, job: Job) -> Job:
        """Retry a failed job"""
        if not job.can_retry():
            raise ValueError(f"Job {job.id} has exceeded max retries")
        
        job.status = JobStatus.PENDING
        job.retry_count += 1
        job.error_message = None
        
        await self.session.flush()
        return job
    
    async def cancel_job(self, job: Job) -> Job:
        """Cancel a pending or running job"""
        if job.status in [JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED]:
            raise ValueError(f"Cannot cancel job in status {job.status}")
        
        job.status = JobStatus.CANCELLED
        job.completed_at = datetime.utcnow()
        
        await self.session.flush()
        return job
    
    async def get_job_statistics(self) -> dict:
        """Get job statistics"""
        from sqlalchemy import func
        
        result = await self.session.execute(
            select(
                Job.status,
                func.count(Job.id).label('count')
            )
            .group_by(Job.status)
        )
        
        stats = {status.value: 0 for status in JobStatus}
        for row in result:
            stats[row.status] = row.count
        
        return stats
    
    async def cleanup_old_jobs(self, days: int = 30) -> int:
        """
        Delete completed/failed jobs older than specified days
        
        Args:
            days: Number of days to keep
            
        Returns:
            Number of jobs deleted
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        result = await self.session.execute(
            select(Job)
            .where(
                and_(
                    Job.status.in_([JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED]),
                    Job.completed_at < cutoff_date
                )
            )
        )
        
        jobs_to_delete = list(result.scalars().all())
        
        for job in jobs_to_delete:
            await self.session.delete(job)
        
        await self.session.flush()
        return len(jobs_to_delete)
    
    async def update_heartbeat(
        self,
        job: Job,
        lease_duration_seconds: int = 300
    ) -> Job:
        """
        Update job heartbeat and extend lease
        
        Args:
            job: Job to update
            lease_duration_seconds: Duration of the lease in seconds (default 5 minutes)
            
        Returns:
            Updated job
        """
        now = datetime.utcnow()
        job.heartbeat_at = now
        job.lease_expires_at = now + timedelta(seconds=lease_duration_seconds)
        
        await self.session.flush()
        return job
    
    async def acquire_job_lease(
        self,
        job: Job,
        worker_id: str,
        lease_duration_seconds: int = 300
    ) -> Job:
        """
        Acquire a lease on a job for a specific worker
        
        Args:
            job: Job to acquire lease on
            worker_id: Unique identifier of the worker
            lease_duration_seconds: Duration of the lease in seconds (default 5 minutes)
            
        Returns:
            Updated job with lease
        """
        now = datetime.utcnow()
        job.worker_id = worker_id
        job.heartbeat_at = now
        job.lease_expires_at = now + timedelta(seconds=lease_duration_seconds)
        job.started_at = now if not job.started_at else job.started_at
        
        await self.session.flush()
        return job
    
    async def release_job_lease(self, job: Job) -> Job:
        """
        Release the lease on a job
        
        Args:
            job: Job to release lease from
            
        Returns:
            Updated job
        """
        job.worker_id = None
        job.heartbeat_at = None
        job.lease_expires_at = None
        
        await self.session.flush()
        return job
    
    async def get_zombie_jobs(
        self,
        lease_grace_period_seconds: int = 60
    ) -> list[Job]:
        """
        Find zombie jobs (running jobs with expired leases)
        
        Args:
            lease_grace_period_seconds: Additional grace period beyond lease expiration (default 60s)
            
        Returns:
            List of zombie jobs
        """
        now = datetime.utcnow()
        grace_cutoff = now - timedelta(seconds=lease_grace_period_seconds)
        
        result = await self.session.execute(
            select(Job)
            .where(
                and_(
                    Job.status == JobStatus.RUNNING,
                    Job.lease_expires_at.isnot(None),
                    Job.lease_expires_at < grace_cutoff
                )
            )
            .with_for_update(skip_locked=True)
        )
        
        return list(result.scalars().all())
    
    async def recover_zombie_job(
        self,
        job: Job,
        retry: bool = True
    ) -> Job:
        """
        Recover a zombie job by resetting it for retry or marking as failed
        
        Args:
            job: Zombie job to recover
            retry: If True, reset to PENDING for retry; if False, mark as FAILED
            
        Returns:
            Recovered job
        """
        # Release the lease
        job.worker_id = None
        job.heartbeat_at = None
        job.lease_expires_at = None
        
        if retry and job.can_retry():
            # Reset to pending for retry
            job.status = JobStatus.PENDING
            job.retry_count += 1
            job.error_message = f"Job recovered from zombie state. Previous worker may have crashed."
        else:
            # Mark as failed
            job.status = JobStatus.FAILED
            job.completed_at = datetime.utcnow()
            job.error_message = f"Job failed: worker crashed and max retries exceeded"
        
        await self.session.flush()
        return job
    
    async def check_cancellation_requested(self, job_id: uuid.UUID) -> bool:
        """
        Check if cancellation has been requested for a job
        
        This is called periodically by running jobs to check if they should stop.
        
        Args:
            job_id: Job ID to check
            
        Returns:
            True if job status is CANCELLED, False otherwise
        """
        result = await self.session.execute(
            select(Job.status)
            .where(Job.id == job_id)
        )
        row = result.first()
        
        if not row:
            return False
        
        return row[0] == JobStatus.CANCELLED
