from typing import Dict, Type

# Skeleton registry for future agent classes

_REGISTRY: Dict[str, type] = {}

def register(name: str, cls: type):
    _REGISTRY[name] = cls

def get(name: str) -> type | None:
    return _REGISTRY.get(name)
