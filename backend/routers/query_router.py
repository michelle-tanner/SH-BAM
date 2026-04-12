"""
query_router.py
---------------
FastAPI routes for the query system (search, list, document text).

Endpoints:
  POST /query             — natural-language search over indexed reports
  GET  /list              — metadata for files in the docs folder
  GET  /document?path=... — plain text of one document (for preview)
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from query_system.agents.retrieval_agent import run_retrieval
from query_system.parser import guess_doc_date

router = APIRouter()

DOCS_DIR = os.path.abspath(os.getenv("DOCS_DIR", os.path.join(os.path.dirname(__file__), "..", "query_system", "docs")))


def _run_synthesis(query: str) -> dict[str, Any]:
    from query_system.agents.synthesis_agent import run_synthesis  # noqa: WPS433

    return run_synthesis(query)


def _classify(query: str) -> str:
    from query_system.agents.router_agent import classify  # noqa: WPS433

    return classify(query)


class QueryRequest(BaseModel):
    query: str
    date_range: Optional[dict[str, Any]] = None  # {"from": "YYYY-MM-DD", "to": "YYYY-MM-DD"}


@router.post("/query")
async def handle_query(body: QueryRequest) -> dict[str, Any]:
    if not body.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty.")

    print(f"\n{'='*60}")
    print(f"[QUERY] {body.query.strip()!r}")
    if body.date_range:
        print(f"[QUERY] date_range: {body.date_range}")

    enriched = body.query.strip()
    if body.date_range:
        date_from = body.date_range.get("from", "") or body.date_range.get("start", "")
        date_to = body.date_range.get("to", "") or body.date_range.get("end", "")
        if date_from and date_to:
            enriched += f" (date range: {date_from} to {date_to})"

    try:
        query_type = _classify(enriched)
    except Exception:  # noqa: BLE001
        query_type = "retrieval"

    print(f"[ROUTER] classified as → {query_type.upper()}")

    if query_type == "retrieval":
        return run_retrieval(body.query.strip(), date_range=body.date_range)

    return _run_synthesis(enriched)


@router.get("/list")
async def list_documents() -> dict[str, Any]:
    docs: list[dict[str, str]] = []
    if not os.path.isdir(DOCS_DIR):
        return {"documents": [], "total": 0}

    for fname in sorted(os.listdir(DOCS_DIR)):
        if fname.startswith("."):
            continue
        ext = fname.rsplit(".", 1)[-1].lower()
        if ext not in {"pdf", "docx", "txt"}:
            continue
        path = os.path.join(DOCS_DIR, fname)
        doc_date = guess_doc_date(Path(path)) if os.path.isfile(path) else ""
        docs.append(
            {
                "filename": fname,
                "doc_date": doc_date,
                "doc_type": "report",
                "file_path": f"/docs/{fname}",
            }
        )

    return {"documents": docs, "total": len(docs)}


@router.get("/document")
async def get_document(
    path: str = Query(..., description="Relative file path, e.g. /docs/report.pdf"),
) -> dict[str, str]:
    safe_name = os.path.basename(path)
    full_path = os.path.join(DOCS_DIR, safe_name)

    if not os.path.isfile(full_path):
        raise HTTPException(status_code=404, detail=f"Document '{safe_name}' not found.")

    ext = safe_name.rsplit(".", 1)[-1].lower()

    if ext == "pdf":
        try:
            import fitz  # PyMuPDF

            doc = fitz.open(full_path)
            try:
                text = "\n".join(page.get_text() for page in doc)
            finally:
                doc.close()
        except ImportError:
            text = "[PDF viewer not available — install PyMuPDF]"

    elif ext == "docx":
        try:
            from docx import Document

            doc = Document(full_path)
            text = "\n".join(p.text for p in doc.paragraphs)
        except ImportError:
            text = "[DOCX viewer not available — install python-docx]"

    else:
        with open(full_path, "r", encoding="utf-8", errors="replace") as f:
            text = f.read()

    return {"filename": safe_name, "content": text, "file_path": path}
