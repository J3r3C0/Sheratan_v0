# Sheratan v0 - RAG/ETL Monorepo

Sheratan ist ein modulares RAG (Retrieval-Augmented Generation) und ETL (Extract, Transform, Load) System, das als Monorepo organisiert ist.

## Architektur

Das System basiert auf Python mit PostgreSQL 16 + pgvector und ist in folgende Pakete unterteilt:

### Pakete

- **sheratan-gateway**: FastAPI REST-Endpunkte für `/ingest`, `/search`, `/answer`
- **sheratan-orchestrator**: Worker für Crawling, Chunking und Embedding
- **sheratan-embeddings**: Lokale CPU-basierte Embeddings mit Provider-Switch über ENV
- **sheratan-store**: Datenbank-Migrationen und Repositories (Postgres + pgvector)
- **sheratan-guard**: Policy-Engine, PII-Schutz und Audit-Logging
- **sheratan-cli**: Admin-Tools und Seed-Daten

## Technologie-Stack

- **Backend**: Python 3.11+
- **API Framework**: FastAPI
- **Datenbank**: PostgreSQL 16 mit pgvector-Extension
- **Embeddings**: Lokal (CPU), konfigurierbar über Umgebungsvariablen
- **LLM**: Extern (standardmäßig deaktiviert, ENV-gesteuert)

## Quick Start

### Voraussetzungen

- Python 3.11+
- PostgreSQL 16 mit pgvector
- Docker & Docker Compose (optional)

### Installation

```bash
# Clone repository
git clone https://github.com/J3r3C0/Sheratan_v0.git
cd Sheratan_v0

# Virtual environment erstellen
python -m venv venv
source venv/bin/activate  # Linux/Mac
# oder
venv\Scripts\activate  # Windows

# Dependencies installieren
pip install -r requirements.txt
```

### Umgebungsvariablen

Erstellen Sie eine `.env` Datei im Root-Verzeichnis:

```env
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/sheratan
PGVECTOR_ENABLED=true

# Embeddings
EMBEDDINGS_PROVIDER=local  # local, openai, huggingface
EMBEDDINGS_MODEL=all-MiniLM-L6-v2

# LLM (optional, standardmäßig deaktiviert)
LLM_ENABLED=false
LLM_PROVIDER=openai
LLM_API_KEY=

# Gateway
GATEWAY_HOST=0.0.0.0
GATEWAY_PORT=8000

# Security
GUARD_ENABLED=true
PII_DETECTION_ENABLED=true
```

### Mit Docker starten

```bash
docker-compose up -d
```

### Manuell starten

```bash
# Datenbank-Migrationen
cd packages/sheratan-store
python -m alembic upgrade head

# Gateway starten
cd packages/sheratan-gateway
uvicorn sheratan_gateway.app:app --host 0.0.0.0 --port 8000

# Orchestrator starten (in separatem Terminal)
cd packages/sheratan-orchestrator
python -m sheratan_orchestrator.worker
```

## Entwicklung

### Projekt-Struktur

```
Sheratan_v0/
├── packages/
│   ├── sheratan-gateway/       # REST API
│   ├── sheratan-orchestrator/  # Background Workers
│   ├── sheratan-embeddings/    # Embedding Services
│   ├── sheratan-store/         # Database Layer
│   ├── sheratan-guard/         # Security & Policies
│   └── sheratan-cli/           # CLI Tools
├── .env.example                # Beispiel-Konfiguration
├── docker-compose.yml          # Docker Setup
├── requirements.txt            # Root Dependencies
└── README.md
```

### Tests ausführen

```bash
# Alle Tests
pytest

# Spezifisches Paket
cd packages/sheratan-gateway
pytest
```

## API Dokumentation

Nach dem Start der Gateway unter `http://localhost:8000/docs` verfügbar (Swagger UI).

### Hauptendpunkte

- `POST /ingest` - Dokumente indexieren
- `POST /search` - Semantische Suche
- `POST /answer` - RAG-basierte Antwortgenerierung

## Lizenz

[Lizenz noch festzulegen]

## Kontakt

J3r3C0 - GitHub: [@J3r3C0](https://github.com/J3r3C0)
