from dataclasses import dataclass
from typing import Dict, Any, List

@dataclass
class CodingPlan:
    files: List[Dict[str, Any]]  # [{path, task, deps?}]

class CodingAgent:
    def __init__(self, router):
        self.router = router

    def analyze(self, prompt: str) -> CodingPlan:
        # stub: one file
        return CodingPlan(files=[{"path": "demo/hello.py", "task": "print('hello')"}])

    def generate(self, plan: CodingPlan) -> Dict[str, str]:
        # stub: produce content map
        return {f["path"]: f"# generated
{f['task']}" for f in plan.files}

    def review(self, contents: Dict[str, str]) -> Dict[str, Any]:
        # stub review
        return {"ok": True, "notes": []}
