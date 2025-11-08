"""Job repository for background task management"""
from typing import List, Optional, Dict, Any
from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from datetime import datetime

from ..models.documents import Job


class JobRepository:
    """Repository for job operations"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create_job(
        self,
        job_type: str,
        payload: Dict[str, Any],
        priority: int = 0,
        status: str = "pending"
    ) -> Job:
        """Create a new job"""
        job = Job(
            job_type=job_type,
            status=status,
            payload=payload,
            priority=priority
        )
        self.session.add(job)
        await self.session.flush()
        return job
    
    async def get_job(self, job_id: UUID) -> Optional[Job]:
        """Get job by ID"""
        result = await self.session.execute(
            select(Job).where(Job.id == job_id)
        )
        return result.scalar_one_or_none()
    
    async def update_job_status(
        self,
        job_id: UUID,
        status: str,
        result: Optional[Dict[str, Any]] = None,
        error_message: Optional[str] = None
    ) -> Optional[Job]:
        """Update job status and optionally set result or error"""
        job = await self.get_job(job_id)
        if not job:
            return None
        
        job.status = status
        if result is not None:
            job.result = result
        if error_message is not None:
            job.error_message = error_message
        
        # Update timestamps based on status
        if status == "running" and not job.started_at:
            job.started_at = datetime.utcnow()
        elif status in ("completed", "failed"):
            job.completed_at = datetime.utcnow()
        
        await self.session.flush()
        return job
    
    async def get_pending_jobs(
        self,
        job_types: Optional[List[str]] = None,
        limit: int = 10
    ) -> List[Job]:
        """Get pending jobs ordered by priority and creation time"""
        query = select(Job).where(Job.status == "pending")
        
        if job_types:
            query = query.where(Job.job_type.in_(job_types))
        
        query = query.order_by(Job.priority.desc(), Job.created_at.asc()).limit(limit)
        
        result = await self.session.execute(query)
        return list(result.scalars().all())
    
    async def get_jobs_by_status(
        self,
        status: str,
        limit: int = 100
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
            .order_by(Job.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())
    
    async def cleanup_old_jobs(
        self,
        days: int = 30,
        statuses: Optional[List[str]] = None
    ) -> int:
        """Delete old completed/failed jobs"""
        from datetime import timedelta
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        query = select(Job).where(
            Job.created_at < cutoff_date
        )
        
        if statuses:
            query = query.where(Job.status.in_(statuses))
        else:
            query = query.where(Job.status.in_(["completed", "failed"]))
        
        result = await self.session.execute(query)
        jobs = result.scalars().all()
        
        count = len(jobs)
        for job in jobs:
            await self.session.delete(job)
        
        await self.session.flush()
        return count
