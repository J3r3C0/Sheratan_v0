import os
from typing import Dict, Any
import httpx

class OllamaAdapter:
    """
    Minimal Ollama client using /api/generate.
    Config via env:
      OLLAMA_HOST (default http://localhost:11434)
      OLLAMA_MODEL (default mistral)
      OLLAMA_TIMEOUT_S (default 30)
    ""
    def __init__(self, host: str | None = None, model: str | None = None, timeout_s: float | None = None):
        self.host = (host or os.getenv('OLLAMA_HOST') or 'http://localhost:11434').rstrip('/')
        self.model = model or os.getenv('OLLAMA_MODEL') or 'mistral'
        self.timeout_s = float(timeout_s or os.getenv('OLLAMA_TIMEOUT_S') or 30)

    def generate(self, prompt: str, **opts) -> Dict[str, Any]:
        url = f"{self.host}/api/generate"
        payload = {"model": self.model, "prompt": prompt, "stream": False} | opts
        try:
            with httpx.Client(timeout=self.timeout_s) as client:
                r = client.post(url, json=payload)
                r.raise_for_status()
                data = r.json()
                return {
                    "ok": True,
                    "model": f"ollama:{data.get('model', self.model)}",
                    "response": data.get('response'),
                    "raw": data,
                }
        except Exception as e:
            return {"ok": False, "error": str(e), "model": f"ollama:{self.model}"}
