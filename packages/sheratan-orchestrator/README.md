# Sheratan Orchestrator

Background worker for processing documents through the pipeline: crawl, chunk, embed.

## Features

- **Crawling**: Fetch content from URLs
- **Chunking**: Split documents into manageable chunks
- **Embedding**: Generate vector embeddings for chunks

## Running

```bash
# Install dependencies
pip install -r requirements.txt

# Run worker
python -m sheratan_orchestrator.worker
```

## Architecture

The orchestrator processes documents asynchronously:
1. Receives documents from queue
2. Crawls content if URL provided
3. Chunks content into smaller pieces
4. Generates embeddings via sheratan-embeddings
5. Stores results in sheratan-store
