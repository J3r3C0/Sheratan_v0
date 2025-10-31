# Agents API

### POST /agents/coding
Request:
```json
{ "prompt": "make a hello file" }
```
Response (stub):
```json
{
  "ok": true,
  "plan": { "files": [{ "path": "demo/hello.py", "task": "print('hello')" }] },
  "files": { "demo/hello.py": "# generated\nprint('hello')" },
  "review": { "ok": true, "notes": [] }
}
```

### Notes
- This is a minimal skeleton to be extended with adapters, replay/reflection, and persistence.
- Later, `core.agents.registry` can be used to resolve agent classes by name (e.g. `coding`, `trader`, `research`).
