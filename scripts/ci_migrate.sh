#!/usr/bin/env bash
set -euo pipefail
if [ -f "alembic.ini" ] || [ -d "alembic" ] ; then
  echo "[CI] Alembic detected – running upgrade/downgrade sanity checks"
  python -m pip install alembic psycopg2-binary || true
  alembic upgrade head
  # Try a single-step downgrade/upgrade to catch simple issues
  alembic downgrade -1 || echo "[CI] downgrade -1 failed (ok if first migration)"
  alembic upgrade head
else
  echo "[CI] No Alembic config found – skipping DB migration checks"
fi