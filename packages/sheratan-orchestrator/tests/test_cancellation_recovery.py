"""Tests for job cancellation and worker recovery functionality"""
import pytest
import asyncio
import uuid
from datetime import datetime, timedelta
from unittest.mock import patch, AsyncMock

from sheratan_store.models.jobs import Job, JobStatus, JobType
from sheratan_store.repositories.job_repo import JobRepository
from sheratan_store.database import AsyncSessionLocal
from sheratan_orchestrator.job_manager import JobManager


@pytest.mark.asyncio
async def test_acquire_and_release_job_lease():
    """Test acquiring and releasing job lease"""
    async with AsyncSessionLocal() as session:
        repo = JobRepository(session)
        
        # Create a job
        job = await repo.create_job(
            job_type=JobType.CRAWL,
            input_data={"url": "https://example.com"}
        )
        await session.commit()
        
        # Acquire lease
        worker_id = "test-worker-123"
        await repo.acquire_job_lease(job, worker_id, lease_duration_seconds=300)
        
        assert job.worker_id == worker_id
        assert job.heartbeat_at is not None
        assert job.lease_expires_at is not None
        assert job.lease_expires_at > datetime.utcnow()
        
        # Release lease
        await repo.release_job_lease(job)
        
        assert job.worker_id is None
        assert job.heartbeat_at is None
        assert job.lease_expires_at is None


@pytest.mark.asyncio
async def test_heartbeat_update():
    """Test heartbeat updates extend lease"""
    async with AsyncSessionLocal() as session:
        repo = JobRepository(session)
        
        # Create and acquire job
        job = await repo.create_job(
            job_type=JobType.CRAWL,
            input_data={"url": "https://example.com"}
        )
        await repo.acquire_job_lease(job, "worker-1", lease_duration_seconds=60)
        await session.commit()
        
        first_lease_expires = job.lease_expires_at
        first_heartbeat = job.heartbeat_at
        
        # Wait a moment
        await asyncio.sleep(0.1)
        
        # Update heartbeat
        await repo.update_heartbeat(job, lease_duration_seconds=60)
        
        # Lease should be extended
        assert job.lease_expires_at > first_lease_expires
        assert job.heartbeat_at > first_heartbeat


@pytest.mark.asyncio
async def test_zombie_job_detection():
    """Test detection of zombie jobs with expired leases"""
    async with AsyncSessionLocal() as session:
        repo = JobRepository(session)
        
        # Create a job with expired lease (simulate zombie)
        job = await repo.create_job(
            job_type=JobType.CRAWL,
            input_data={"url": "https://example.com"}
        )
        await repo.update_job_status(job, JobStatus.RUNNING)
        
        # Set expired lease
        job.worker_id = "crashed-worker"
        job.heartbeat_at = datetime.utcnow() - timedelta(minutes=10)
        job.lease_expires_at = datetime.utcnow() - timedelta(minutes=5)
        await session.commit()
        
        # Find zombie jobs
        zombies = await repo.get_zombie_jobs(lease_grace_period_seconds=60)
        
        assert len(zombies) >= 1
        assert any(z.id == job.id for z in zombies)


@pytest.mark.asyncio
async def test_zombie_job_recovery():
    """Test recovery of zombie jobs"""
    async with AsyncSessionLocal() as session:
        repo = JobRepository(session)
        
        # Create zombie job
        job = await repo.create_job(
            job_type=JobType.CRAWL,
            input_data={"url": "https://example.com"},
            max_retries=3
        )
        await repo.update_job_status(job, JobStatus.RUNNING)
        job.worker_id = "crashed-worker"
        job.heartbeat_at = datetime.utcnow() - timedelta(minutes=10)
        job.lease_expires_at = datetime.utcnow() - timedelta(minutes=5)
        await session.commit()
        
        # Recover the job
        recovered = await repo.recover_zombie_job(job, retry=True)
        await session.commit()
        
        # Should be reset to pending for retry
        assert recovered.status == JobStatus.PENDING
        assert recovered.retry_count == 1
        assert recovered.worker_id is None
        assert recovered.lease_expires_at is None
        assert "zombie" in recovered.error_message.lower()


@pytest.mark.asyncio
async def test_zombie_job_recovery_max_retries_exceeded():
    """Test zombie job marked as failed when max retries exceeded"""
    async with AsyncSessionLocal() as session:
        repo = JobRepository(session)
        
        # Create zombie job that has already been retried max times
        job = await repo.create_job(
            job_type=JobType.CRAWL,
            input_data={"url": "https://example.com"},
            max_retries=2
        )
        job.retry_count = 2  # Already at max
        await repo.update_job_status(job, JobStatus.RUNNING)
        job.worker_id = "crashed-worker"
        job.lease_expires_at = datetime.utcnow() - timedelta(minutes=5)
        await session.commit()
        
        # Recover the job
        recovered = await repo.recover_zombie_job(job, retry=True)
        await session.commit()
        
        # Should be marked as failed
        assert recovered.status == JobStatus.FAILED
        assert recovered.completed_at is not None
        assert "crashed" in recovered.error_message.lower()


@pytest.mark.asyncio
async def test_check_cancellation_requested():
    """Test checking if cancellation has been requested"""
    async with AsyncSessionLocal() as session:
        repo = JobRepository(session)
        
        # Create a job
        job = await repo.create_job(
            job_type=JobType.CRAWL,
            input_data={"url": "https://example.com"}
        )
        await session.commit()
        
        # Initially not cancelled
        is_cancelled = await repo.check_cancellation_requested(job.id)
        assert is_cancelled is False
        
        # Cancel the job
        await repo.cancel_job(job)
        await session.commit()
        
        # Now should be cancelled
        is_cancelled = await repo.check_cancellation_requested(job.id)
        assert is_cancelled is True


@pytest.mark.asyncio
async def test_cancel_pending_job():
    """Test cancelling a pending job"""
    async with AsyncSessionLocal() as session:
        repo = JobRepository(session)
        
        # Create pending job
        job = await repo.create_job(
            job_type=JobType.CRAWL,
            input_data={"url": "https://example.com"}
        )
        await session.commit()
        
        assert job.status == JobStatus.PENDING
        
        # Cancel it
        cancelled = await repo.cancel_job(job)
        await session.commit()
        
        assert cancelled.status == JobStatus.CANCELLED
        assert cancelled.completed_at is not None


@pytest.mark.asyncio
async def test_cancel_running_job():
    """Test cancelling a running job"""
    async with AsyncSessionLocal() as session:
        repo = JobRepository(session)
        
        # Create and start job
        job = await repo.create_job(
            job_type=JobType.CRAWL,
            input_data={"url": "https://example.com"}
        )
        await repo.update_job_status(job, JobStatus.RUNNING)
        await session.commit()
        
        # Cancel it
        cancelled = await repo.cancel_job(job)
        await session.commit()
        
        assert cancelled.status == JobStatus.CANCELLED


@pytest.mark.asyncio
async def test_cannot_cancel_completed_job():
    """Test that completed jobs cannot be cancelled"""
    async with AsyncSessionLocal() as session:
        repo = JobRepository(session)
        
        # Create completed job
        job = await repo.create_job(
            job_type=JobType.CRAWL,
            input_data={"url": "https://example.com"}
        )
        await repo.update_job_status(job, JobStatus.COMPLETED)
        await session.commit()
        
        # Try to cancel
        with pytest.raises(ValueError):
            await repo.cancel_job(job)


@pytest.mark.asyncio
async def test_job_can_be_cancelled_method():
    """Test the can_be_cancelled method"""
    async with AsyncSessionLocal() as session:
        repo = JobRepository(session)
        
        # Pending job can be cancelled
        job = await repo.create_job(
            job_type=JobType.CRAWL,
            input_data={"url": "https://example.com"}
        )
        assert job.can_be_cancelled() is True
        
        # Running job can be cancelled
        await repo.update_job_status(job, JobStatus.RUNNING)
        assert job.can_be_cancelled() is True
        
        # Completed job cannot be cancelled
        await repo.update_job_status(job, JobStatus.COMPLETED)
        assert job.can_be_cancelled() is False


@pytest.mark.asyncio
async def test_job_is_lease_expired_method():
    """Test the is_lease_expired method"""
    async with AsyncSessionLocal() as session:
        repo = JobRepository(session)
        
        job = await repo.create_job(
            job_type=JobType.CRAWL,
            input_data={"url": "https://example.com"}
        )
        
        # No lease set
        assert job.is_lease_expired() is False
        
        # Active lease
        job.lease_expires_at = datetime.utcnow() + timedelta(minutes=5)
        assert job.is_lease_expired() is False
        
        # Expired lease
        job.lease_expires_at = datetime.utcnow() - timedelta(minutes=5)
        assert job.is_lease_expired() is True


@pytest.mark.asyncio
async def test_job_manager_cancel_job():
    """Test JobManager cancel_job method"""
    # Mock the pipeline to avoid initialization issues
    with patch('sheratan_orchestrator.job_manager.get_embedding_provider'):
        manager = JobManager()
        
        async with AsyncSessionLocal() as session:
            repo = JobRepository(session)
            
            # Create a pending job
            job = await repo.create_job(
                job_type=JobType.CRAWL,
                input_data={"url": "https://example.com"}
            )
            await session.commit()
            job_id = job.id
        
        # Cancel through manager
        result = await manager.cancel_job(job_id)
        assert result is True
        
        # Verify it's cancelled
        async with AsyncSessionLocal() as session:
            repo = JobRepository(session)
            job = await repo.get_job(job_id)
            assert job.status == JobStatus.CANCELLED


@pytest.mark.asyncio
async def test_job_manager_worker_id_generation():
    """Test that JobManager generates unique worker ID"""
    with patch('sheratan_orchestrator.job_manager.get_embedding_provider'):
        manager1 = JobManager()
        manager2 = JobManager()
        
        # Each manager should have a unique worker ID
        assert manager1.worker_id != manager2.worker_id
        assert len(manager1.worker_id) > 0
        assert len(manager2.worker_id) > 0


@pytest.mark.asyncio
async def test_cooperative_cancellation_in_execute():
    """Test that job execution checks for cancellation"""
    with patch('sheratan_orchestrator.job_manager.get_embedding_provider'):
        manager = JobManager()
        
        async with AsyncSessionLocal() as session:
            repo = JobRepository(session)
            
            # Create a job
            job = await repo.create_job(
                job_type=JobType.CRAWL,
                input_data={"url": "https://example.com"}
            )
            await repo.update_job_status(job, JobStatus.RUNNING)
            await repo.acquire_job_lease(job, manager.worker_id)
            
            # Mark as cancelled
            await repo.cancel_job(job)
            await session.commit()
            job_id = job.id
        
        # Try to execute - should detect cancellation
        await manager._execute_job(job_id)
        
        # Verify job is cancelled and lease released
        async with AsyncSessionLocal() as session:
            repo = JobRepository(session)
            job = await repo.get_job(job_id)
            assert job.status == JobStatus.CANCELLED
            assert job.worker_id is None


@pytest.mark.asyncio
async def test_heartbeat_loop_stops_when_job_completes():
    """Test that heartbeat loop stops when job is no longer active"""
    with patch('sheratan_orchestrator.job_manager.get_embedding_provider'):
        manager = JobManager(heartbeat_interval=1)
        
        async with AsyncSessionLocal() as session:
            repo = JobRepository(session)
            job = await repo.create_job(
                job_type=JobType.CRAWL,
                input_data={"url": "https://example.com"}
            )
            await session.commit()
            job_id = job.id
        
        # Start heartbeat loop
        heartbeat_task = asyncio.create_task(manager._heartbeat_loop(job_id))
        
        # Let it run for a bit
        await asyncio.sleep(2)
        
        # Should stop when job not in active_jobs
        await asyncio.sleep(2)
        
        # Task should complete
        assert heartbeat_task.done()


@pytest.mark.asyncio 
async def test_zombie_recovery_on_startup():
    """Test that zombie jobs are recovered when manager starts"""
    with patch('sheratan_orchestrator.job_manager.get_embedding_provider'):
        # Create a zombie job
        async with AsyncSessionLocal() as session:
            repo = JobRepository(session)
            job = await repo.create_job(
                job_type=JobType.CRAWL,
                input_data={"url": "https://example.com"}
            )
            await repo.update_job_status(job, JobStatus.RUNNING)
            job.worker_id = "old-worker"
            job.lease_expires_at = datetime.utcnow() - timedelta(minutes=10)
            await session.commit()
            job_id = job.id
        
        # Create manager (will recover zombies on start)
        manager = JobManager()
        await manager._recover_zombie_jobs()
        
        # Check job was recovered
        async with AsyncSessionLocal() as session:
            repo = JobRepository(session)
            job = await repo.get_job(job_id)
            assert job.status == JobStatus.PENDING  # Reset for retry
            assert job.worker_id is None


@pytest.mark.asyncio
async def test_graceful_shutdown_cancels_heartbeats():
    """Test that graceful shutdown cancels heartbeat tasks"""
    with patch('sheratan_orchestrator.job_manager.get_embedding_provider'):
        manager = JobManager()
        
        # Create some mock heartbeat tasks
        task1 = asyncio.create_task(asyncio.sleep(100))
        task2 = asyncio.create_task(asyncio.sleep(100))
        
        manager.heartbeat_tasks[uuid.uuid4()] = task1
        manager.heartbeat_tasks[uuid.uuid4()] = task2
        
        # Stop manager
        await manager.stop()
        
        # Tasks should be cancelled
        assert task1.cancelled()
        assert task2.cancelled()
        assert len(manager.heartbeat_tasks) == 0
