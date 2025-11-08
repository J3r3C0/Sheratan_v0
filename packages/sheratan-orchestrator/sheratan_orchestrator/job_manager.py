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
        retry_delay: int = 60
    ):
        """
        Initialize job manager
        
        Args:
            poll_interval: Seconds between queue polls
            max_concurrent_jobs: Maximum concurrent job executions
            retry_delay: Delay before retrying failed jobs (seconds)
        """
        self.poll_interval = poll_interval
        self.max_concurrent_jobs = max_concurrent_jobs
        self.retry_delay = retry_delay
        self.is_running = False
        self.active_jobs: Dict[uuid.UUID, asyncio.Task] = {}
        
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
        
        try:
            while self.is_running:
                await self._process_jobs()
                await asyncio.sleep(self.poll_interval)
        finally:
            await self.stop()
    
    async def stop(self):
        """Stop the job manager"""
        logger.info("Stopping job manager...")
        self.is_running = False
        
        # Wait for active jobs to complete
        if self.active_jobs:
            logger.info(f"Waiting for {len(self.active_jobs)} active jobs to complete...")
            await asyncio.gather(*self.active_jobs.values(), return_exceptions=True)
        
        # Clean up pipeline resources
        await self.pipeline.close()
        
        logger.info("Job manager stopped")
    
    async def _process_jobs(self):
        """Process pending jobs from queue"""
        try:
            # Clean up completed tasks
            completed_job_ids = [
                job_id for job_id, task in self.active_jobs.items()
                if task.done()
            ]
            for job_id in completed_job_ids:
                del self.active_jobs[job_id]
            
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
                    
                    # Mark job as running
                    await repo.update_job_status(job, JobStatus.RUNNING)
                    await session.commit()
                    
                    # Execute job asynchronously
                    task = asyncio.create_task(self._execute_job(job.id))
                    self.active_jobs[job.id] = task
                    
                    logger.info(f"Started job {job.id} ({job.job_type})")
        
        except Exception as e:
            logger.error(f"Error processing jobs: {e}")
    
    async def _execute_job(self, job_id: uuid.UUID):
        """
        Execute a single job
        
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
                
                logger.info(f"Executing job {job_id}: {job.job_type}")
                
                # Execute based on job type
                if job.job_type == JobType.FULL_ETL:
                    result = await self._execute_full_etl(job, session)
                elif job.job_type == JobType.CRAWL:
                    result = await self._execute_crawl(job)
                elif job.job_type == JobType.CHUNK:
                    result = await self._execute_chunk(job)
                elif job.job_type == JobType.EMBED:
                    result = await self._execute_embed(job)
                else:
                    result = {"success": False, "error": f"Unknown job type: {job.job_type}"}
                
                # Update job status based on result
                if result.get("success"):
                    await repo.update_job_status(
                        job,
                        JobStatus.COMPLETED,
                        output_data=result
                    )
                    logger.info(f"Job {job_id} completed successfully")
                else:
                    error = result.get("error", "Unknown error")
                    
                    # Check if can retry
                    if job.can_retry():
                        await repo.update_job_status(job, JobStatus.RETRYING, error_message=error)
                        await repo.retry_job(job)
                        logger.warning(f"Job {job_id} failed, will retry: {error}")
                    else:
                        await repo.update_job_status(job, JobStatus.FAILED, error_message=error)
                        logger.error(f"Job {job_id} failed permanently: {error}")
                
                await session.commit()
        
        except Exception as e:
            logger.error(f"Error executing job {job_id}: {e}")
            
            # Mark job as failed
            try:
                async with AsyncSessionLocal() as session:
                    repo = JobRepository(session)
                    job = await repo.get_job(job_id)
                    if job:
                        await repo.update_job_status(job, JobStatus.FAILED, error_message=str(e))
                        await session.commit()
            except Exception as update_error:
                logger.error(f"Failed to update job status: {update_error}")
    
    async def _execute_full_etl(self, job: Job, session) -> Dict[str, Any]:
        """Execute full ETL pipeline"""
        input_data = job.input_data
        
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
    
    async def _execute_crawl(self, job: Job) -> Dict[str, Any]:
        """Execute crawl job"""
        url = job.input_data.get("url")
        if not url:
            return {"success": False, "error": "No URL provided"}
        
        result = await self.pipeline.crawler.crawl(url)
        return result
    
    async def _execute_chunk(self, job: Job) -> Dict[str, Any]:
        """Execute chunk job"""
        text = job.input_data.get("text")
        if not text:
            return {"success": False, "error": "No text provided"}
        
        chunks = self.pipeline.chunker.chunk(text, metadata=job.input_data.get("metadata"))
        return {
            "success": True,
            "chunks": chunks,
            "count": len(chunks)
        }
    
    async def _execute_embed(self, job: Job) -> Dict[str, Any]:
        """Execute embed job"""
        texts = job.input_data.get("texts")
        if not texts:
            return {"success": False, "error": "No texts provided"}
        
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
