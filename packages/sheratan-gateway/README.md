# Sheratan Gateway

FastAPI REST endpoints for document ingestion, search, and RAG-based answers.

## Features

- **Authentication**: JWT (HMAC) tokens and API keys
- **Database**: PostgreSQL with pgvector support
- **OpenAPI Documentation**: Automatic via FastAPI
- **Endpoints**:
  - `POST /auth/token` - Get JWT access token
  - `POST /ingest` - Ingest documents for indexing (authenticated)
  - `POST /search` - Semantic search across documents (authenticated)
  - `POST /answer` - RAG-based question answering (authenticated, requires LLM)
  - `GET /admin` - System information and status (authenticated)
  - `GET /health` - Health check
  - `GET /` - Root endpoint

## Environment Variables

### Gateway Configuration
- `GATEWAY_HOST` - Host to bind (default: 0.0.0.0)
- `GATEWAY_PORT` - Port to bind (default: 8000)

### Database
- `DATABASE_URL` - PostgreSQL connection URL (default: postgresql://sheratan:sheratan@localhost:5432/sheratan)

### Authentication
- `JWT_SECRET_KEY` - Secret key for JWT signing (default: dev-secret-key-change-in-production)
- `JWT_ALGORITHM` - JWT algorithm (default: HS256)
- `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` - Token expiration time in minutes (default: 30)
- `API_KEYS` - Comma-separated list of valid API keys (optional)

### Features
- `LLM_ENABLED` - Enable LLM for /answer endpoint (default: false)
- `EMBEDDINGS_PROVIDER` - Embeddings provider: local, openai, huggingface (default: local)

## Authentication

The gateway supports two authentication methods:

### 1. JWT Tokens (Bearer)
```bash
# Get a token
curl -X POST http://localhost:8000/auth/token \
  -H "Content-Type: application/json" \
  -d '{"username": "myuser", "password": ""}'

# Use the token
curl -X POST http://localhost:8000/search \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -H "Content-Type: application/json" \
  -d '{"query": "test", "top_k": 5}'
```

### 2. API Keys
```bash
# Use API key in header
curl -X POST http://localhost:8000/search \
  -H "X-API-Key: your-api-key-here" \
  -H "Content-Type: application/json" \
  -d '{"query": "test", "top_k": 5}'
```

**Note**: If no API keys are configured and JWT_SECRET_KEY is set to the default value, authentication is not required (development mode).

## Running

```bash
# Install dependencies
pip install -r requirements.txt

# Run server
python -m sheratan_gateway.app

# Or with uvicorn
uvicorn sheratan_gateway.app:app --host 0.0.0.0 --port 8000 --reload
```

## API Documentation

When running, visit:
- `http://localhost:8000/docs` - Interactive Swagger UI documentation
- `http://localhost:8000/redoc` - ReDoc documentation
- `http://localhost:8000/openapi.json` - OpenAPI schema

## Testing

```bash
# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_auth.py -v
pytest tests/test_app.py -v
```

## Example Usage

### Ingest Documents
```bash
curl -X POST http://localhost:8000/ingest \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "documents": [
      {
        "content": "This is a test document",
        "metadata": {"source": "test"},
        "source": "manual"
      }
    ]
  }'
```

### Search Documents
```bash
curl -X POST http://localhost:8000/search \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "test document",
    "top_k": 5
  }'
```

### Admin Information
```bash
curl -X GET http://localhost:8000/admin \
  -H "Authorization: Bearer YOUR_TOKEN"
```
