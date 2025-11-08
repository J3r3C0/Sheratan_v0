# Sheratan Gateway

FastAPI REST endpoints for document ingestion, search, and RAG-based answers.

## Endpoints

- `GET /` - Root endpoint
- `GET /health` - Health check
- `POST /ingest` - Ingest documents for indexing
- `POST /search` - Semantic search across documents
- `POST /answer` - RAG-based question answering (requires LLM_ENABLED=true)

## Environment Variables

- `GATEWAY_HOST` - Host to bind (default: 0.0.0.0)
- `GATEWAY_PORT` - Port to bind (default: 8000)
- `LLM_ENABLED` - Enable LLM for /answer endpoint (default: false)
- `EMBEDDINGS_PROVIDER` - Embeddings provider (default: local)

## Running

```bash
# Install dependencies
pip install -r requirements.txt

# Run server
python -m sheratan_gateway.app

# Or with uvicorn
uvicorn sheratan_gateway.app:app --host 0.0.0.0 --port 8000
```

## API Documentation

When running, visit `http://localhost:8000/docs` for interactive Swagger UI documentation.
