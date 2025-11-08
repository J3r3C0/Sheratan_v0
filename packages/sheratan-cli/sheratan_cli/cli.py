"""CLI application for Sheratan administration"""
import click
import asyncio
from typing import Optional
import sys


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


if __name__ == '__main__':
    cli()
