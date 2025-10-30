from fastapi import FastAPI
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

from core.orchestrator.router import ModelRouter
from core.orchestrator.policies import Policy
from core.orchestrator.tools import ToolRegistry
from core.memory.vector import InMemoryVS

app = FastAPI(title="Sheratan API", version="0.1.0")

# ---- Minimal in-process singletons (stub) ----
router = ModelRouter(config={"preference": "local_first", "allow_ollama": True, "allow_relay": True, "max_latency_ms": 1500})
policy = Policy(name="default")
vs = InMemoryVS()
reg = ToolRegistry()
reg.register('echo', lambda p: { 'ok': True, 'payload': p })

class Job(BaseModel):
    id: str
    kind: str
    payload: Dict[str, Any] = Field(default_factory=dict)
    tools: Optional[List[str]] = None
    budget: Optional[str] = Field(default="low")
    latency_ms: Optional[int] = Field(default=1000)

class MemoryQuery(BaseModel):
    text: str
    top_k: int = 5

class ToolCall(BaseModel):
    name: str
    payload: Dict[str, Any] = Field(default_factory=dict)

@app.get('/health')
def health():
    return {"status": "ok", "api": "sheratan", "version": app.version}

@app.post('/router/decide')
def router_decide(job: Job):
    if not policy.allow(job.dict()):
        return {"decision": None, "reason": "policy_reject"}
    d = router.choose(job.dict())
    return {"decision": d.model, "reason": d.reason, "policy": d.policy}

@app.post('/memory/add/{doc_id}')
def memory_add(doc_id: str, q: MemoryQuery):
    vs.add(doc_id, q.text)
    return {"ok": True, "doc_id": doc_id}

@app.post('/memory/query')
def memory_query(q: MemoryQuery):
    return {"matches": vs.query(q.text, q.top_k)}

@app.post('/tools/run')
def tools_run(call: ToolCall):
    return reg.run(call.name, call.payload)
