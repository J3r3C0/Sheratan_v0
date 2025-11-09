"""
Sheratan Orchestrator package
Lightweight orchestration utilities and PoC helpers (logbook, lease, etc.).
"""

__version__ = "0.1.0"

# Public API re-exports for convenience
from .logbook import Logbook  # noqa: F401
from .lease import LeaseState  # noqa: F401

# If available in your tree, expose the JobManager as well
try:  # pragma: no cover
    from .job_manager import JobManager  # noqa: F401
except Exception:
    JobManager = None  # type: ignore

__all__ = [
    "Logbook",
    "LeaseState",
    "JobManager",
]
