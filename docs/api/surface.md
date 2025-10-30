# Sheratan API Surface (CLI/HTTP)

## HTTP (FastAPI)
- `GET /health` → status
- `POST /router/decide` → Model decision for a Job
- `POST /memory/add/{doc_id}` { text, top_k } → store text
- `POST /memory/query` { text, top_k } → matches
- `POST /tools/run` { name, payload } → tool result

Run locally:
```bash
# Windows
scripts\start_api.bat
# macOS/Linux
chmod +x scripts/start_api.sh && scripts/start_api.sh
```

## CLI
- `python -m core.cli decide --file job.json`
- `python -m core.cli decide --job '{"id":"1","kind":"task","payload":{},"budget":"low","latency_ms":800}'`
- `python -m core.cli tool --name echo --payload '{"msg":"hi"}'`

Contracts: see `/interfaces/schemas/*.json`.
