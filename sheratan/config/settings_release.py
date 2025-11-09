# Basic settings module to parse environment for heartbeat/lease.
# Drop-in: place as `sheratan/config/settings_release.py` or merge into your central config.
from __future__ import annotations

import os
from dataclasses import dataclass

def _read_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except Exception:
        return default

@dataclass(frozen=True)
class SheratanSettings:
    database_url: str = os.getenv("DATABASE_URL", "postgresql+psycopg2://sheratan:sheratan@localhost:5432/sheratan")
    heartbeat_interval: int = _read_int("HEARTBEAT_INTERVAL", 30)
    lease_duration: int = _read_int("LEASE_DURATION", 300)

    @property
    def as_dict(self) -> dict:
        return {
            "database_url": self.database_url,
            "heartbeat_interval": self.heartbeat_interval,
            "lease_duration": self.lease_duration,
        }

SETTINGS = SheratanSettings()