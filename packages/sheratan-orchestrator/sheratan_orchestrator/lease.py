import time
from dataclasses import dataclass

@dataclass
class LeaseState:
    lease_duration_seconds: float
    grace_period_seconds: float
    lease_expires_at: float  # epoch seconds

    @classmethod
    def start(cls, lease_duration_seconds: float, grace_period_seconds: float):
        now = time.time()
        return cls(
            lease_duration_seconds=lease_duration_seconds,
            grace_period_seconds=grace_period_seconds,
            lease_expires_at=now + lease_duration_seconds,
        )

    def renew(self):
        # Konservativ: erneuert Lease relativ zu jetzt (now + duration)
        self.lease_expires_at = time.time() + self.lease_duration_seconds
        return self.lease_expires_at

    def expired(self) -> bool:
        return time.time() > self.lease_expires_at

    def expired_with_grace(self) -> bool:
        return time.time() > (self.lease_expires_at + self.grace_period_seconds)
