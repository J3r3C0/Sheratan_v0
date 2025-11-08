"""Tests for job queue functionality"""
import pytest
import uuid
from datetime import datetime, timedelta

from sheratan_store.models.jobs import Job, JobStatus, JobType
from sheratan_store.repositories.job_repo import JobRepository
from sheratan_store.database import AsyncSessionLocal


@pytest.mark.asyncio
async def test_create_job():
    """Test creating a new job"""
    async with AsyncSessionLocal() as session:
        repo = JobRepository(session)
        
        job = await repo.create_job(
            job_type=JobType.FULL_ETL,
            input_data={"url": "https://example.com"},
            priority=5
        )
        
        assert job.id is not None
        assert job.job_type == JobType.FULL_ETL
        assert job.status == JobStatus.PENDING
        assert job.priority == 5
        assert job.input_data["url"] == "https://example.com"


@pytest.mark.asyncio
async def test_get_next_pending_job():
    """Test getting next pending job by priority"""
    async with AsyncSessionLocal() as session:
        repo = JobRepository(session)
        
        # Create jobs with different priorities
        job1 = await repo.create_job(
            job_type=JobType.CRAWL,
            input_data={"url": "https://example1.com"},
            priority=1
        )
        
        job2 = await repo.create_job(
            job_type=JobType.CRAWL,
            input_data={"url": "https://example2.com"},
            priority=10
        )
        
        await session.commit()
        
        # Higher priority job should be returned first
        next_job = await repo.get_next_pending_job()
        assert next_job is not None
        assert next_job.id == job2.id
        assert next_job.priority == 10


@pytest.mark.asyncio
async def test_update_job_status():
    """Test updating job status"""
    async with AsyncSessionLocal() as session:
        repo = JobRepository(session)
        
        job = await repo.create_job(
            job_type=JobType.CHUNK,
            input_data={"text": "sample text"}
        )
        
        # Update to running
        await repo.update_job_status(job, JobStatus.RUNNING)
        assert job.status == JobStatus.RUNNING
        assert job.started_at is not None
        
        # Update to completed
        output = {"chunks": 5}
        await repo.update_job_status(job, JobStatus.COMPLETED, output_data=output)
        assert job.status == JobStatus.COMPLETED
        assert job.completed_at is not None
        assert job.output_data == output


@pytest.mark.asyncio
async def test_retry_job():
    """Test retrying a failed job"""
    async with AsyncSessionLocal() as session:
        repo = JobRepository(session)
        
        job = await repo.create_job(
            job_type=JobType.EMBED,
            input_data={"texts": ["test"]},
            max_retries=3
        )
        
        # Mark as failed
        await repo.update_job_status(job, JobStatus.FAILED, error_message="Test error")
        assert job.status == JobStatus.FAILED
        
        # Retry
        await repo.retry_job(job)
        assert job.status == JobStatus.PENDING
        assert job.retry_count == 1


@pytest.mark.asyncio
async def test_job_statistics():
    """Test getting job statistics"""
    async with AsyncSessionLocal() as session:
        repo = JobRepository(session)
        
        # Create various jobs
        await repo.create_job(JobType.CRAWL, {"url": "test1"})
        await repo.create_job(JobType.CRAWL, {"url": "test2"})
        
        job3 = await repo.create_job(JobType.EMBED, {"texts": ["test"]})
        await repo.update_job_status(job3, JobStatus.COMPLETED)
        
        await session.commit()
        
        stats = await repo.get_job_statistics()
        assert stats["pending"] >= 2
        assert stats["completed"] >= 1
