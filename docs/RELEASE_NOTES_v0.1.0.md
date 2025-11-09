# Sheratan v0 – Release Notes v0.1.0 (2025-11-09)

## Added
- Cooperative Job Cancellation (Checkpoints, sauberes Cleanup)
- Heartbeat/Lease-Mechanismus (Zombie-Erkennung, Auto-Recovery)
- DB-Felder: `worker_id`, `heartbeat_at`, `lease_expires_at` (+ Migration)
- Dokumentation: Cancel/Recovery Basics
- Test-Skeleton für Lease/Cancellation

## Changed
- `metadata` → `job_metadata` (Breaking – Downstream anpassen)

## Ops
- HEARTBEAT_INTERVAL (default 30 s) & LEASE_DURATION (default 300 s) via Env konfigurierbar.