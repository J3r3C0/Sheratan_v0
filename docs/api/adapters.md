# Adapters (LLM)

Thin adapter layer to connect routers/policies with concrete runtimes.

- `local_llm.py` — placeholders for **llama-cpp** and **Ollama**
- `web_relay.py` — placeholder for HTTP relay (e.g., GPT-Relay)

Real implementations should be injected via config and handle:
- timeouts / retries / backoff
- streaming vs. batch
- logging & token accounting
