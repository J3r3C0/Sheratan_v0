import asyncio
import time
from datetime import datetime, timezone

# Versuche Paket-Import (nach Installation). Fallback: direkt aus Repo-Struktur.
try:
    from sheratan_orchestrator.logbook import Logbook
    from sheratan_orchestrator.lease import LeaseState
except ImportError:
    import os, sys
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "packages", "sheratan-orchestrator"))
    if repo_root not in sys.path:
        sys.path.insert(0, repo_root)
    from sheratan_orchestrator.logbook import Logbook
    from sheratan_orchestrator.lease import LeaseState

# Repo-Stub: nur für PoC; in realer Umgebung tatsächliche Repo-Funktionen injizieren
class RepoStub:
    def __init__(self):
        self.cancel_set = set()

    async def check_cancellation_requested(self, job_id: int) -> bool:
        await asyncio.sleep(0)  # yield
        return job_id in self.cancel_set

def iso_utc(ts: float) -> str:
    return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()

async def heartbeat_loop(job_id: int, worker_id: str, interval: float, stop_evt: asyncio.Event, log: Logbook, lease: LeaseState):
    """
    Sendet regelmäßige Heartbeats (DEBUG) und erneuert die Lease (LeaseRenewed).
    """
    while not stop_evt.is_set():
        # Heartbeat-Event
        log.heartbeat(worker_id, job_id, lease_expires_at=iso_utc(lease.lease_expires_at))
        # Lease erneuern
        new_expiry = lease.renew()
        log.lease_renewed(worker_id, job_id, lease_expires_at=iso_utc(new_expiry))
        try:
            await asyncio.wait_for(stop_evt.wait(), timeout=interval)
        except asyncio.TimeoutError:
            continue
    log.heartbeat_stopped(worker_id, job_id)

async def lease_monitor(job_id: int, worker_id: str, stop_evt: asyncio.Event, log: Logbook, lease: LeaseState):
    """
    Beobachtet das Lease-Expiry und loggt LeaseExpired, sobald abgelaufen (+ optionaler Grace).
    """
    expired_logged = False
    while not stop_evt.is_set():
        await asyncio.sleep(0.2)
        if lease.expired() and not expired_logged:
            log.lease_expired(worker_id=None, job_id=job_id, expired_at=iso_utc(lease.lease_expires_at), grace_applied_seconds=0.0)
            expired_logged = True
        # Optional: nach Grace nochmal gesondert loggen
        if lease.expired_with_grace():
            pass

async def runtime_ticker(job_id: int, worker_id: str, start_ts: float, stop_evt: asyncio.Event, log: Logbook, period: float = 2.0, phase: str = "FullETL"):
    while not stop_evt.is_set():
        await asyncio.sleep(period)
        runtime = time.time() - start_ts
        log.runtime(worker_id, job_id, runtime_seconds=runtime, phase=phase)

async def run_job(job_id: int, worker_id: str, repo: RepoStub, log: Logbook, duration: float = 8.0):
    start = time.time()
    log.job_started(worker_id, job_id)
    log.action_started(worker_id, job_id, action="FullETL")

    # Runtime ticker
    stop_evt = asyncio.Event()
    ticker = asyncio.create_task(runtime_ticker(job_id, worker_id, start, stop_evt, log, period=2.0, phase="FullETL"))

    try:
        while time.time() - start < duration:
            await asyncio.sleep(0.5)
            if await repo.check_cancellation_requested(job_id):
                log.cancel_requested(worker_id=None, job_id=job_id, by="operator")
                raise asyncio.CancelledError()
        log.job_completed(worker_id, job_id, outcome="SUCCEEDED", runtime_seconds=(time.time() - start))
    except asyncio.CancelledError:
        log.job_cancelled(worker_id=None, job_id=job_id)
        raise
    finally:
        stop_evt.set()
        await ticker

async def main():
    worker_id = "worker-1"
    job_id = 42

    # PoC-Parameter
    heartbeat_interval = 1.0
    lease_duration = 5.0
    lease_grace = 2.0
    job_duration = 8.0

    log = Logbook(maxlen=2000)
    await log.start_stream()  # PoC: Stream einschalten

    repo = RepoStub()
    hb_stop_evt = asyncio.Event()

    # Lease-Start
    lease = LeaseState.start(lease_duration_seconds=lease_duration, grace_period_seconds=lease_grace)

    # Tasks
    hb_task = asyncio.create_task(heartbeat_loop(job_id, worker_id, heartbeat_interval, hb_stop_evt, log, lease))
    lm_task = asyncio.create_task(lease_monitor(job_id, worker_id, hb_stop_evt, log, lease))
    job_task = asyncio.create_task(run_job(job_id, worker_id, repo, log, duration=job_duration))

    # Simuliere Cancel nach 3 Sekunden
    await asyncio.sleep(3)
    repo.cancel_set.add(job_id)

    try:
        await job_task
    except asyncio.CancelledError:
        # Job abgebrochen → Heartbeat stoppen → Lease läuft weiter aus (Monitor zeigt ggf. Expiry)
        pass

    hb_stop_evt.set()
    await asyncio.gather(hb_task, lm_task, return_exceptions=True)
    await log.stop_stream()

if __name__ == "__main__":
    asyncio.run(main())
