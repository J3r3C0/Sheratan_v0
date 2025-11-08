# Sheratan Orchestrator

Background worker for processing documents through the pipeline: crawl, chunk, embed.

## Features

- **Job Queue**: Postgres-based job queue with priority and scheduling
- **ETL Pipeline**: Complete pipeline for crawling, parsing, chunking, and embedding
- **Retry Logic**: Automatic retry with configurable attempts
- **Concurrency Control**: Configurable parallel job execution
- **Status Tracking**: Real-time job status and statistics

## Architecture

The orchestrator uses a Postgres-based job queue (no external brokers required):

1. **Job Queue**: Jobs stored in Postgres with status tracking
2. **Job Manager**: Polls queue and executes jobs with concurrency control
3. **ETL Pipeline**: Orchestrates crawl → parse → chunk → embed → upsert
4. **Embedding Providers**: Pluggable embedding providers (local, OpenAI, HuggingFace)

## Components

### Crawler
- Async HTTP fetching with aiohttp
- Content size limits and timeout handling
- Multiple content type support

### Parser
- HTML text extraction (removes scripts/styles)
- JSON content parsing
- XML parsing
- Plain text processing

### Chunker
- Smart text splitting with overlap
- Separator-aware chunking (paragraphs, sentences)
- Configurable chunk size and overlap

### Pipeline
- Complete ETL orchestration
- Embedding generation and database upsert
- Error handling and recovery

### Job Manager
- Queue polling with configurable interval
- Concurrent job execution
- Automatic retry logic
- Graceful shutdown

## Running

### Start Worker

```bash
# Install dependencies
pip install -r requirements.txt

# Configure environment
export DATABASE_URL=postgresql://user:pass@localhost:5432/sheratan
export EMBEDDINGS_PROVIDER=local
export JOB_POLL_INTERVAL=5
export MAX_CONCURRENT_JOBS=5

# Run worker
python -m sheratan_orchestrator.worker
```

### Using CLI

```bash
# Create a job to process a URL
sheratan jobs create --url https://example.com --priority 5

# Check job status
sheratan jobs status <job-id>

# List jobs
sheratan jobs list --status-filter pending --limit 10

# View statistics
sheratan jobs stats

# Retry a failed job
sheratan jobs retry <job-id>

# Cancel a job
sheratan jobs cancel <job-id>

# Cleanup old jobs
sheratan jobs cleanup --days 30 --confirm
```

## Job Types

- `FULL_ETL`: Complete pipeline (crawl/parse → chunk → embed → upsert)
- `CRAWL`: Fetch content from URL
- `PARSE`: Parse content by type
- `CHUNK`: Split text into chunks
- `EMBED`: Generate embeddings

## Job Status

- `PENDING`: Waiting to be processed
- `RUNNING`: Currently being processed
- `COMPLETED`: Successfully completed
- `FAILED`: Failed (can be retried)
- `RETRYING`: Queued for retry
- `CANCELLED`: Manually cancelled

## Configuration

Environment variables:

```bash
# Job queue settings
JOB_POLL_INTERVAL=5          # Seconds between queue polls
MAX_CONCURRENT_JOBS=5        # Max parallel job execution

# Database
DATABASE_URL=postgresql://...

# Embeddings
EMBEDDINGS_PROVIDER=local
EMBEDDINGS_MODEL=all-MiniLM-L6-v2

# Logging
LOG_LEVEL=INFO
```

## Testing

```bash
pytest tests/
```
