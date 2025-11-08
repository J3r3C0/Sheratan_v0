"""Worker for processing documents: crawl, chunk, embed"""
import asyncio
import logging
import os
from dotenv import load_dotenv

from .job_manager import JobManager

# Load environment variables
load_dotenv()

# Configure logging
log_level = os.getenv("LOG_LEVEL", "INFO")
logging.basicConfig(
    level=getattr(logging, log_level),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def main():
    """Entry point for worker"""
    logger.info("Starting Sheratan Orchestrator Worker")
    
    # Configuration from environment
    poll_interval = int(os.getenv("JOB_POLL_INTERVAL", "5"))
    max_concurrent = int(os.getenv("MAX_CONCURRENT_JOBS", "5"))
    
    # Create and start job manager
    manager = JobManager(
        poll_interval=poll_interval,
        max_concurrent_jobs=max_concurrent
    )
    
    try:
        await manager.start()
    except KeyboardInterrupt:
        logger.info("Received shutdown signal")
    finally:
        await manager.stop()
        logger.info("Worker stopped")


if __name__ == "__main__":
    asyncio.run(main())
