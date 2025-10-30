# Coding Agent (skeleton)

Minimal thinker→generator→review loop.

API sketch:
```python
agent = CodingAgent(router)
plan = agent.analyze("make a hello file")
files = agent.generate(plan)
report = agent.review(files)
```

Next: connect to adapters, add replay/reflexion hooks.
