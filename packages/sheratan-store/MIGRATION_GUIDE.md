# Migration Guide - Sheratan Store

This guide explains how to set up and manage the database schema for the Sheratan system.

## Prerequisites

1. **PostgreSQL 16** installed and running
2. **pgvector extension** installed
3. **Python 3.11+** with all dependencies installed

## Initial Setup

### 1. Install pgvector Extension

#### On Ubuntu/Debian:
```bash
sudo apt-get update
sudo apt-get install postgresql-16-pgvector
```

#### On macOS (Homebrew):
```bash
brew install pgvector
```

#### On Windows:
Download from https://github.com/pgvector/pgvector/releases

### 2. Create Database

```sql
CREATE DATABASE sheratan;
CREATE USER sheratan WITH PASSWORD 'sheratan';
GRANT ALL PRIVILEGES ON DATABASE sheratan TO sheratan;
```

### 3. Enable pgvector Extension

Connect to the database:
```bash
psql -U sheratan -d sheratan
```

Enable the extension:
```sql
CREATE EXTENSION IF NOT EXISTS vector;
\q
```

### 4. Configure Environment Variables

Create `.env` file in the project root:
```env
DATABASE_URL=postgresql://sheratan:sheratan@localhost:5432/sheratan
VECTOR_DIMENSION=384  # Must match your embedding model
```

**Important:** The `VECTOR_DIMENSION` must match your embedding model:
- `all-MiniLM-L6-v2`: 384 dimensions (default)
- `all-mpnet-base-v2`: 768 dimensions
- `text-embedding-ada-002`: 1536 dimensions

### 5. Run Initial Migration

```bash
cd packages/sheratan-store
alembic upgrade head
```

This will:
- Create all database tables
- Set up indexes
- Configure vector columns
- Enable foreign key constraints

## Verifying the Setup

### Check Tables

```sql
\dt
```

You should see:
- `documents`
- `document_chunks`
- `jobs`
- `audit_logs`
- `search_logs`
- `alembic_version`

### Check pgvector Extension

```sql
SELECT * FROM pg_extension WHERE extname = 'vector';
```

### Verify Vector Dimension

```sql
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'document_chunks' AND column_name = 'embedding';
```

### Check Indexes

```sql
SELECT indexname, indexdef 
FROM pg_indexes 
WHERE tablename IN ('documents', 'document_chunks', 'jobs', 'audit_logs', 'search_logs')
ORDER BY tablename, indexname;
```

## Schema Overview

### Tables

1. **documents**
   - Stores full document content and metadata
   - Tracks source and timestamps
   - Indexed on: created_at, source

2. **document_chunks**
   - Stores document chunks with vector embeddings
   - Links to parent document with CASCADE delete
   - Indexed on: document_id, embedding (IVFFlat)

3. **jobs**
   - Background job queue with priority
   - Tracks job lifecycle (pending → running → completed/failed)
   - Indexed on: status, job_type, created_at, priority

4. **audit_logs**
   - Security and compliance audit trail
   - Tracks user actions and resource access
   - Indexed on: created_at, event_type, user_id, resource

5. **search_logs**
   - Search analytics and performance metrics
   - Tracks queries and results
   - Indexed on: created_at

### Indexes

#### B-Tree Indexes (Standard)
- Fast lookups for exact matches and ranges
- Used for: IDs, timestamps, status fields

#### IVFFlat Index (Vector Search)
- Approximate nearest neighbor search
- Used for: vector similarity search
- Trade-off: Speed vs accuracy

The IVFFlat index uses cosine distance for similarity:
```sql
CREATE INDEX idx_chunks_embedding 
ON document_chunks 
USING ivfflat (embedding vector_cosine_ops);
```

## Migration Management

### Check Current Version

```bash
alembic current
```

### View Migration History

```bash
alembic history --verbose
```

### Create New Migration

After modifying models:
```bash
alembic revision --autogenerate -m "Description of changes"
```

Review the generated migration file before applying!

### Apply Migrations

```bash
# Apply all pending migrations
alembic upgrade head

# Apply one migration at a time
alembic upgrade +1

# Apply to specific revision
alembic upgrade <revision_id>
```

### Rollback Migrations

```bash
# Rollback one migration
alembic downgrade -1

# Rollback to specific revision
alembic downgrade <revision_id>

# Rollback all migrations
alembic downgrade base
```

## Troubleshooting

### Issue: pgvector extension not found

**Error:** `ERROR: could not open extension control file`

**Solution:**
1. Install pgvector for your PostgreSQL version
2. Restart PostgreSQL service
3. Verify installation: `SELECT * FROM pg_available_extensions WHERE name = 'vector';`

### Issue: IVFFlat index creation fails

**Error:** `ERROR: index creation failed`

**Cause:** IVFFlat requires data to build the index

**Solution:**
1. Create tables without the index first
2. Insert some sample data (at least 100 rows recommended)
3. Create the index manually:
```sql
CREATE INDEX idx_chunks_embedding 
ON document_chunks 
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);
```

### Issue: Vector dimension mismatch

**Error:** `ERROR: expected 384 dimensions, not 768`

**Cause:** Changing VECTOR_DIMENSION after table creation

**Solution:**
1. This cannot be fixed with migrations
2. You must either:
   - Drop and recreate the table
   - Create a new migration to alter the column type
   - Start with a fresh database

**Prevention:** Set VECTOR_DIMENSION correctly from the start!

### Issue: Connection pool exhausted

**Error:** `asyncpg.exceptions.TooManyConnectionsError`

**Solution:**
Increase pool size in environment:
```env
DB_POOL_SIZE=20
DB_MAX_OVERFLOW=30
```

### Issue: Foreign key constraint violations

**Error:** `ERROR: update or delete on table "documents" violates foreign key constraint`

**Cause:** Trying to delete a document that has chunks

**Solution:** The schema uses CASCADE delete, so this shouldn't happen. If it does:
1. Check that the foreign key was created correctly:
```sql
SELECT conname, conrelid::regclass, confrelid::regclass 
FROM pg_constraint 
WHERE contype = 'f' AND conrelid = 'document_chunks'::regclass;
```
2. If missing, add it:
```sql
ALTER TABLE document_chunks 
ADD CONSTRAINT fk_document_chunks_document 
FOREIGN KEY (document_id) 
REFERENCES documents(id) 
ON DELETE CASCADE;
```

## Best Practices

### 1. Backup Before Migrations

```bash
pg_dump -U sheratan sheratan > backup_$(date +%Y%m%d_%H%M%S).sql
```

### 2. Test Migrations in Development

Always test migrations on a development database first:
```bash
# Development
DATABASE_URL=postgresql://sheratan:sheratan@localhost:5432/sheratan_dev alembic upgrade head

# Production (only after testing)
DATABASE_URL=postgresql://sheratan:sheratan@localhost:5432/sheratan alembic upgrade head
```

### 3. Review Auto-Generated Migrations

Always review migrations created with `--autogenerate`:
- Check for unintended changes
- Verify data migrations if needed
- Add data transformations manually if required

### 4. Keep Migrations Small

Create separate migrations for:
- Schema changes (adding/modifying tables)
- Index changes
- Data migrations
- Permission changes

### 5. Document Complex Migrations

Add comments to migration files explaining:
- Why the change was made
- What data transformations occur
- Any manual steps required

## Performance Tuning

### IVFFlat Index Tuning

The `lists` parameter affects query performance:
```sql
-- More lists = faster search, more memory
CREATE INDEX idx_chunks_embedding 
ON document_chunks 
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);  -- Adjust based on data size
```

Rule of thumb: `lists = rows / 1000`

### Monitoring Index Usage

```sql
SELECT 
    schemaname, tablename, indexname, 
    idx_scan, idx_tup_read, idx_tup_fetch
FROM pg_stat_user_indexes
WHERE schemaname = 'public'
ORDER BY idx_scan;
```

### Vacuum and Analyze

Regular maintenance:
```sql
-- After bulk inserts
VACUUM ANALYZE document_chunks;

-- Check table statistics
SELECT * FROM pg_stat_user_tables WHERE relname = 'document_chunks';
```

## Security Considerations

### 1. Use Strong Passwords

Never use default passwords in production!

### 2. Limit Database Access

```sql
-- Create read-only user for reporting
CREATE USER sheratan_readonly WITH PASSWORD 'secure_password';
GRANT CONNECT ON DATABASE sheratan TO sheratan_readonly;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO sheratan_readonly;
```

### 3. Enable SSL Connections

In production, use SSL:
```env
DATABASE_URL=postgresql://sheratan:sheratan@localhost:5432/sheratan?sslmode=require
```

### 4. Audit Log Retention

Set up automated cleanup:
```python
# In a scheduled job
from sheratan_store import AuditLogRepository

async def cleanup_old_audits():
    async with get_db() as db:
        repo = AuditLogRepository(db)
        deleted = await repo.cleanup_old_logs(days=90)
        print(f"Deleted {deleted} old audit logs")
```

## Additional Resources

- PostgreSQL Documentation: https://www.postgresql.org/docs/16/
- pgvector Documentation: https://github.com/pgvector/pgvector
- Alembic Documentation: https://alembic.sqlalchemy.org/
- SQLAlchemy Documentation: https://docs.sqlalchemy.org/
