from llama_index.core import VectorStoreIndex, StorageContext
from llama_index.core.retrievers import VectorIndexRetriever
from llama_index.vector_stores.chroma import ChromaVectorStore
from llama_index.embeddings.ollama import OllamaEmbedding
import chromadb
import json
import os
from datetime import datetime
from typing import Optional
import anthropic
from llama_index.core import VectorStoreIndex, StorageContext


"""
Retrieval Agent
---------------
Responsibilities:
  1. Use Claude to extract structured intent from the raw user query
     (keywords, date range, document type, etc.)
  2. Run a filtered vector search against ChromaDB via LlamaIndex
  3. Return a ranked list of matching documents + metadata
 
Called by: query_router.py  (when the Router agent classifies the query as "retrieval")
"""
 

 
# ── Config ────────────────────────────────────────────────────────────────────
 
CHROMA_PATH  = os.getenv("CHROMA_PATH",  "./index_store/chroma")
CHROMA_COLLECTION = os.getenv("CHROMA_COLLECTION", "reports")
TOP_K        = int(os.getenv("RETRIEVAL_TOP_K", "8"))
 
client = anthropic.Anthropic()          
 
# ── Step 1: Claude parses the raw query into structured intent ─────────────────
 
PARSE_SYSTEM_PROMPT = """
You are a query-understanding assistant for a medical/pharma research report system.
 
Given a user's natural-language search query, extract structured search intent and
return ONLY a valid JSON object — no markdown fences, no prose, no explanation.
 
Return this exact schema:
{
  "keywords": ["list", "of", "important", "search", "terms"],
  "drug_names": ["any", "drug", "or", "compound", "names"],
  "disease_areas": ["therapeutic", "areas", "or", "conditions"],
  "date_from": "YYYY-MM-DD or null",
  "date_to":   "YYYY-MM-DD or null",
  "doc_type":  "report | alert | summary | any",
  "refined_query": "a clean, concise version of the query for vector search"
}
 
Rules:
- keywords must include all meaningful terms (exclude stop-words)
- If no date range is mentioned, set both date fields to null
- If a relative date is mentioned (e.g. "last 3 months"), compute from today: {today}
- refined_query should be 1–2 sentences, optimised for semantic similarity search
"""
 
def parse_query_with_claude(raw_query: str) -> dict:
    """
    Send the raw user query to Claude and get back a structured intent object.
    Returns a dict matching the schema above.
    """
    today = datetime.today().strftime("%Y-%m-%d")
    system = PARSE_SYSTEM_PROMPT.replace("{today}", today)
 
    message = client.messages.create(
        model="claude-opus-4-5",
        max_tokens=512,
        system=system,
        messages=[{"role": "user", "content": raw_query}],
    )
 
    raw_json = message.content[0].text.strip()
 
    try:
        return json.loads(raw_json)
    except json.JSONDecodeError:
        # Fallback: treat the whole query as keywords
        return {
            "keywords": raw_query.split(),
            "drug_names": [],
            "disease_areas": [],
            "date_from": None,
            "date_to": None,
            "doc_type": "any",
            "refined_query": raw_query,
        }
 
 
# ── Step 2: Build ChromaDB / LlamaIndex query engine ──────────────────────────
 
def _get_index() -> VectorStoreIndex:
    """Load the persisted LlamaIndex index backed by ChromaDB."""
    chroma_client     = chromadb.PersistentClient(path=CHROMA_PATH)
    chroma_collection = chroma_client.get_or_create_collection(CHROMA_COLLECTION)
    vector_store      = ChromaVectorStore(chroma_collection=chroma_collection)
    storage_context   = StorageContext.from_defaults(vector_store=vector_store)
    return VectorStoreIndex.from_vector_store(
        vector_store, storage_context=storage_context
    )
 
 
def _build_metadata_filters(intent: dict) -> Optional[dict]:
    """
    Translate the parsed intent into LlamaIndex metadata filters.
    Filters are applied BEFORE the vector similarity search (pre-filtering).
 
    Expected metadata fields stored during ingest (see ingest.py):
      - doc_date   : "YYYY-MM-DD"
      - doc_type   : "report" | "alert" | "summary"
      - filename   : original file name
    """
    from llama_index.core.vector_stores import (
        MetadataFilter,
        MetadataFilters,
        FilterOperator,
        FilterCondition,
    )
 
    filters = []
 
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
 
 
# ── Step 3: Run the retrieval and format results ───────────────────────────────
 
def run_retrieval(raw_query: str) -> dict:
    """
    Full retrieval pipeline:
      1. Parse query with Claude
      2. Build metadata filters
      3. Vector-search ChromaDB via LlamaIndex
      4. Return ranked document list
 
    Returns:
    {
      "type": "retrieval",
      "intent": { ...parsed intent... },
      "results": [
        {
          "filename": "report_2024_ovarian_cancer.pdf",
          "doc_date": "2024-03-15",
          "doc_type": "report",
          "score": 0.87,
          "snippet": "first ~300 chars of the matched chunk...",
          "file_path": "/docs/report_2024_ovarian_cancer.pdf"
        },
        ...
      ],
      "total": 5
    }
    """
    # 1. Understand the query
    intent = parse_query_with_claude(raw_query)
 
    # 2. Load index + build filters
    index           = _get_index()
    metadata_filters = _build_metadata_filters(intent)
 
    retriever_kwargs = {"similarity_top_k": TOP_K}
    if metadata_filters:
        retriever_kwargs["filters"] = metadata_filters
 
    retriever = index.as_retriever(**retriever_kwargs)
 
    # 3. Run the search using the Claude-refined query
    nodes = retriever.retrieve(intent["refined_query"])
 
    # 4. Deduplicate by source file (keep highest-scoring chunk per file)
    seen: dict[str, dict] = {}
    for node in nodes:
        meta     = node.metadata or {}
        filename = meta.get("filename", "unknown")
        score    = node.score or 0.0
 
        if filename not in seen or score > seen[filename]["score"]:
            seen[filename] = {
                "filename":  filename,
                "doc_date":  meta.get("doc_date", ""),
                "doc_type":  meta.get("doc_type", ""),
                "score":     round(score, 4),
                "snippet":   node.get_content()[:300].strip(),
                "file_path": meta.get("file_path", f"/docs/{filename}"),
            }
 
    results = sorted(seen.values(), key=lambda r: r["score"], reverse=True)
 
    return {
        "type":    "retrieval",
        "intent":  intent,
        "results": results,
        "total":   len(results),
    }
 