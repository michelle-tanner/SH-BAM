"""
retrieval_agent.py
------------------
1. Parse the user query into search intent (keywords + optional date window).
2. Vector-search Chroma (LlamaIndex + Ollama embeddings) with metadata filters.
3. Return ranked, de-duplicated documents for the frontend.

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
from llama_index.core import Settings, StorageContext, VectorStoreIndex
from llama_index.embeddings.ollama import OllamaEmbedding
from llama_index.vector_stores.chroma import ChromaVectorStore

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

    if (not date_from or not date_to) and date_range:
        # tolerate partial
        pass

    if not date_from or not date_to:
        months = _parse_relative_months(q)
        if months is not None:
            date_to = _today_iso()
            date_from = _months_ago(months)

    words = [w.strip('.,?!()[]"\'') for w in q.split() if len(w.strip('.,?!()[]"\'')) > 2]
    stop = {
        "the",
        "and",
        "for",
        "with",
        "from",
        "that",
        "this",
        "have",
        "has",
        "was",
        "were",
        "are",
        "about",
        "give",
        "documents",
        "document",
        "reports",
        "report",
        "please",
        "show",
        "find",
        "search",
        "last",
        "past",
        "months",
        "month",
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


def _build_metadata_filters(intent: dict[str, Any]):
    from llama_index.core.vector_stores import (
        FilterCondition,
        FilterOperator,
        MetadataFilter,
        MetadataFilters,
    )

    filters: list = []
    if intent.get("date_from"):
        filters.append(
            MetadataFilter(
                key="doc_date",
                value=intent["date_from"],
                operator=FilterOperator.GTE,
            )
        )
    if intent.get("date_to"):
        filters.append(
            MetadataFilter(
                key="doc_date",
                value=intent["date_to"],
                operator=FilterOperator.LTE,
            )
        )
    if intent.get("doc_type") and intent["doc_type"] != "any":
        filters.append(
            MetadataFilter(
                key="doc_type",
                value=intent["doc_type"],
                operator=FilterOperator.EQ,
            )
        )
    if not filters:
        return None
    return MetadataFilters(filters=filters, condition=FilterCondition.AND)


def _get_index() -> VectorStoreIndex:
    embed_model = OllamaEmbedding(
        model_name=OLLAMA_EMBED_MODEL,
        base_url=OLLAMA_BASE_URL,
    )
    Settings.embed_model = embed_model

    CHROMA_PATH.mkdir(parents=True, exist_ok=True)
    chroma_client = chromadb.PersistentClient(path=str(CHROMA_PATH))
    chroma_collection = chroma_client.get_or_create_collection(CHROMA_COLLECTION)
    vector_store = ChromaVectorStore(chroma_collection=chroma_collection)
    storage_context = StorageContext.from_defaults(vector_store=vector_store)
    return VectorStoreIndex.from_vector_store(
        vector_store,
        storage_context=storage_context,
        embed_model=embed_model,
    )


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

    try:
        index = _get_index()
    except Exception as exc:  # noqa: BLE001 — surface friendly message to UI
        print(f"[RETRIEVAL] ERROR: could not open index — {exc}")
        return {
            "type": "retrieval",
            "intent": intent,
            "results": [],
            "total": 0,
            "error": f"Could not open the search index ({exc}). Run `python -m query_system.ingest` after adding PDFs to docs/.",
        }

    metadata_filters = _build_metadata_filters(intent)
    retriever_kwargs: dict[str, Any] = {"similarity_top_k": TOP_K}
    if metadata_filters:
        retriever_kwargs["filters"] = metadata_filters

    print(f"[RETRIEVAL] searching index (top_k={TOP_K})...")
    try:
        retriever = index.as_retriever(**retriever_kwargs)
        nodes = retriever.retrieve(intent["refined_query"])
    except Exception as exc:  # noqa: BLE001
        print(f"[RETRIEVAL] ERROR: search failed — {exc}")
        return {
            "type": "retrieval",
            "intent": intent,
            "results": [],
            "total": 0,
            "error": f"Search failed ({exc}). Is Ollama running with model {OLLAMA_EMBED_MODEL!r}?",
        }

    print(f"[RETRIEVAL] {len(nodes)} raw chunks returned")

    seen: dict[str, dict[str, Any]] = {}
    for node in nodes:
        meta = node.metadata or {}
        filename = meta.get("filename", "unknown")
        score = float(node.score or 0.0)
        snippet = (node.get_content() or "")[:400].strip()

        if filename not in seen or score > float(seen[filename]["score"]):
            seen[filename] = {
                "filename": filename,
                "doc_date": meta.get("doc_date", ""),
                "doc_type": meta.get("doc_type", "report"),
                "score": round(score, 4),
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
