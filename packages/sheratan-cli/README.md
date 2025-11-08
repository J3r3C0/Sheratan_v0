# Sheratan CLI

Command-line interface for Sheratan administration, maintenance, and operations.

## Installation

```bash
cd packages/sheratan-cli
pip install -r requirements.txt
```

## Usage

```bash
# Show help
sheratan --help

# Or run as module
python -m sheratan_cli.cli --help
```

## Commands

### Database Management (`db`)

Initialize, migrate, and manage the database.

```bash
# Initialize database schema
sheratan db init

# Run database migrations
sheratan db migrate

# Show database statistics
sheratan db stats

# Reset database (destructive, requires --confirm)
sheratan db reset --confirm
```

### Seed Data (`seed`)

Generate and load demo/test data for development.

```bash
# Generate and ingest sample documents (demo dataset)
sheratan seed sample

# Generate different sized datasets
sheratan seed sample --size minimal    # 5 documents
sheratan seed sample --size demo       # 20 documents
sheratan seed sample --size full       # 50 documents

# Save sample data to file instead of ingesting
sheratan seed sample --save ./seed_data.json

# Load seed data from file
sheratan seed load --file ./seed_data.json

# Clear all seed data (requires --confirm)
sheratan seed clear --confirm
```

### Document Management (`documents`)

Ingest, search, and manage documents.

```bash
# Ingest single file
sheratan documents ingest ./document.txt

# Ingest directory (non-recursive)
sheratan documents ingest ./docs/

# Ingest directory recursively
sheratan documents ingest ./docs/ --recursive

# Search documents
sheratan documents search "machine learning"
sheratan documents search "cloud computing" --top-k 10

# Show document statistics
sheratan documents stats

# List documents
sheratan documents list
sheratan documents list --limit 20 --offset 10
```

### Admin Jobs (`admin`)

Background jobs for maintenance and repair.

```bash
# Re-generate embeddings for all chunks (backfill)
sheratan admin backfill
sheratan admin backfill --batch-size 200

# Compact database (remove orphaned data)
sheratan admin compact

# Repair database inconsistencies
sheratan admin repair

# Run database vacuum (PostgreSQL maintenance)
sheratan admin vacuum
```

### Security (`guard`)

PII detection and security policies.

```bash
# Scan text for PII
sheratan guard scan "Contact: john@example.com"

# List active security policies
sheratan guard policies
```

### Configuration (`config`)

View and validate configuration.

```bash
# Show current configuration
sheratan config show

# Validate configuration
sheratan config check
```

## Complete Examples

### Initial Setup

```bash
# Set up environment variables
export DATABASE_URL="postgresql://sheratan:sheratan@localhost:5432/sheratan"
export EMBEDDINGS_PROVIDER="local"
export GATEWAY_HOST="localhost"
export GATEWAY_PORT="8000"

# Initialize database
sheratan db init

# Generate and load demo data
sheratan seed sample --size demo

# Check statistics
sheratan db stats
```

### Daily Operations

```bash
# Ingest new documents
sheratan documents ingest ./new_docs/ --recursive

# Search for content
sheratan documents search "kubernetes deployment" --top-k 5

# Check system health
sheratan documents stats
sheratan config check
```

### Maintenance Tasks

```bash
# Re-process documents (after changing embedding model)
sheratan admin backfill

# Clean up database
sheratan admin compact

# Repair any inconsistencies
sheratan admin repair
```

### Development Workflow

```bash
# Start fresh
sheratan db reset --confirm
sheratan db init

# Load test data
sheratan seed sample --size minimal

# Test search
sheratan documents search "test query"

# Clear when done
sheratan seed clear --confirm
```

## Environment Variables

The CLI uses the following environment variables:

- `DATABASE_URL` - PostgreSQL connection string
- `GATEWAY_URL` - Gateway API URL (or `GATEWAY_HOST` + `GATEWAY_PORT`)
- `EMBEDDINGS_PROVIDER` - Embedding provider (local, openai, huggingface)
- `EMBEDDINGS_MODEL` - Model name for embeddings
- `LLM_ENABLED` - Enable LLM features (true/false)
- `GUARD_ENABLED` - Enable security guard (true/false)
- `PII_DETECTION_ENABLED` - Enable PII detection (true/false)

## Troubleshooting

### Connection Errors

If you get connection errors:
```bash
# Check configuration
sheratan config check

# Verify DATABASE_URL is set
echo $DATABASE_URL

# Verify gateway is running
curl http://localhost:8000/health
```

### Database Errors

If you get database errors:
```bash
# Reset database
sheratan db reset --confirm
sheratan db init

# Or run migrations
sheratan db migrate
```

### Import Errors

If you get import errors:
```bash
# Install dependencies
cd packages/sheratan-cli
pip install -r requirements.txt

# Also install other packages
cd ../sheratan-store && pip install -r requirements.txt
cd ../sheratan-embeddings && pip install -r requirements.txt
cd ../sheratan-guard && pip install -r requirements.txt
```
