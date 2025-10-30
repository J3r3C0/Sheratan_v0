from dataclasses import dataclass
from typing import Dict, Any

@dataclass
class Policy:
    name: str
    max_latency_ms: int = 1500
    max_cost: str = 'low'

    def allow(self, task: Dict[str, Any]) -> bool:
        cost_ok = task.get('budget','low') in ('low','medium')
        lat_ok = task.get('latency_ms', 1000) <= self.max_latency_ms
        return cost_ok and lat_ok
