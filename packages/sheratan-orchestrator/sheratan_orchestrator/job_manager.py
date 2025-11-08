"""Job manager for orchestrating ETL jobs"""
import asyncio
import logging
from typing import Optional, Dict, Any
from datetime import datetime
import uuid

from sheratan_store.database import AsyncSessionLocal
from sheratan_store.models.jobs import Job, JobStatus, JobType
from sheratan_store.repositories.job_repo import JobRepository
from sheratan_embeddings.providers import get_embedding_provider

from .pipeline import ETLPipeline

logger = logging.getLogger(__name__)


class JobManager:
    """Manages job queue and executes ETL jobs"""
    
    def __init__(
        self,
        poll_interval: int = 5,
        max_concurrent_jobs: int = 5,
        retry_delay: int = 60,
        heartbeat_interval: int = 30,
        lease_duration: int = 300
    ):
        """
        Initialize job manager
        
        Args:
            poll_interval: Seconds between queue polls
            max_concurrent_jobs: Maximum concurrent job executions
            retry_delay: Delay before retrying failed jobs (seconds)
            heartbeat_interval: Seconds between heartbeat updates (default 30s)
            lease_duration: Job lease duration in seconds (default 300s/5min)
        """
        self.poll_interval = poll_interval
        self.max_concurrent_jobs = max_concurrent_jobs
        self.retry_delay = retry_delay
        self.heartbeat_interval = heartbeat_interval
        self.lease_duration = lease_duration
        self.is_running = False
        self.active_jobs: Dict[uuid.UUID, asyncio.Task] = {}
        self.heartbeat_tasks: Dict[uuid.UUID, asyncio.Task] = {}
        
        # Generate unique worker ID
        import socket
        import os
        self.worker_id = f"{socket.gethostname()}-{os.getpid()}-{uuid.uuid4().hex[:8]}"
        logger.info(f"Worker ID: {self.worker_id}")
        
        # Initialize ETL pipeline with embedding provider
        try:
            embedding_provider = get_embedding_provider()
            self.pipeline = ETLPipeline(embedding_provider=embedding_provider)
            logger.info("ETL pipeline initialized with embedding provider")
        except Exception as e:
            logger.warning(f"Failed to initialize embedding provider: {e}")
            self.pipeline = ETLPipeline()
    
    async def start(self):
        """Start the job manager"""
        logger.info("Starting job manager...")
        self.is_running = True
        
        # Recover any zombie jobs on startup
        await self._recover_zombie_jobs()
        
        try:
            while self.is_running:
                await self._process_jobs()
                await self._recover_zombie_jobs()
                await asyncio.sleep(self.poll_interval)
        finally:
            await self.stop()
    
    async def stop(self):
        """Stop the job manager gracefully"""
        logger.info("Stopping job manager...")
        self.is_running = False
        
        # Cancel all heartbeat tasks
        if self.heartbeat_tasks:
            logger.info(f"Cancelling {len(self.heartbeat_tasks)} heartbeat tasks...")
            for task in self.heartbeat_tasks.values():
                task.cancel()
            await asyncio.gather(*self.heartbeat_tasks.values(), return_exceptions=True)
            self.heartbeat_tasks.clear()
        
        # Wait for active jobs to complete (with timeout)
        if self.active_jobs:
            logger.info(f"Waiting for {len(self.active_jobs)} active jobs to complete...")
            try:
                # Give jobs 30 seconds to complete gracefully
                await asyncio.wait_for(
                    asyncio.gather(*self.active_jobs.values(), return_exceptions=True),
                    timeout=30.0
                )
            except asyncio.TimeoutError:
                logger.warning("Timeout waiting for jobs to complete, cancelling remaining jobs...")
                for task in self.active_jobs.values():
                    task.cancel()
                await asyncio.gather(*self.active_jobs.values(), return_exceptions=True)
        
        # Clean up pipeline resources
        await self.pipeline.close()
        
        logger.info("Job manager stopped")
    
    async def _process_jobs(self):
        """Process pending jobs from queue"""
        try:
            # Clean up completed tasks and their heartbeats
            completed_job_ids = [
                job_id for job_id, task in self.active_jobs.items()
                if task.done()
            ]
            for job_id in completed_job_ids:
                del self.active_jobs[job_id]
                # Cancel and clean up heartbeat task
                if job_id in self.heartbeat_tasks:
                    self.heartbeat_tasks[job_id].cancel()
                    try:
                        await self.heartbeat_tasks[job_id]
                    except asyncio.CancelledError:
                        pass
                    del self.heartbeat_tasks[job_id]
            
            # Check if we can process more jobs
            available_slots = self.max_concurrent_jobs - len(self.active_jobs)
            if available_slots <= 0:
                return
            
            # Get pending jobs
            async with AsyncSessionLocal() as session:
                repo = JobRepository(session)
                
                for _ in range(available_slots):
                    job = await repo.get_next_pending_job()
                    if not job:
                        break
                    
                    # Mark job as running and acquire lease
                    await repo.update_job_status(job, JobStatus.RUNNING)
                    await repo.acquire_job_lease(
                        job,
                        self.worker_id,
                        lease_duration_seconds=self.lease_duration
                    )
                    await session.commit()
                    
                    # Execute job asynchronously
                    task = asyncio.create_task(self._execute_job(job.id))
                    self.active_jobs[job.id] = task
                    
                    # Start heartbeat task
                    heartbeat_task = asyncio.create_task(self._heartbeat_loop(job.id))
                    self.heartbeat_tasks[job.id] = heartbeat_task
                    
                    logger.info(f"Started job {job.id} ({job.job_type}) with worker {self.worker_id}")
        
        except Exception as e:
            logger.error(f"Error processing jobs: {e}")
    
    async def _execute_job(self, job_id: uuid.UUID):
        """
        Execute a single job with cancellation support
        
        Args:
            job_id: Job ID to execute
        """
        try:
            async with AsyncSessionLocal() as session:
                repo = JobRepository(session)
                job = await repo.get_job(job_id)
                
                if not job:
                    logger.error(f"Job {job_id} not found")
                    return
                
                # Check for cancellation before starting
                if await repo.check_cancellation_requested(job_id):
                    logger.info(f"Job {job_id} was cancelled before execution")
                    await repo.release_job_lease(job)
                    await session.commit()
                    return
                
                logger.info(f"Executing job {job_id}: {job.job_type}")
                
                # Execute based on job type with cancellation checks
                result = None
                try:
                    if job.job_type == JobType.FULL_ETL:
                        result = await self._execute_full_etl(job, session, job_id)
                    elif job.job_type == JobType.CRAWL:
                        result = await self._execute_crawl(job, job_id)
                    elif job.job_type == JobType.CHUNK:
                        result = await self._execute_chunk(job, job_id)
                    elif job.job_type == JobType.EMBED:
                        result = await self._execute_embed(job, job_id)
                    else:
                        result = {"success": False, "error": f"Unknown job type: {job.job_type}"}
                except asyncio.CancelledError:
                    # Job was cancelled during execution
                    logger.info(f"Job {job_id} execution was cancelled")
                    await repo.release_job_lease(job)
                    await session.commit()
                    return
                
                # Check for cancellation after execution
                if await repo.check_cancellation_requested(job_id):
                    logger.info(f"Job {job_id} was cancelled during execution")
                    await repo.release_job_lease(job)
                    await session.commit()
                    return
                
                # Update job status based on result
                if result and result.get("success"):
                    await repo.update_job_status(
                        job,
                        JobStatus.COMPLETED,
                        output_data=result
                    )
                    await repo.release_job_lease(job)
                    logger.info(f"Job {job_id} completed successfully")
                else:
                    error = result.get("error", "Unknown error") if result else "No result returned"
                    
                    # Check if can retry
                    if job.can_retry():
                        await repo.update_job_status(job, JobStatus.RETRYING, error_message=error)
                        await repo.retry_job(job)
                        await repo.release_job_lease(job)
                        logger.warning(f"Job {job_id} failed, will retry: {error}")
                    else:
                        await repo.update_job_status(job, JobStatus.FAILED, error_message=error)
                        await repo.release_job_lease(job)
                        logger.error(f"Job {job_id} failed permanently: {error}")
                
                await session.commit()
        
        except asyncio.CancelledError:
            # Handle cancellation at the task level
            logger.info(f"Job {job_id} task was cancelled")
            try:
                async with AsyncSessionLocal() as session:
                    repo = JobRepository(session)
                    job = await repo.get_job(job_id)
                    if job and job.status == JobStatus.RUNNING:
                        await repo.release_job_lease(job)
                        await session.commit()
            except Exception as e:
                logger.error(f"Error releasing lease after cancellation: {e}")
            raise
        
        except Exception as e:
            logger.error(f"Error executing job {job_id}: {e}")
            
            # Mark job as failed and release lease
            try:
                async with AsyncSessionLocal() as session:
                    repo = JobRepository(session)
                    job = await repo.get_job(job_id)
                    if job:
                        await repo.update_job_status(job, JobStatus.FAILED, error_message=str(e))
                        await repo.release_job_lease(job)
                        await session.commit()
            except Exception as update_error:
                logger.error(f"Failed to update job status: {update_error}")
    
    async def _execute_full_etl(self, job: Job, session, job_id: uuid.UUID) -> Dict[str, Any]:
        """Execute full ETL pipeline with cancellation checks"""
        input_data = job.input_data
        
        # Check for cancellation
        async with AsyncSessionLocal() as check_session:
            repo = JobRepository(check_session)
            if await repo.check_cancellation_requested(job_id):
                logger.info(f"Job {job_id} cancellation detected during ETL")
                raise asyncio.CancelledError()
        
        if "url" in input_data:
            # Process URL
            result = await self.pipeline.process_url(
                input_data["url"],
                metadata=input_data.get("metadata")
            )
        elif "text" in input_data:
            # Process text
            result = await self.pipeline.process_text(
                input_data["text"],
                metadata=input_data.get("metadata")
            )
        else:
            return {"success": False, "error": "No URL or text provided"}
        
        if not result.get("success"):
            return result
        
        # Check for cancellation before database operations
        async with AsyncSessionLocal() as check_session:
            repo = JobRepository(check_session)
            if await repo.check_cancellation_requested(job_id):
                logger.info(f"Job {job_id} cancellation detected before upsert")
                raise asyncio.CancelledError()
        
        # Upsert to database
        chunks = result.get("chunks", [])
        document_id = input_data.get("document_id")
        
        upsert_result = await self.pipeline.upsert_to_store(chunks, document_id, session)
        
        return {
            "success": upsert_result.get("success"),
            "document_id": upsert_result.get("document_id"),
            "chunks_created": len(chunks),
            "pipeline_result": result
        }
    
    async def _execute_crawl(self, job: Job, job_id: uuid.UUID) -> Dict[str, Any]:
        """Execute crawl job with cancellation check"""
        url = job.input_data.get("url")
        if not url:
            return {"success": False, "error": "No URL provided"}
        
        # Check for cancellation
        async with AsyncSessionLocal() as check_session:
            repo = JobRepository(check_session)
            if await repo.check_cancellation_requested(job_id):
                logger.info(f"Job {job_id} cancellation detected during crawl")
                raise asyncio.CancelledError()
        
        result = await self.pipeline.crawler.crawl(url)
        return result
    
    async def _execute_chunk(self, job: Job, job_id: uuid.UUID) -> Dict[str, Any]:
        """Execute chunk job with cancellation check"""
        text = job.input_data.get("text")
        if not text:
            return {"success": False, "error": "No text provided"}
        
        # Check for cancellation
        async with AsyncSessionLocal() as check_session:
            repo = JobRepository(check_session)
            if await repo.check_cancellation_requested(job_id):
                logger.info(f"Job {job_id} cancellation detected during chunk")
                raise asyncio.CancelledError()
        
        chunks = self.pipeline.chunker.chunk(text, metadata=job.input_data.get("metadata"))
        return {
            "success": True,
            "chunks": chunks,
            "count": len(chunks)
        }
    
    async def _execute_embed(self, job: Job, job_id: uuid.UUID) -> Dict[str, Any]:
        """Execute embed job with cancellation check"""
        texts = job.input_data.get("texts")
        if not texts:
            return {"success": False, "error": "No texts provided"}
        
        # Check for cancellation
        async with AsyncSessionLocal() as check_session:
            repo = JobRepository(check_session)
            if await repo.check_cancellation_requested(job_id):
                logger.info(f"Job {job_id} cancellation detected during embed")
                raise asyncio.CancelledError()
        
        chunks = [{"text": t, "index": i, "metadata": {}} for i, t in enumerate(texts)]
        embeddings = await self.pipeline._embed_chunks(chunks)
        
        return {
            "success": True,
            "embeddings": embeddings,
            "count": len(embeddings)
        }
    
    async def create_job(
        self,
        job_type: JobType,
        input_data: Dict[str, Any],
        priority: int = 0,
        max_retries: int = 3
    ) -> uuid.UUID:
        """
        Create a new job
        
        Args:
            job_type: Type of job
            input_data: Input parameters
            priority: Job priority
            max_retries: Maximum retry attempts
            
        Returns:
            Job ID
        """
        async with AsyncSessionLocal() as session:
            repo = JobRepository(session)
            job = await repo.create_job(
                job_type=job_type,
                input_data=input_data,
                priority=priority,
                max_retries=max_retries
            )
            await session.commit()
            
            logger.info(f"Created job {job.id}: {job_type}")
            return job.id
    
    async def get_job_status(self, job_id: uuid.UUID) -> Optional[Dict[str, Any]]:
        """Get job status"""
        async with AsyncSessionLocal() as session:
            repo = JobRepository(session)
            job = await repo.get_job(job_id)
            
            if not job:
                return None
            
            return {
                "id": str(job.id),
                "type": job.job_type.value,
                "status": job.status.value,
                "created_at": job.created_at.isoformat() if job.created_at else None,
                "started_at": job.started_at.isoformat() if job.started_at else None,
                "completed_at": job.completed_at.isoformat() if job.completed_at else None,
                "retry_count": job.retry_count,
                "error_message": job.error_message,
                "output_data": job.output_data
            }
    
    async def cancel_job(self, job_id: uuid.UUID) -> bool:
        """
        Request cancellation of a running or pending job
        
        This method marks the job as CANCELLED. For RUNNING jobs, the worker will
        cooperatively stop execution at the next checkpoint.
        
        Args:
            job_id: Job ID to cancel
            
        Returns:
            True if job was cancelled, False if job couldn't be cancelled
        """
        try:
            async with AsyncSessionLocal() as session:
                repo = JobRepository(session)
                job = await repo.get_job(job_id)
                
                if not job:
                    logger.error(f"Job {job_id} not found")
                    return False
                
                if not job.can_be_cancelled():
                    logger.warning(f"Job {job_id} cannot be cancelled (status: {job.status})")
                    return False
                
                await repo.cancel_job(job)
                await session.commit()
                
                logger.info(f"Job {job_id} marked for cancellation")
                return True
        
        except Exception as e:
            logger.error(f"Error cancelling job {job_id}: {e}")
            return False
    
    async def _heartbeat_loop(self, job_id: uuid.UUID):
        """
        Maintain heartbeat for a running job
        
        Periodically updates the job's heartbeat timestamp and extends its lease
        to prevent it from being detected as a zombie.
        
        Args:
            job_id: Job ID to maintain heartbeat for
        """
        try:
            while True:
                await asyncio.sleep(self.heartbeat_interval)
                
                # Check if job is still active
                if job_id not in self.active_jobs:
                    logger.debug(f"Job {job_id} no longer active, stopping heartbeat")
                    break
                
                # Update heartbeat
                try:
                    async with AsyncSessionLocal() as session:
                        repo = JobRepository(session)
                        job = await repo.get_job(job_id)
                        
                        if job and job.status == JobStatus.RUNNING:
                            await repo.update_heartbeat(job, lease_duration_seconds=self.lease_duration)
                            await session.commit()
                            logger.debug(f"Heartbeat updated for job {job_id}")
                        else:
                            logger.debug(f"Job {job_id} no longer running, stopping heartbeat")
                            break
                
                except Exception as e:
                    logger.error(f"Error updating heartbeat for job {job_id}: {e}")
                    # Continue trying to send heartbeats even after error
        
        except asyncio.CancelledError:
            logger.debug(f"Heartbeat cancelled for job {job_id}")
            raise
    
    async def _recover_zombie_jobs(self):
        """
        Detect and recover zombie jobs
        
        Zombie jobs are RUNNING jobs whose lease has expired, indicating the
        worker may have crashed. This method resets them for retry or marks
        them as failed.
        """
        try:
            async with AsyncSessionLocal() as session:
                repo = JobRepository(session)
                
                # Find zombie jobs (running jobs with expired leases)
                zombie_jobs = await repo.get_zombie_jobs(
                    lease_grace_period_seconds=60  # 1 minute grace period
                )
                
                if not zombie_jobs:
                    return
                
                logger.warning(f"Found {len(zombie_jobs)} zombie jobs")
                
                for job in zombie_jobs:
                    logger.warning(
                        f"Recovering zombie job {job.id} "
                        f"(worker: {job.worker_id}, "
                        f"last heartbeat: {job.heartbeat_at})"
                    )
                    
                    # Recover the job (retry if possible, otherwise fail)
                    await repo.recover_zombie_job(job, retry=True)
                
                await session.commit()
                logger.info(f"Recovered {len(zombie_jobs)} zombie jobs")
        
        except Exception as e:
            logger.error(f"Error recovering zombie jobs: {e}")
