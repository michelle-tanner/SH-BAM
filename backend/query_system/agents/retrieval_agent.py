"""
retrieval_agent.py
------------------
1. Parse the user query into search intent (keywords + optional date window).
2. Embed the query directly via the ollama Python client (bypasses LlamaIndex's
   retriever layer which caches query embeddings globally and returns identical
   scores across different queries in the same server session).
3. Query ChromaDB directly with the fresh embedding vector.
4. Return ranked, de-duplicated documents for the frontend.

Called from query_router.handle_query when the route is classified as retrieval.
"""

from __future__ import annotations

import json
import os
import re
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Optional

import chromadb
import ollama as _ollama

BACKEND_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_CHROMA = BACKEND_ROOT / "index_store" / "chroma"

CHROMA_PATH = Path(os.getenv("CHROMA_PATH", DEFAULT_CHROMA)).resolve()
CHROMA_COLLECTION = os.getenv("CHROMA_COLLECTION", "reports")
TOP_K = int(os.getenv("RETRIEVAL_TOP_K", "16"))

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_EMBED_MODEL = os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text")

_MONTH_WORDS = {
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
    "eleven": 11,
    "twelve": 12,
}


def _today_iso() -> str:
    return date.today().isoformat()


def _months_ago(months: int) -> str:
    d = date.today()
    y, m = d.year, d.month
    m -= months
    while m <= 0:
        m += 12
        y -= 1
    last_day = min(d.day, _days_in_month(y, m))
    return date(y, m, last_day).isoformat()


def _days_in_month(year: int, month: int) -> int:
    if month == 12:
        next_m = date(year + 1, 1, 1)
    else:
        next_m = date(year, month + 1, 1)
    return (next_m - timedelta(days=1)).day


def _parse_relative_months(raw: str) -> Optional[int]:
    s = raw.lower()
    m = re.search(r"\b(?:past|last|in the last|within the last)\s+(\d{1,2})\s+months?\b", s)
    if m:
        return max(1, min(120, int(m.group(1))))
    m = re.search(
        r"\b(?:past|last|in the last|within the last)\s+(one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve)\s+months?\b",
        s,
    )
    if m:
        return _MONTH_WORDS.get(m.group(1), 3)
    if re.search(r"\b(?:past|last)\s+(?:a|one)\s+month\b", s):
        return 1
    if re.search(r"\b(?:past|last)\s+(?:a|one)\s+year\b", s) or re.search(r"\blast\s+year\b", s):
        return 12
    return None


def parse_query_intent(raw_query: str, date_range: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    """
    Build structured intent without an external LLM (works offline with Ollama only).

    If the frontend sends date_range { from, to }, those win. Otherwise relative
    phrases like 'past three months' set the window against today's date.
    """
    q = raw_query.strip()
    date_from: Optional[str] = None
    date_to: Optional[str] = None

    if date_range:
        date_from = date_range.get("from") or date_range.get("start")
        date_to = date_range.get("to") or date_range.get("end")

    if not date_from or not date_to:
        months = _parse_relative_months(q)
        if months is not None:
            date_to = _today_iso()
            date_from = _months_ago(months)

    words = [w.strip('.,?!()[]"\'') for w in q.split() if len(w.strip('.,?!()[]"\'')) > 2]
    stop = {
        "the", "and", "for", "with", "from", "that", "this", "have", "has",
        "was", "were", "are", "about", "give", "documents", "document",
        "reports", "report", "please", "show", "find", "search", "last",
        "past", "months", "month",
    }
    keywords = [w for w in words if w.lower() not in stop][:24]

    return {
        "keywords": keywords or words[:12],
        "drug_names": [],
        "disease_areas": [],
        "date_from": date_from,
        "date_to": date_to,
        "doc_type": "any",
        "refined_query": q,
    }


def _build_chroma_where(intent: dict[str, Any]) -> Optional[dict]:
    """
    Translates structured intent into a ChromaDB `where` filter dict.
    Date strings are compared lexicographically — valid for ISO YYYY-MM-DD.
    """
    conditions = []
    if intent.get("date_from"):
        conditions.append({"doc_date": {"$gte": intent["date_from"]}})
    if intent.get("date_to"):
        conditions.append({"doc_date": {"$lte": intent["date_to"]}})
    if intent.get("doc_type") and intent["doc_type"] != "any":
        conditions.append({"doc_type": {"$eq": intent["doc_type"]}})

    if not conditions:
        return None
    if len(conditions) == 1:
        return conditions[0]
    return {"$and": conditions}


# ---------------------------------------------------------------------------
# ChromaDB singleton — connection opened once, reused across queries.
# ---------------------------------------------------------------------------
_chroma_collection: Optional[Any] = None


def _get_collection():
    global _chroma_collection
    if _chroma_collection is not None:
        return _chroma_collection

    CHROMA_PATH.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(CHROMA_PATH))
    _chroma_collection = client.get_or_create_collection(
        CHROMA_COLLECTION,
        metadata={"hnsw:space": "cosine"},
    )
    print(f"[RETRIEVAL] ChromaDB opened: collection={CHROMA_COLLECTION} (cosine distance)")
    return _chroma_collection


def _embed_query(text: str) -> list[float]:
    """
    Embeds query text directly via the ollama Python client.
    Bypasses LlamaIndex's OllamaEmbedding wrapper which caches query vectors
    globally in Settings, causing identical scores across different queries.
    """
    client = _ollama.Client(host=OLLAMA_BASE_URL)
    response = client.embeddings(model=OLLAMA_EMBED_MODEL, prompt=text)
    return response["embedding"]


def _dist_to_score(distance: float) -> float:
    """
    Converts ChromaDB cosine distance to a similarity score (0–1).
    ChromaDB cosine distance: 0 = identical, 1 = orthogonal, 2 = opposite.
        score = 1 - (distance / 2)  →  1.0 = perfect match, 0.0 = opposite
    Higher score = more relevant.
    """
    return round(max(0.0, 1.0 - distance / 2), 4)


def run_retrieval(raw_query: str, date_range: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    """
    Full retrieval pipeline. Response matches what the frontend expects:

    {
      "type": "retrieval",
      "intent": { ... },
      "results": [
        { "filename", "doc_date", "doc_type", "score", "snippet", "file_path" },
        ...
      ],
      "total": N
    }
    """
    intent = parse_query_intent(raw_query, date_range=date_range)

    print(f"[RETRIEVAL] keywords: {intent['keywords']}")
    if intent.get("date_from") or intent.get("date_to"):
        print(f"[RETRIEVAL] date filter: {intent.get('date_from')} → {intent.get('date_to')}")
    else:
        print("[RETRIEVAL] no date filter")

    # Embed the query fresh on every call — no caching layer
    print(f"[RETRIEVAL] embedding query via ollama ({OLLAMA_EMBED_MODEL})...")
    try:
        query_vector = _embed_query(intent["refined_query"])
    except Exception as exc:  # noqa: BLE001
        print(f"[RETRIEVAL] ERROR: embedding failed — {exc}")
        return {
            "type": "retrieval",
            "intent": intent,
            "results": [],
            "total": 0,
            "error": f"Embedding failed ({exc}). Is Ollama running with model {OLLAMA_EMBED_MODEL!r}?",
        }

    try:
        collection = _get_collection()
    except Exception as exc:  # noqa: BLE001
        print(f"[RETRIEVAL] ERROR: could not open ChromaDB — {exc}")
        return {
            "type": "retrieval",
            "intent": intent,
            "results": [],
            "total": 0,
            "error": f"Could not open the search index ({exc}). Run `python -m query_system.ingest`.",
        }

    # Cap n_results to actual collection size to avoid ChromaDB errors
    doc_count = collection.count()
    n_results = min(TOP_K, max(1, doc_count))
    where = _build_chroma_where(intent)

    print(f"[RETRIEVAL] searching {doc_count} chunks (n_results={n_results})...")
    try:
        query_kwargs: dict[str, Any] = {
            "query_embeddings": [query_vector],
            "n_results": n_results,
            "include": ["documents", "metadatas", "distances"],
        }
        if where:
            query_kwargs["where"] = where
        raw = collection.query(**query_kwargs)
    except Exception as exc:  # noqa: BLE001
        print(f"[RETRIEVAL] ERROR: ChromaDB query failed — {exc}")
        return {
            "type": "retrieval",
            "intent": intent,
            "results": [],
            "total": 0,
            "error": f"Search failed ({exc}).",
        }

    texts = raw["documents"][0]
    metas = raw["metadatas"][0]
    distances = raw["distances"][0]
    print(f"[RETRIEVAL] {len(texts)} raw chunks returned")

    # De-duplicate by filename, keeping the highest-scoring chunk per document
    seen: dict[str, dict[str, Any]] = {}
    for text, meta, dist in zip(texts, metas, distances):
        filename = meta.get("filename", "unknown")
        score = _dist_to_score(dist)
        snippet = (text or "")[:400].strip()

        if filename not in seen or score > float(seen[filename]["score"]):
            seen[filename] = {
                "filename": filename,
                "doc_date": meta.get("doc_date", ""),
                "doc_type": meta.get("doc_type", "report"),
                "score": score,
                "snippet": snippet,
                "file_path": meta.get("file_path", f"/docs/{filename}"),
            }

    results = sorted(seen.values(), key=lambda r: r["score"], reverse=True)
    print(f"[RETRIEVAL] {len(results)} unique documents after de-duplication:")
    for r in results:
        print(f"  {r['score']:.4f}  {r['filename']}  ({r['doc_date']})")
    print(f"{'='*60}\n")

    return {
        "type": "retrieval",
        "intent": intent,
        "results": results,
        "total": len(results),
    }


def run_retrieval_json(raw_query: str, date_range: Optional[dict[str, Any]] = None) -> str:
    """Optional helper for debugging / non-FastAPI callers."""
    return json.dumps(run_retrieval(raw_query, date_range=date_range), indent=2)
