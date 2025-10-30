import json
from typing import Dict, Any, Callable

class ToolRegistry:
    def __init__(self):
        self._tools: Dict[str, Callable[[Dict[str, Any]], Dict[str, Any]]] = {}

    def register(self, name: str, fn: Callable[[Dict[str, Any]], Dict[str, Any]]):
        self._tools[name] = fn

    def run(self, name: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        if name not in self._tools:
            return { 'error': f'tool {name} not found' }
        try:
            return self._tools[name](payload)
        except Exception as e:
            return { 'error': str(e) }

# Example tool
if __name__ == '__main__':
    reg = ToolRegistry()
    reg.register('echo', lambda p: {'ok': True, 'payload': p})
    print(json.dumps(reg.run('echo', {'msg':'hello'})))
