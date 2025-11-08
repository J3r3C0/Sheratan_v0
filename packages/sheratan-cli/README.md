# Sheratan CLI

Command-line interface for Sheratan administration and maintenance.

## Installation

```bash
pip install -r requirements.txt
```

## Usage

```bash
# Show help
python -m sheratan_cli.cli --help

# Database commands
python -m sheratan_cli.cli db init        # Initialize database
python -m sheratan_cli.cli db migrate     # Run migrations
python -m sheratan_cli.cli db reset --confirm  # Reset database

# Seed data
python -m sheratan_cli.cli seed load      # Load seed data
python -m sheratan_cli.cli seed sample    # Generate sample documents

# Document management
python -m sheratan_cli.cli documents ingest ./data    # Ingest documents
python -m sheratan_cli.cli documents search "query"   # Search documents
python -m sheratan_cli.cli documents stats            # Show statistics

# Security/Guard
python -m sheratan_cli.cli guard scan "text with PII"  # Scan for PII
python -m sheratan_cli.cli guard policies              # List policies

# Configuration
python -m sheratan_cli.cli config show    # Show current config
python -m sheratan_cli.cli config check   # Validate config
```

## Commands

### Database Management (`db`)
- `init` - Initialize database schema
- `migrate` - Run database migrations
- `reset` - Reset database (destructive, requires --confirm)

### Seed Data (`seed`)
- `load` - Load seed data from file
- `sample` - Generate sample documents

### Document Management (`documents`)
- `ingest PATH` - Ingest documents from file or directory
- `search QUERY` - Search documents
- `stats` - Show document statistics

### Security (`guard`)
- `scan TEXT` - Scan text for PII
- `policies` - List active policies

### Configuration (`config`)
- `show` - Show current configuration
- `check` - Validate configuration

## Examples

```bash
# Initialize database
python -m sheratan_cli.cli db init

# Load sample data
python -m sheratan_cli.cli seed sample

# Ingest directory of documents
python -m sheratan_cli.cli documents ingest ./my_docs --recursive

# Search
python -m sheratan_cli.cli documents search "machine learning"

# Check for PII
python -m sheratan_cli.cli guard scan "Contact: john@example.com"

# Validate configuration
python -m sheratan_cli.cli config check
```
