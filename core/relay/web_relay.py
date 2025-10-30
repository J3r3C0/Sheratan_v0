from typing import Dict, Any
import httpx

class WebRelayAdapter:
    def __init__(self, endpoint: str, api_key: str | None = None, timeout: float = 30.0):
        self.endpoint = endpoint.rstrip('/')
        self.api_key = api_key
        self.timeout = timeout

    def generate(self, prompt: str, **opts) -> Dict[str, Any]:
        # placeholder: just echo in stub mode
        return {"model": "web_relay", "ok": True, "prompt": prompt, "opts": opts}
