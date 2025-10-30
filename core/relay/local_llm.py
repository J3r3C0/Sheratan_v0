from typing import Dict, Any, Optional

class LlamaCppAdapter:
    def __init__(self, model_path: str, **kw):
        self.model_path = model_path
        self.kw = kw
        # defer heavy imports; real impl would import llama_cpp

    def generate(self, prompt: str, **opts) -> Dict[str, Any]:
        # placeholder response
        return {"model": "llama_cpp", "ok": True, "prompt": prompt, "opts": opts}

class OllamaAdapter:
    def __init__(self, model: str = 'mistral', host: str = 'http://localhost:11434'):
        self.model = model
        self.host = host
        # real impl: requests/httpx to POST /api/generate

    def generate(self, prompt: str, **opts) -> Dict[str, Any]:
        return {"model": f"ollama:{self.model}", "ok": True, "prompt": prompt, "opts": opts}
