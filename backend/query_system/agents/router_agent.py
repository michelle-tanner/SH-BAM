"""
router_agent.py
---------------
Lightweight retrieval vs synthesis routing. Extend when synthesis is real.
"""


def classify(query: str) -> str:
    q = (query or "").lower()
    synthesis_hints = (
        "summarize all",
        "summarize every",
        "write a report",
        "executive summary",
        "compare all",
        "synthesize",
    )
    if any(h in q for h in synthesis_hints):
        return "synthesis"
    return "retrieval"
