from fastapi import APIRouter
from pydantic import BaseModel
from fastapi import APIRouter, HTTPException, Query
from typing import Optional
import os
 
from query_system.agents.retrieval_agent import run_retrieval

router = APIRouter()

# Routes implemented when query_system agents are complete:
#   POST /query
#   GET  /list
#   GET  /document/{path}

class Query(BaseModel):
    query: str

class OKResponse(BaseModel):
    status: str = "ok"
    #name: str = "Hend Alawi"

@router.post("/query", response_model=OKResponse, status_code=201)
async def queryDocuments(payload: Query):
    print("Received query:", payload.query)
    return OKResponse()


"""
query_router.py
---------------
FastAPI routes consumed by the React frontend.
 
Endpoints:
  POST /query             ← main entry point; routes to retrieval or synthesis
  GET  /list              ← return all indexed documents
  GET  /document?path=... ← return raw text of one document
"""
 
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional
import os
 
from query_system.agents.retrieval_agent import run_retrieval
 
# Synthesis agent (separate team-member's file — import lazily so the
# project still runs even if that module isn't ready yet)
def _run_synthesis(query: str):
    from query_system.agents.synthesis_agent import run_synthesis  # noqa
    return run_synthesis(query)
 
# Router agent (classifies retrieval vs synthesis)
def _classify(query: str) -> str:
    from query_system.agents.router_agent import classify  # noqa
    return classify(query)
 
router = APIRouter()
 
DOCS_DIR = os.getenv("DOCS_DIR", "./docs")
 
 
# ── Request / Response models ─────────────────────────────────────────────────
 
class QueryRequest(BaseModel):
    query: str
    date_range: Optional[dict] = None   # {"from": "YYYY-MM-DD", "to": "YYYY-MM-DD"}
 
 
# ── Routes ────────────────────────────────────────────────────────────────────
 
@router.post("/query")
async def handle_query(body: QueryRequest):
    """
    1. Router agent classifies the query ("retrieval" or "synthesis")
    2. Delegate to the appropriate agent
    3. Return structured result to the frontend
 
    Retrieval response shape:
    {
      "type": "retrieval",
      "intent": { ...parsed intent from Claude... },
      "results": [ { filename, doc_date, doc_type, score, snippet, file_path }, ... ],
      "total": N
    }
 
    Synthesis response shape (other team's work):
    {
      "type": "synthesis",
      "content": "<markdown report>",
      "sources": ["filename1.pdf", ...]
    }
    """
    if not body.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty.")
 
    # If the frontend supplies an explicit date range, append it to the query
    # string so Claude's parser can pick it up naturally
    enriched_query = body.query
    if body.date_range:
        date_from = body.date_range.get("from", "")
        date_to   = body.date_range.get("to", "")
        if date_from and date_to:
            enriched_query += f" (date range: {date_from} to {date_to})"
 
    # Route
    try:
        query_type = _classify(enriched_query)
    except Exception:
        # If router agent isn't implemented yet, default to retrieval
        query_type = "retrieval"
 
    # Delegate
    if query_type == "retrieval":
        return run_retrieval(enriched_query)
    else:
        return _run_synthesis(enriched_query)
 
 
@router.get("/list")
async def list_documents():
    """
    Return metadata for every document in the index / docs folder.
    The frontend uses this to populate the Reports tab.
 
    Response:
    {
      "documents": [
        { "filename": "report.pdf", "doc_date": "2024-03-01", "doc_type": "report", "file_path": "/docs/report.pdf" },
        ...
      ],
      "total": N
    }
    """
    docs = []
    for fname in sorted(os.listdir(DOCS_DIR)):
        if fname.startswith("."):
            continue
        ext = fname.rsplit(".", 1)[-1].lower()
        if ext not in {"pdf", "docx", "txt"}:
            continue
        docs.append({
            "filename":  fname,
            "doc_date":  "",            # populated properly after ingest
            "doc_type":  "report",
            "file_path": f"/docs/{fname}",
        })
 
    return {"documents": docs, "total": len(docs)}
 
 
@router.get("/document")
async def get_document(path: str = Query(..., description="Relative file path, e.g. /docs/report.pdf")):
    """
    Return the plain-text content of a single document.
    The frontend's DocumentViewer calls this to display a report.
 
    Response:
    {
      "filename": "report.pdf",
      "content": "full plain-text content...",
      "file_path": "/docs/report.pdf"
    }
    """
    # Sanitise path — prevent directory traversal
    safe_name = os.path.basename(path)
    full_path = os.path.join(DOCS_DIR, safe_name)
 
    if not os.path.isfile(full_path):
        raise HTTPException(status_code=404, detail=f"Document '{safe_name}' not found.")
 
    ext = safe_name.rsplit(".", 1)[-1].lower()
 
    if ext == "pdf":
        try:
            import fitz  # PyMuPDF
            doc  = fitz.open(full_path)
            text = "\n".join(page.get_text() for page in doc)
        except ImportError:
            text = "[PDF viewer not available — install PyMuPDF]"
 
    elif ext == "docx":
        try:
            from docx import Document
            doc  = Document(full_path)
            text = "\n".join(p.text for p in doc.paragraphs)
        except ImportError:
            text = "[DOCX viewer not available — install python-docx]"
 
    else:
        with open(full_path, "r", encoding="utf-8", errors="replace") as f:
            text = f.read()
 
    return {"filename": safe_name, "content": text, "file_path": path}