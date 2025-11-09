import random
from dataclasses import dataclass

@dataclass
class BackoffPolicy:
    """
    Exponentielle Backoff-Strategie mit optionalem Jitter.
    attempt zählt ab 1.
    Formel: base * factor**(attempt-1) bis max_delay, dann ± jitter_range%.
    """
    base_delay: float = 2.0
    factor: float = 1.8
    max_delay: float = 60.0
    jitter: bool = True
    jitter_range: float = 0.25  # ±25%

    def next_delay(self, attempt: int) -> float:
        raw = self.base_delay * (self.factor ** max(0, attempt - 1))
        capped = min(raw, self.max_delay)
        if not self.jitter:
            return capped
        return capped * (1 + random.uniform(-self.jitter_range, self.jitter_range))
