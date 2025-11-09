# Sheratan_v0 – Release Addendum (v0.1.0)

## Quickstart (Local, Docker Postgres)
```bash
# 1) Start Postgres (if docker-compose.yml exists)
docker compose up -d postgres || true

# 2) Configure environment
cp config/.env.example.additions .env  # falls noch keine .env existiert
# Passen Sie HEARTBEAT_INTERVAL und LEASE_DURATION bei Bedarf an.

# 3) DB-Migration (Alembic, falls vorhanden)
alembic upgrade head || echo "No Alembic detected; skipping"

# 4) Start Orchestrator
python -m sheratan.core.run

# 5) Cancellation-Demo (Pseudobeispiel)
python - <<'PY'
from sheratan.core import orchestrator
job_id = orchestrator.enqueue("demo.long_task", {"seconds": 120})
print("Enqueued:", job_id)
# ... nach ein paar Sekunden:
orchestrator.cancel_job(job_id)
PY
```

## Job Lifecycle: Cancel & Recovery
- **Heartbeat**: Worker senden alle `HEARTBEAT_INTERVAL` Sekunden ein Signal.
- **Lease**: Wird nach `LEASE_DURATION` Sekunden ohne Heartbeat als abgelaufen betrachtet → Recovery greift und setzt Job wieder auf `PENDING`.
- **Kooperative Cancellation**: Langer Job prüft periodisch `is_cancelled(job_id)` und verlässt sauber via Checkpoint.

Siehe außerdem: `docs/RELEASE_NOTES_v0.1.0.md`.

## Breaking Change
- Feld `metadata` wurde in `job_metadata` umbenannt. Downstream-Code bitte entsprechend anpassen.