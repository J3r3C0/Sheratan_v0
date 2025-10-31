from fastapi import APIRouter
from pydantic import BaseModel
from typing import Dict, Any

from core.agents.coding_agent.agent import CodingAgent
from core.orchestrator.router import ModelRouter
from core.orchestrator.policies import Policy

router = APIRouter(prefix='/agents', tags=['agents'])

# In a future step these would be injected
_router = ModelRouter(config={
    'preference': 'local_first',
    'allow_ollama': True,
    'allow_relay': True,
    'max_latency_ms': 1500,
})
_policy = Policy(name='default')

class CodingRequest(BaseModel):
    prompt: str

@router.post('/coding')
def run_coding_agent(req: CodingRequest) -> Dict[str, Any]:
    # basic policy guard (could inspect prompt length, budget, etc.)
    if not _policy.allow({'budget': 'low', 'latency_ms': 800}):
        return {'ok': False, 'reason': 'policy_reject'}

    agent = CodingAgent(_router)
    plan = agent.analyze(req.prompt)
    files = agent.generate(plan)
    review = agent.review(files)
    return {
        'ok': True,
        'plan': plan.__dict__,
        'files': files,
        'review': review,
    }
