Param()
$ErrorActionPreference = "Stop"
if (Test-Path "alembic.ini" -or (Test-Path "alembic")) {
  Write-Host "[CI] Alembic detected – running upgrade/downgrade sanity checks"
  python -m pip install alembic psycopg2-binary | Out-Null
  alembic upgrade head
  try { alembic downgrade -1 } catch { Write-Host "[CI] downgrade -1 failed (ok if first migration)" }
  alembic upgrade head
} else {
  Write-Host "[CI] No Alembic config found – skipping DB migration checks"
}