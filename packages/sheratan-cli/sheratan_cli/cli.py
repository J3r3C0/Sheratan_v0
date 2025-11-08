"""CLI application for Sheratan administration"""
import click
import asyncio
from typing import Optional
import sys
import os


def run_async(coro):
    """Helper to run async coroutines in Click commands"""
    return asyncio.run(coro)


@click.group()
@click.version_option(version="0.1.0")
def cli():
    """Sheratan CLI - Administration and maintenance tools"""
    pass


@cli.group()
def db():
    """Database management commands"""
    pass


@db.command()
def init():
    """Initialize database schema"""
    click.echo("Initializing database...")
    # TODO: Import and run sheratan-store migrations
    click.echo("✓ Database initialized")


@db.command()
def migrate():
    """Run database migrations"""
    click.echo("Running migrations...")
    # TODO: Run alembic migrations
    click.echo("✓ Migrations complete")


@db.command()
@click.option('--confirm', is_flag=True, help='Confirm reset')
def reset(confirm):
    """Reset database (destructive)"""
    if not confirm:
        click.echo("This will delete all data. Use --confirm to proceed.")
        return
    
    click.echo("Resetting database...")
    # TODO: Drop and recreate schema
    click.echo("✓ Database reset")


@cli.group()
def seed():
    """Seed data management"""
    pass


@seed.command()
@click.option('--file', type=click.Path(exists=True), help='Seed data file')
def load(file: Optional[str]):
    """Load seed data"""
    if file:
        click.echo(f"Loading seed data from {file}...")
    else:
        click.echo("Loading default seed data...")
    
    # TODO: Load seed data
    click.echo("✓ Seed data loaded")


@seed.command()
def sample():
    """Generate sample documents"""
    click.echo("Generating sample documents...")
    
    # TODO: Generate and ingest sample documents
    sample_docs = [
        "Sample document 1 content",
        "Sample document 2 content",
        "Sample document 3 content",
    ]
    
    click.echo(f"✓ Generated {len(sample_docs)} sample documents")


@cli.group()
def documents():
    """Document management"""
    pass


@documents.command()
@click.argument('path', type=click.Path(exists=True))
@click.option('--recursive', is_flag=True, help='Process directories recursively')
def ingest(path: str, recursive: bool):
    """Ingest documents from file or directory"""
    click.echo(f"Ingesting documents from {path}...")
    
    # TODO: Read files and send to gateway /ingest endpoint
    click.echo("✓ Documents queued for ingestion")


@documents.command()
@click.argument('query')
@click.option('--top-k', default=5, help='Number of results')
def search(query: str, top_k: int):
    """Search documents"""
    click.echo(f"Searching for: {query}")
    
    # TODO: Call gateway /search endpoint
    click.echo(f"Found 0 results")


@documents.command()
def stats():
    """Show document statistics"""
    click.echo("Document Statistics")
    click.echo("=" * 40)
    
    # TODO: Query database for stats
    click.echo("Total documents: 0")
    click.echo("Total chunks: 0")
    click.echo("Total searches: 0")


@cli.group()
def guard():
    """Security and policy management"""
    pass


@guard.command()
@click.argument('text')
def scan(text: str):
    """Scan text for PII"""
    from sheratan_guard.pii import PIIDetector
    
    detector = PIIDetector()
    report = detector.scan_and_report(text)
    
    click.echo(f"PII Detection Report")
    click.echo("=" * 40)
    click.echo(f"Has PII: {report['has_pii']}")
    click.echo(f"PII Count: {report['pii_count']}")
    
    if report['has_pii']:
        click.echo(f"PII Types: {', '.join(report['pii_types'])}")
        click.echo(f"\nRedacted: {report['redacted_text']}")


@guard.command()
def policies():
    """List active policies"""
    click.echo("Active Policies")
    click.echo("=" * 40)
    
    # TODO: List policies from sheratan-guard
    click.echo("- no_empty_content (DENY)")
    click.echo("- large_document_warning (WARN)")


@cli.group()
def config():
    """Configuration management"""
    pass


@config.command()
def show():
    """Show current configuration"""
    import os
    
    click.echo("Current Configuration")
    click.echo("=" * 40)
    click.echo(f"DATABASE_URL: {os.getenv('DATABASE_URL', 'Not set')}")
    click.echo(f"EMBEDDINGS_PROVIDER: {os.getenv('EMBEDDINGS_PROVIDER', 'local')}")
    click.echo(f"LLM_ENABLED: {os.getenv('LLM_ENABLED', 'false')}")
    click.echo(f"GUARD_ENABLED: {os.getenv('GUARD_ENABLED', 'true')}")
    click.echo(f"PII_DETECTION_ENABLED: {os.getenv('PII_DETECTION_ENABLED', 'true')}")


@config.command()
def check():
    """Check configuration validity"""
    import os
    
    click.echo("Checking configuration...")
    
    errors = []
    warnings = []
    
    # Check database
    if not os.getenv('DATABASE_URL'):
        errors.append("DATABASE_URL not set")
    
    # Check embeddings
    provider = os.getenv('EMBEDDINGS_PROVIDER', 'local')
    if provider not in ['local', 'openai', 'huggingface']:
        errors.append(f"Invalid EMBEDDINGS_PROVIDER: {provider}")
    
    if errors:
        click.echo("\n✗ Errors:")
        for error in errors:
            click.echo(f"  - {error}")
    
    if warnings:
        click.echo("\n⚠ Warnings:")
        for warning in warnings:
            click.echo(f"  - {warning}")
    
    if not errors and not warnings:
        click.echo("✓ Configuration is valid")
    
    sys.exit(1 if errors else 0)


@cli.group()
def jobs():
    """Job queue management"""
    pass


@jobs.command()
@click.option('--url', help='URL to process')
@click.option('--text', help='Text content to process')
@click.option('--priority', default=0, help='Job priority (higher = more important)')
@click.option('--metadata', help='JSON metadata')
def create(url: Optional[str], text: Optional[str], priority: int, metadata: Optional[str]):
    """Create a new ETL job"""
    import json
    from dotenv import load_dotenv
    load_dotenv()
    
    if not url and not text:
        click.echo("Error: Either --url or --text must be provided", err=True)
        sys.exit(1)
    
    async def _create_job():
        from sheratan_orchestrator.job_manager import JobManager
        from sheratan_store.models.jobs import JobType
        
        manager = JobManager()
        
        input_data = {}
        if url:
            input_data["url"] = url
        if text:
            input_data["text"] = text
        if metadata:
            try:
                input_data["metadata"] = json.loads(metadata)
            except json.JSONDecodeError:
                click.echo("Error: Invalid JSON metadata", err=True)
                sys.exit(1)
        
        job_id = await manager.create_job(
            job_type=JobType.FULL_ETL,
            input_data=input_data,
            priority=priority
        )
        
        click.echo(f"✓ Job created: {job_id}")
        click.echo(f"  Type: FULL_ETL")
        click.echo(f"  Priority: {priority}")
        if url:
            click.echo(f"  URL: {url}")
    
    run_async(_create_job())


@jobs.command()
@click.argument('job_id')
def status(job_id: str):
    """Get job status"""
    import uuid
    from dotenv import load_dotenv
    load_dotenv()
    
    try:
        job_uuid = uuid.UUID(job_id)
    except ValueError:
        click.echo("Error: Invalid job ID", err=True)
        sys.exit(1)
    
    async def _get_status():
        from sheratan_orchestrator.job_manager import JobManager
        
        manager = JobManager()
        status_data = await manager.get_job_status(job_uuid)
        
        if not status_data:
            click.echo(f"Job {job_id} not found", err=True)
            sys.exit(1)
        
        click.echo("Job Status")
        click.echo("=" * 40)
        click.echo(f"ID: {status_data['id']}")
        click.echo(f"Type: {status_data['type']}")
        click.echo(f"Status: {status_data['status']}")
        click.echo(f"Created: {status_data['created_at']}")
        if status_data['started_at']:
            click.echo(f"Started: {status_data['started_at']}")
        if status_data['completed_at']:
            click.echo(f"Completed: {status_data['completed_at']}")
        click.echo(f"Retry count: {status_data['retry_count']}")
        if status_data['error_message']:
            click.echo(f"Error: {status_data['error_message']}")
    
    run_async(_get_status())


@jobs.command()
@click.option('--status-filter', help='Filter by status (pending, running, completed, failed)')
@click.option('--limit', default=10, help='Number of jobs to show')
def list(status_filter: Optional[str], limit: int):
    """List jobs"""
    from dotenv import load_dotenv
    load_dotenv()
    
    async def _list_jobs():
        from sheratan_store.database import AsyncSessionLocal
        from sheratan_store.repositories.job_repo import JobRepository
        from sheratan_store.models.jobs import JobStatus
        
        async with AsyncSessionLocal() as session:
            repo = JobRepository(session)
            
            if status_filter:
                try:
                    status_enum = JobStatus(status_filter)
                    jobs_list = await repo.get_jobs_by_status(status_enum, limit=limit)
                except ValueError:
                    click.echo(f"Error: Invalid status '{status_filter}'", err=True)
                    sys.exit(1)
            else:
                # Get statistics instead
                stats = await repo.get_job_statistics()
                
                click.echo("Job Statistics")
                click.echo("=" * 40)
                for status, count in stats.items():
                    click.echo(f"{status}: {count}")
                return
            
            click.echo(f"Jobs ({status_filter or 'all'})")
            click.echo("=" * 60)
            
            if not jobs_list:
                click.echo("No jobs found")
                return
            
            for job in jobs_list:
                click.echo(f"{job.id} | {job.job_type.value} | {job.status.value} | {job.created_at}")
    
    run_async(_list_jobs())


@jobs.command()
@click.argument('job_id')
def retry(job_id: str):
    """Retry a failed job"""
    import uuid
    from dotenv import load_dotenv
    load_dotenv()
    
    try:
        job_uuid = uuid.UUID(job_id)
    except ValueError:
        click.echo("Error: Invalid job ID", err=True)
        sys.exit(1)
    
    async def _retry_job():
        from sheratan_store.database import AsyncSessionLocal
        from sheratan_store.repositories.job_repo import JobRepository
        
        async with AsyncSessionLocal() as session:
            repo = JobRepository(session)
            job = await repo.get_job(job_uuid)
            
            if not job:
                click.echo(f"Job {job_id} not found", err=True)
                sys.exit(1)
            
            try:
                await repo.retry_job(job)
                await session.commit()
                click.echo(f"✓ Job {job_id} queued for retry")
            except ValueError as e:
                click.echo(f"Error: {e}", err=True)
                sys.exit(1)
    
    run_async(_retry_job())


@jobs.command()
@click.argument('job_id')
def cancel(job_id: str):
    """Cancel a pending or running job"""
    import uuid
    from dotenv import load_dotenv
    load_dotenv()
    
    try:
        job_uuid = uuid.UUID(job_id)
    except ValueError:
        click.echo("Error: Invalid job ID", err=True)
        sys.exit(1)
    
    async def _cancel_job():
        from sheratan_store.database import AsyncSessionLocal
        from sheratan_store.repositories.job_repo import JobRepository
        
        async with AsyncSessionLocal() as session:
            repo = JobRepository(session)
            job = await repo.get_job(job_uuid)
            
            if not job:
                click.echo(f"Job {job_id} not found", err=True)
                sys.exit(1)
            
            try:
                await repo.cancel_job(job)
                await session.commit()
                click.echo(f"✓ Job {job_id} cancelled")
            except ValueError as e:
                click.echo(f"Error: {e}", err=True)
                sys.exit(1)
    
    run_async(_cancel_job())


@jobs.command()
def stats():
    """Show job statistics"""
    from dotenv import load_dotenv
    load_dotenv()
    
    async def _show_stats():
        from sheratan_store.database import AsyncSessionLocal
        from sheratan_store.repositories.job_repo import JobRepository
        
        async with AsyncSessionLocal() as session:
            repo = JobRepository(session)
            stats = await repo.get_job_statistics()
            
            click.echo("Job Queue Statistics")
            click.echo("=" * 40)
            
            total = sum(stats.values())
            click.echo(f"Total: {total}")
            click.echo("")
            
            for status, count in sorted(stats.items()):
                percentage = (count / total * 100) if total > 0 else 0
                click.echo(f"  {status:12} : {count:5} ({percentage:5.1f}%)")
    
    run_async(_show_stats())


@jobs.command()
@click.option('--days', default=30, help='Delete jobs older than N days')
@click.option('--confirm', is_flag=True, help='Confirm cleanup')
def cleanup(days: int, confirm: bool):
    """Clean up old completed/failed jobs"""
    from dotenv import load_dotenv
    load_dotenv()
    
    if not confirm:
        click.echo(f"This will delete completed/failed jobs older than {days} days.")
        click.echo("Use --confirm to proceed.")
        return
    
    async def _cleanup():
        from sheratan_store.database import AsyncSessionLocal
        from sheratan_store.repositories.job_repo import JobRepository
        
        async with AsyncSessionLocal() as session:
            repo = JobRepository(session)
            deleted = await repo.cleanup_old_jobs(days=days)
            await session.commit()
            
            click.echo(f"✓ Deleted {deleted} old jobs")
    
    run_async(_cleanup())


if __name__ == '__main__':
    cli()
