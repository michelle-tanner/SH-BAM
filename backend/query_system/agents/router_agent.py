"""
router_agent.py
---------------
Two-tier query router: classifies a user query as "retrieval" or "synthesis"
and returns the string label. Called by query_router.handle_query().

Tier 1 — keyword fast-path (zero latency, no LLM)
  Checks for unambiguous signal words in the query. If found, returns
  immediately without touching Ollama. Covers the majority of queries.

Tier 2 — LLM classification (Sandra's approach, via Ollama)
  For ambiguous queries that don't match any keyword, asks the local LLM
  to classify intent using a structured one-word prompt.

Safe default: "retrieval" on any Tier 2 failure (timeout, Ollama down, etc.)
  Retrieval is cheap, fast, and always useful. Synthesis is expensive and
  wrong-routing to it on an ambiguous query wastes ~10-30 seconds of LLM time.
"""

from __future__ import annotations

import os

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_LLM_MODEL = os.getenv("OLLAMA_LLM_MODEL", "llama3.1")

# Timeout for the LLM classification call. Kept short intentionally — routing
# should be near-instant. If the LLM takes longer than this it likely won't
# produce a useful classification anyway.
ROUTER_LLM_TIMEOUT = float(os.getenv("ROUTER_LLM_TIMEOUT", "10.0"))

# ---------------------------------------------------------------------------
# Tier 1 keyword lists
# ---------------------------------------------------------------------------
_SYNTHESIS_KEYWORDS = (
    "summarize all",
    "summarize every",
    "write a report",
    "write me a report",
    "executive summary",
    "compare all",
    "synthesize",
    "give me an overview",
    "overview of all",
    "analyze all",
    "analysis of all",
    "across all",
    "across the reports",
)

_RETRIEVAL_KEYWORDS = (
    "find",
    "show me",
    "list",
    "search",
    "what documents",
    "which reports",
    "which documents",
    "do you have",
    "give me the report",
    "get me the report",
)

# ---------------------------------------------------------------------------
# Tier 2 LLM classification prompt (from Sandra's branch)
# Returns exactly one word: "retrieval" or "synthesis"
# ---------------------------------------------------------------------------
_CLASSIFICATION_PROMPT = """\
You are a query router for a medical research document system.

Given the user query below, decide whether to:
- Return a list of relevant source documents ("retrieval"), OR
- Generate a synthesized summary report ("synthesis")

Rules:
- If the user is asking to find, list, search, or show specific documents → answer: retrieval
- If the user is asking to summarize, explain, compare, or analyze content → answer: synthesis
- Answer with exactly one word: retrieval or synthesis

Query: {query}
Answer:"""


def classify(query: str) -> str:
    """
    Classifies a query as "retrieval" or "synthesis".

    Tier 1 runs first with zero latency. Tier 2 (LLM) is only reached for
    queries that don't contain clear signal in either direction.
    Falls back to "retrieval" on any error.
    """
    q = query.lower()

    # ------------------------------------------------------------------
    # Tier 1: keyword fast-path
    # ------------------------------------------------------------------
    matched = next((h for h in _SYNTHESIS_KEYWORDS if h in q), None)
    if matched:
        print(f"[ROUTER] Tier 1 match: synthesis keyword {matched!r}")
        return "synthesis"

    matched = next((h for h in _RETRIEVAL_KEYWORDS if h in q), None)
    if matched:
        print(f"[ROUTER] Tier 1 match: retrieval keyword {matched!r}")
        return "retrieval"

    # ------------------------------------------------------------------
    # Tier 2: LLM classification for ambiguous queries
    # ------------------------------------------------------------------
    print(f"[ROUTER] No Tier 1 keyword match — asking LLM ({OLLAMA_LLM_MODEL})...")
    try:
        from llama_index.llms.ollama import Ollama

        llm = Ollama(
            model=OLLAMA_LLM_MODEL,
            base_url=OLLAMA_BASE_URL,
            request_timeout=ROUTER_LLM_TIMEOUT,
        )
        prompt = _CLASSIFICATION_PROMPT.format(query=query)
        response = llm.complete(prompt)
        intent = (response.text or "").strip().lower()
        print(f"[ROUTER] LLM raw response: {intent!r}")

        if "synthesis" in intent:
            print("[ROUTER] Tier 2 result → synthesis")
            return "synthesis"
        print("[ROUTER] Tier 2 result → retrieval")
        return "retrieval"

    except Exception as exc:  # noqa: BLE001 — Ollama down, timeout, etc.
        print(f"[ROUTER] Tier 2 failed ({exc}) — defaulting to retrieval")
        return "retrieval"
