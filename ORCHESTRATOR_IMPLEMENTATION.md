# Sheratan Orchestrator Implementation Summary

## Overview

This implementation delivers a complete ETL pipeline orchestrator with background job management using PostgreSQL as the job queue. No external message brokers are required.

## Components Implemented

### 1. Job Queue System (`sheratan-store`)

**Models** (`models/jobs.py`):
- `Job`: Main job entity with status tracking, retry logic, priority, and scheduling
- `JobStatus`: Enum for job states (PENDING, RUNNING, COMPLETED, FAILED, RETRYING, CANCELLED)
- `JobType`: Enum for job types (CRAWL, PARSE, CHUNK, EMBED, FULL_ETL)

**Repository** (`repositories/job_repo.py`):
- `JobRepository`: Complete CRUD operations for job management
- Row-level locking with `SELECT FOR UPDATE SKIP LOCKED` for concurrent processing
- Priority-based job retrieval
- Retry logic and statistics

**Migration** (`migrations/versions/001_create_job_queue.py`):
- Creates `jobs` table with proper indexes
- Optimized for queue operations with indexes on status, type, priority, and scheduling

### 2. ETL Pipeline Components (`sheratan-orchestrator`)

**Crawler** (`crawler.py`):
- Async HTTP fetching using aiohttp
- Configurable timeout and size limits
- Error handling and retry support
- Concurrent crawling of multiple URLs

**Parser** (`parser.py`):
- Content-type aware parsing
- HTML text extraction (removes scripts/styles)
- JSON content parsing with nested text extraction
- XML parsing
- Plain text processing

**Chunker** (`chunker.py`):
- Smart text splitting with configurable overlap
- Separator-aware chunking (paragraphs, newlines)
- Word boundary awareness
- Sentence-based chunking option
- Metadata preservation

**Pipeline** (`pipeline.py`):
- Complete ETL orchestration
- URL processing: crawl → parse → chunk → embed → upsert
- Text processing: chunk → embed → upsert
- Integration with embedding providers
- Database upsert functionality

### 3. Job Manager (`job_manager.py`)

- Async job queue polling
- Configurable concurrency control (MAX_CONCURRENT_JOBS)
- Automatic retry with exponential backoff
- Graceful shutdown handling
- Job type dispatching (FULL_ETL, CRAWL, CHUNK, EMBED)
- Resource cleanup

### 4. Worker (`worker.py`)

- Entry point for orchestrator worker
- Environment configuration
- Logging setup
- Signal handling for graceful shutdown

### 5. CLI Commands (`sheratan-cli`)

New `jobs` command group with subcommands:
- `create`: Create new ETL jobs
- `status`: Get job status by ID
- `list`: List jobs with filtering
- `retry`: Retry failed jobs
- `cancel`: Cancel pending/running jobs
- `stats`: View job statistics
- `cleanup`: Clean up old jobs

## Configuration

### Environment Variables

Added to `.env.example`:
```bash
JOB_POLL_INTERVAL=5          # Seconds between queue polls
MAX_CONCURRENT_JOBS=5        # Max parallel job execution
```

### Dependencies

Added to `sheratan-orchestrator/requirements.txt`:
- aiohttp==3.9.1 (async HTTP client)
- beautifulsoup4==4.12.2 (HTML parsing)

## Testing

**Test Files**:
- `tests/test_job_queue.py`: Job queue operations
- `tests/test_pipeline.py`: ETL pipeline components
- `tests/conftest.py`: Pytest configuration and fixtures

**Test Coverage**:
- Job creation and retrieval
- Priority-based job ordering
- Status updates and transitions
- Retry logic
- Statistics generation
- HTML/JSON/XML/text parsing
- Text chunking with various strategies
- Empty/edge case handling

## Architecture Highlights

### No External Brokers
All job coordination happens through PostgreSQL:
- Jobs stored in database with status tracking
- Row-level locking prevents race conditions
- Indexes optimize queue operations

### Concurrency Control
- `SELECT FOR UPDATE SKIP LOCKED`: Workers skip locked rows
- Configurable worker count
- Graceful handling of concurrent access

### Retry Mechanism
- Configurable max retries per job
- Automatic retry on failure
- Retry count tracking
- Error message preservation

### Priority & Scheduling
- Priority-based job ordering (higher first)
- Optional scheduled execution (future jobs)
- FIFO within priority level

### Embedding Integration
- Uses existing `sheratan-embeddings` providers
- Supports local, OpenAI, and HuggingFace
- Async embedding generation
- Batch processing

## Usage Examples

### Starting the Worker

```bash
cd packages/sheratan-orchestrator
export DATABASE_URL=postgresql://user:pass@localhost:5432/sheratan
export EMBEDDINGS_PROVIDER=local
python -m sheratan_orchestrator.worker
```

### Using CLI

```bash
# Create a job to process a URL
sheratan jobs create --url https://example.com --priority 5

# Check status
sheratan jobs status <job-id>

# List pending jobs
sheratan jobs list --status-filter pending

# View statistics
sheratan jobs stats

# Retry failed jobs
sheratan jobs retry <job-id>
```

### Programmatic Usage

```python
from sheratan_orchestrator.job_manager import JobManager
from sheratan_store.models.jobs import JobType

manager = JobManager()

# Create a job
job_id = await manager.create_job(
    job_type=JobType.FULL_ETL,
    input_data={"url": "https://example.com"},
    priority=5
)

# Start processing
await manager.start()
```

## Security

- **CodeQL Analysis**: ✅ No security vulnerabilities detected
- Input validation on URLs and content
- Size limits on crawled content
- Timeout protection on HTTP requests
- SQL injection prevention via SQLAlchemy ORM
- No hardcoded credentials

## Performance Considerations

- Async I/O for all operations
- Configurable concurrency
- Efficient database queries with indexes
- Row-level locking minimizes contention
- Connection pooling via SQLAlchemy

## Future Enhancements

Potential improvements (not in current scope):
- Dead letter queue for permanently failed jobs
- Job dependencies and workflows
- Webhooks for job completion
- Job metrics and monitoring
- Rate limiting per source
- Distributed worker support
- Job priority adjustment
- Pause/resume functionality

## Migration Path

To use the orchestrator:

1. Run database migration:
   ```bash
   cd packages/sheratan-store
   alembic upgrade head
   ```

2. Install dependencies:
   ```bash
   pip install -r packages/sheratan-orchestrator/requirements.txt
   ```

3. Configure environment:
   ```bash
   cp .env.example .env
   # Edit .env with your settings
   ```

4. Start worker:
   ```bash
   python -m sheratan_orchestrator.worker
   ```

5. Use CLI to manage jobs:
   ```bash
   sheratan jobs create --url https://example.com
   ```

## Summary

This implementation provides a robust, production-ready orchestrator service that:
- ✅ Uses Postgres as job queue (no external brokers)
- ✅ Implements complete ETL pipeline
- ✅ Provides retry logic and error handling
- ✅ Supports priority and scheduling
- ✅ Includes CLI for job management
- ✅ Has test coverage
- ✅ Passes security scan
- ✅ Is fully documented
