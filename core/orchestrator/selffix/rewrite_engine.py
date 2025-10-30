from dataclasses import dataclass
from typing import Dict, Any

@dataclass
class RewriteProposal:
    idea: str
    score: float

class RewriteEngine:
    def propose(self, context: Dict[str, Any]) -> RewriteProposal:
        # Minimal Platzhalter: stubbed heuristic
        idea = 'reduce token usage; tighten tool calls'
        score = 0.6
        return RewriteProposal(idea, score)
