import asyncio
import json
import time
from collections import deque
from typing import Any, Deque, Dict, Optional

class Logbook:
    """
    Internes, strukturiertes Logbuch mit:
    - Ringpuffer (in-memory) für Nachvollziehbarkeit
    - Optionalem Stream (stdout oder eigener Writer) für PoC
    """
    def __init__(self, maxlen: int = 1000):
        self._buffer: Deque[Dict[str, Any]] = deque(maxlen=maxlen)
        self._stream_queue: Optional[asyncio.Queue] = None
        self._stream_task: Optional[asyncio.Task] = None
        self._stream_writer = None

    def _now(self) -> float:
        return time.time()

    def _event(
        self,
        event: str,
        level: str = "INFO",
        worker_id: Optional[str] = None,
        job_id: Optional[int] = None,
        message: Optional[str] = None,
        **details: Any,
    ) -> Dict[str, Any]:
        return {
            "ts": self._now(),
            "level": level,
            "event": event,
            "worker_id": worker_id,
            "job_id": job_id,
            "message": message,
            **({"details": details} if details else {}),
        }

    def append(self, ev: Dict[str, Any]) -> None:
        self._buffer.append(ev)
        if self._stream_queue is not None:
            try:
                self._stream_queue.put_nowait(ev)
            except asyncio.QueueFull:
                # If the stream queue is full, drop the event.
                # This is intentional: the logbook is best-effort and should not block or raise.
                pass

    # Convenience-APIs für typische Events
    def job_started(self, worker_id: str, job_id: int, reason: Optional[str] = None, **kw):
        self.append(self._event("JobStarted", "INFO", worker_id, job_id, reason, **kw))

    def action_started(self, worker_id: str, job_id: int, action: str, reason: Optional[str] = None, **kw):
        self.append(self._event("ActionStarted", "INFO", worker_id, job_id, f"{action}", action=action, reason=reason, **kw))

    def heartbeat(self, worker_id: str, job_id: int, lease_expires_at: Optional[str] = None, **kw):
        self.append(self._event("Heartbeat", "DEBUG", worker_id, job_id, None, lease_expires_at=lease_expires_at, **kw))

    def cancel_requested(self, worker_id: Optional[str], job_id: int, by: str, **kw):
        self.append(self._event("CancelRequested", "INFO", worker_id, job_id, f"by={by}", requested_by=by, **kw))

    def job_cancelled(self, worker_id: Optional[str], job_id: int, **kw):
        self.append(self._event("JobCancelled", "INFO", worker_id, job_id, None, **kw))

    def recovery_attempt(self, worker_id: Optional[str], job_id: int, reason: str, attempt: int, **kw):
        self.append(self._event("RecoveryAttempt", "WARN", worker_id, job_id, reason, attempt=attempt, **kw))

    def recovery_outcome(self, worker_id: Optional[str], job_id: int, outcome: str, **kw):
        self.append(self._event("RecoveryOutcome", "INFO", worker_id, job_id, outcome, outcome=outcome, **kw))

    def job_completed(self, worker_id: str, job_id: int, outcome: str = "SUCCEEDED", runtime_seconds: Optional[float] = None, **kw):
        self.append(self._event("JobCompleted", "INFO", worker_id, job_id, outcome, outcome=outcome, runtime_seconds=runtime_seconds, **kw))

    def heartbeat_stopped(self, worker_id: str, job_id: int, **kw):
        self.append(self._event("HeartbeatStopped", "DEBUG", worker_id, job_id, None, **kw))

    def error(self, worker_id: Optional[str], job_id: Optional[int], message: str, **kw):
        self.append(self._event("Error", "ERROR", worker_id, job_id, message, **kw))

    # NEU: Lease-bezogene Events
    def lease_renewed(self, worker_id: str, job_id: int, lease_expires_at: str, **kw):
        self.append(self._event("LeaseRenewed", "DEBUG", worker_id, job_id, None, lease_expires_at=lease_expires_at, **kw))

    def lease_expired(self, worker_id: str, job_id: int, expired_at: str, grace_applied_seconds: Optional[float] = None, **kw):
        self.append(self._event("LeaseExpired", "WARN", worker_id, job_id, None, expired_at=expired_at, grace_applied_seconds=grace_applied_seconds, **kw))

    # NEU: Laufzeit-/Runtime-Event (periodische Statusmeldung)
    def runtime(self, worker_id: str, job_id: int, runtime_seconds: float, phase: Optional[str] = None, **kw):
        self.append(self._event("RunTime", "INFO", worker_id, job_id, None, runtime_seconds=round(runtime_seconds, 3), phase=phase, **kw))

    # Ringpuffer Snapshot (intern nutzbar)
    def snapshot(self):
        return list(self._buffer)

    # PoC: Stream aktivieren/deaktivieren
    async def start_stream(self, writer=None, queue_maxsize: int = 1000):
        if self._stream_task is not None:
            return
        self._stream_queue = asyncio.Queue(maxsize=queue_maxsize)
        self._stream_writer = writer or self._default_writer
        self._stream_task = asyncio.create_task(self._run_streamer())

    async def stop_stream(self):
        if self._stream_task is not None:
            self._stream_task.cancel()
            try:
                await self._stream_task
            except asyncio.CancelledError:
                # Task cancellation is expected here; ignore the exception.
                pass
        self._stream_task = None
        self._stream_queue = None
        self._stream_writer = None

    async def _run_streamer(self):
        assert self._stream_queue is not None
        while True:
            ev = await self._stream_queue.get()
            try:
                self._stream_writer(ev)
            except Exception as e:
                print(json.dumps({"ts": self._now(), "level": "ERROR", "event": "StreamWriteFailed", "message": str(e)}), flush=True)

    @staticmethod
    def _default_writer(ev: Dict[str, Any]):
        print(json.dumps(ev, separators=(",", ":"), ensure_ascii=False), flush=True)
