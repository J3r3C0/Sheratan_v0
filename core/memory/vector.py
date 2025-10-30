from typing import Protocol, Dict, Any

class VectorStore(Protocol):
    def add(self, doc_id: str, text: str): ...
    def query(self, text: str, top_k: int = 5) -> list[tuple[str,float]]: ...

class InMemoryVS:
    def __init__(self):
        self._docs = {}
    def add(self, doc_id: str, text: str):
        self._docs[doc_id] = text
    def query(self, text: str, top_k: int = 5):
        from .similarity import compare
        scored = [(k, compare(text, v)) for k,v in self._docs.items()]
        return sorted(scored, key=lambda x: x[1], reverse=True)[:top_k]
