"""
synthesis_agent.py
------------------
Placeholder until the synthesis pipeline is implemented.
"""


def run_synthesis(query: str) -> dict:
    return {
        "type": "synthesis",
        "content": (
            "Synthesis is not implemented yet. Try rephrasing as a document search "
            f"(your request: {query[:200]!r}…)."
        ),
        "sources": [],
    }
