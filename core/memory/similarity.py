def compare(a: str, b: str) -> float:
    """Jaccard-Ähnlichkeit für einfache Textvergleiche.
    Gibt einen Wert zwischen 0..1 zurück.
    """
    sa, sb = set(a.split()), set(b.split())
    if not sa and not sb: return 1.0
    if not sa or not sb: return 0.0
    inter = len(sa & sb); union = len(sa | sb)
    return inter / union
