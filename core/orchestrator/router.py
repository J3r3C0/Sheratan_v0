from dataclasses import dataclass
from typing import Literal, Optional, Dict, Any

ModelKind = Literal['llama_cpp','ollama','relay','api']

@dataclass
class RouterDecision:
    model: ModelKind
    reason: str
    policy: str

class ModelRouter:
    def __init__(self, config: Dict[str, Any]):
        self.cfg = config or {}

    def choose(self, task: Dict[str, Any]) -> RouterDecision:
        """Very small, policy-driven stub.
        Strategy: prefer local (llama_cpp/ollama), fallback to relay/api by budget/latency.
        """
        pref = self.cfg.get('preference','local_first')
        budget_ok = task.get('budget','low') in ('low','medium')
        latency_ok = task.get('latency_ms', 1000) <= self.cfg.get('max_latency_ms', 1500)

        if pref == 'local_first' and budget_ok and latency_ok:
            return RouterDecision('llama_cpp','local-first within budget','policy/local_first')
        if self.cfg.get('allow_ollama'):
            return RouterDecision('ollama','ollama allowed and selected','policy/allow_ollama')
        if self.cfg.get('allow_relay'):
            return RouterDecision('relay','relay fallback','policy/allow_relay')
        return RouterDecision('api','final fallback','policy/fallback_api')
