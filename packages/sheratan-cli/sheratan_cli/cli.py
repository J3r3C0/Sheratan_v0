"""CLI application for Sheratan administration"""
import click
import asyncio
from typing import Optional
import sys
import os
import json
from pathlib import Path

from .api_client import GatewayClient, run_async
from .seed_generators import (
    generate_sample_dataset,
    generate_user_query_examples,
    generate_seed_file_content
)
from .db_utils import (
    init_database,
    drop_all_tables,
    get_database_stats,
    cleanup_orphaned_chunks,
    vacuum_database,
    get_document_list,
    clear_seed_data,
    backfill_embeddings,
    run_alembic_command
)


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
    try:
        run_async(init_database())
        click.echo("✓ Database initialized successfully")
    except Exception as e:
        click.echo(f"✗ Error initializing database: {e}", err=True)
        sys.exit(1)


@db.command()
def migrate():
    """Run database migrations"""
    click.echo("Running migrations...")
    try:
        run_alembic_command("upgrade", "head")
        click.echo("✓ Migrations complete")
    except Exception as e:
        click.echo(f"✗ Error running migrations: {e}", err=True)
        sys.exit(1)


@db.command()
@click.option('--confirm', is_flag=True, help='Confirm reset')
def reset(confirm):
    """Reset database (destructive)"""
    if not confirm:
        click.echo("⚠ This will delete all data. Use --confirm to proceed.")
        return
    
    click.echo("Resetting database...")
    try:
        run_async(drop_all_tables())
        run_async(init_database())
        click.echo("✓ Database reset successfully")
    except Exception as e:
        click.echo(f"✗ Error resetting database: {e}", err=True)
        sys.exit(1)


@db.command()
def stats():
    """Show database statistics"""
    click.echo("Database Statistics")
    click.echo("=" * 40)
    try:
        stats = run_async(get_database_stats())
        click.echo(f"Documents:    {stats['documents']}")
        click.echo(f"Chunks:       {stats['chunks']}")
        click.echo(f"Searches:     {stats['searches']}")
    except Exception as e:
        click.echo(f"✗ Error getting stats: {e}", err=True)
        sys.exit(1)


@cli.group()
def seed():
    """Seed data management"""
    pass


@seed.command()
@click.option('--file', type=click.Path(exists=True), help='Seed data file (JSON)')
def load(file: Optional[str]):
    """Load seed data from file"""
    try:
        if file:
            click.echo(f"Loading seed data from {file}...")
            with open(file, 'r') as f:
                data = json.load(f)
            documents = data.get('documents', [])
        else:
            click.echo("No file specified. Use --file or try 'seed sample' for demo data.")
            return
        
        if not documents:
            click.echo("No documents found in file.")
            return
        
        # Ingest via API
        client = GatewayClient()
        response = run_async(client.ingest_documents(documents))
        
        click.echo(f"✓ Loaded {len(documents)} documents")
        click.echo(f"Document IDs: {', '.join(response.get('document_ids', []))[:100]}...")
    except Exception as e:
        click.echo(f"✗ Error loading seed data: {e}", err=True)
        sys.exit(1)


@seed.command()
@click.option('--size', type=click.Choice(['minimal', 'demo', 'full']), default='demo', help='Dataset size')
@click.option('--save', type=click.Path(), help='Save to file instead of ingesting')
def sample(size: str, save: Optional[str]):
    """Generate and load sample documents"""
    click.echo(f"Generating {size} sample dataset...")
    
    try:
        documents = generate_sample_dataset(size=size)
        click.echo(f"Generated {len(documents)} sample documents")
        
        if save:
            # Save to file
            with open(save, 'w') as f:
                json.dump({"documents": documents}, f, indent=2)
            click.echo(f"✓ Saved to {save}")
        else:
            # Ingest via API
            client = GatewayClient()
            response = run_async(client.ingest_documents(documents))
            click.echo(f"✓ Ingested {len(documents)} documents")
            click.echo(f"Document IDs: {', '.join(response.get('document_ids', []))[:100]}...")
    except Exception as e:
        click.echo(f"✗ Error generating samples: {e}", err=True)
        sys.exit(1)


@seed.command()
@click.option('--confirm', is_flag=True, help='Confirm deletion')
def clear(confirm):
    """Clear all seed data from database"""
    if not confirm:
        click.echo("⚠ This will delete all documents. Use --confirm to proceed.")
        return
    
    click.echo("Clearing seed data...")
    try:
        run_async(clear_seed_data())
        click.echo("✓ All data cleared")
    except Exception as e:
        click.echo(f"✗ Error clearing data: {e}", err=True)
        sys.exit(1)


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
    
    try:
        path_obj = Path(path)
        documents = []
        
        if path_obj.is_file():
            # Single file
            with open(path_obj, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            documents.append({
                "content": content,
                "metadata": {"filename": path_obj.name},
                "source": str(path_obj)
            })
        elif path_obj.is_dir():
            # Directory
            pattern = "**/*" if recursive else "*"
            for file_path in path_obj.glob(pattern):
                if file_path.is_file() and file_path.suffix in ['.txt', '.md', '.json']:
                    try:
                        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read()
                        documents.append({
                            "content": content,
                            "metadata": {"filename": file_path.name},
                            "source": str(file_path)
                        })
                    except Exception as e:
                        click.echo(f"Warning: Could not read {file_path}: {e}")
        
        if not documents:
            click.echo("No documents found to ingest.")
            return
        
        # Ingest via API
        client = GatewayClient()
        response = run_async(client.ingest_documents(documents))
        click.echo(f"✓ Queued {len(documents)} documents for ingestion")
    except Exception as e:
        click.echo(f"✗ Error ingesting documents: {e}", err=True)
        sys.exit(1)


@documents.command()
@click.argument('query')
@click.option('--top-k', default=5, help='Number of results')
def search(query: str, top_k: int):
    """Search documents"""
    click.echo(f"Searching for: {query}")
    click.echo("=" * 40)
    
    try:
        client = GatewayClient()
        response = run_async(client.search(query, top_k=top_k))
        
        results = response.get('results', [])
        if not results:
            click.echo("No results found.")
        else:
            for i, result in enumerate(results, 1):
                click.echo(f"\n{i}. Score: {result.get('score', 0):.3f}")
                click.echo(f"   Document ID: {result.get('document_id', 'N/A')}")
                content = result.get('content', '')
                preview = content[:200] + "..." if len(content) > 200 else content
                click.echo(f"   Content: {preview}")
                
        click.echo(f"\nTotal results: {len(results)}")
    except Exception as e:
        click.echo(f"✗ Error searching: {e}", err=True)
        sys.exit(1)


@documents.command()
def stats():
    """Show document statistics"""
    click.echo("Document Statistics")
    click.echo("=" * 40)
    
    try:
        stats = run_async(get_database_stats())
        click.echo(f"Total documents: {stats['documents']}")
        click.echo(f"Total chunks:    {stats['chunks']}")
        click.echo(f"Total searches:  {stats['searches']}")
        
        if stats['documents'] > 0 and stats['chunks'] > 0:
            avg_chunks = stats['chunks'] / stats['documents']
            click.echo(f"Avg chunks/doc:  {avg_chunks:.1f}")
    except Exception as e:
        click.echo(f"✗ Error getting stats: {e}", err=True)
        sys.exit(1)


@documents.command(name='list')
@click.option('--limit', default=10, help='Number of documents to show')
@click.option('--offset', default=0, help='Offset for pagination')
def list_documents(limit: int, offset: int):
    """List documents in database"""
    click.echo(f"Documents (limit={limit}, offset={offset})")
    click.echo("=" * 40)
    
    try:
        docs = run_async(get_document_list(limit=limit, offset=offset))
        
        if not docs:
            click.echo("No documents found.")
        else:
            for i, doc in enumerate(docs, offset + 1):
                click.echo(f"\n{i}. {doc['source'] or 'Unknown source'}")
                click.echo(f"   ID: {doc['id']}")
                click.echo(f"   Preview: {doc['content_preview']}")
                if doc['created_at']:
                    click.echo(f"   Created: {doc['created_at']}")
    except Exception as e:
        click.echo(f"✗ Error listing documents: {e}", err=True)
        sys.exit(1)


@cli.group()
def guard():
    """Security and policy management"""
    pass


@cli.group()
def admin():
    """Admin jobs and maintenance"""
    pass


@admin.command()
@click.option('--batch-size', default=100, help='Batch size for processing')
def backfill(batch_size: int):
    """Re-generate embeddings for all chunks"""
    click.echo("Starting backfill job...")
    click.echo(f"Batch size: {batch_size}")
    
    try:
        total = run_async(backfill_embeddings())
        click.echo(f"✓ Re-generated embeddings for {total} chunks")
    except Exception as e:
        click.echo(f"✗ Error during backfill: {e}", err=True)
        sys.exit(1)


@admin.command()
def compact():
    """Compact database (remove orphaned data)"""
    click.echo("Starting database compaction...")
    
    try:
        # Remove orphaned chunks
        orphaned = run_async(cleanup_orphaned_chunks())
        click.echo(f"Removed {orphaned} orphaned chunks")
        
        # Run vacuum
        click.echo("Running vacuum...")
        run_async(vacuum_database())
        
        click.echo("✓ Database compaction complete")
    except Exception as e:
        click.echo(f"✗ Error during compaction: {e}", err=True)
        sys.exit(1)


@admin.command()
def repair():
    """Repair database inconsistencies"""
    click.echo("Running database repair...")
    
    try:
        # Check for orphaned chunks
        orphaned = run_async(cleanup_orphaned_chunks())
        click.echo(f"Fixed {orphaned} orphaned chunks")
        
        # Check stats
        stats = run_async(get_database_stats())
        click.echo(f"Current state:")
        click.echo(f"  Documents: {stats['documents']}")
        click.echo(f"  Chunks: {stats['chunks']}")
        
        click.echo("✓ Database repair complete")
    except Exception as e:
        click.echo(f"✗ Error during repair: {e}", err=True)
        sys.exit(1)


@admin.command()
def vacuum():
    """Run database vacuum (PostgreSQL maintenance)"""
    click.echo("Running vacuum...")
    
    try:
        run_async(vacuum_database())
        click.echo("✓ Vacuum complete")
    except Exception as e:
        click.echo(f"✗ Error running vacuum: {e}", err=True)
        sys.exit(1)


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
