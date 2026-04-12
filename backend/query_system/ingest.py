"""
ingest.py
---------
Index all PDF / DOCX / TXT files under DOCS_DIR into a persistent Chroma store
using Ollama embeddings. Run from the backend folder:

    python -m query_system.ingest
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import chromadb
from llama_index.core import Document, Settings, StorageContext, VectorStoreIndex
from llama_index.core.node_parser import SentenceSplitter
from llama_index.embeddings.ollama import OllamaEmbedding
from llama_index.vector_stores.chroma import ChromaVectorStore

from query_system.parser import guess_doc_date, parse_document

BACKEND_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DOCS_DIR = BACKEND_ROOT / "query_system" / "docs"
DEFAULT_CHROMA = BACKEND_ROOT / "index_store" / "chroma"
DEFAULT_COLLECTION = os.getenv("CHROMA_COLLECTION", "reports")

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_EMBED_MODEL = os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text")


def _allowed_files(docs_dir: Path) -> list[Path]:
    out: list[Path] = []
    if not docs_dir.is_dir():
        return out
    for p in sorted(docs_dir.iterdir()):
        if p.name.startswith("."):
            continue
        if p.suffix.lower() not in {".pdf", ".docx", ".txt"}:
            continue
        if p.is_file():
            out.append(p)
    return out


def ingest_docs(
    docs_dir: Path | None = None,
    chroma_path: Path | None = None,
    collection_name: str | None = None,
) -> dict:
    """
    Read documents from disk, chunk them, and write vectors + metadata to Chroma.

    Returns a small summary dict for logging / CLI.
    """
    docs_dir = Path(docs_dir or os.getenv("DOCS_DIR", DEFAULT_DOCS_DIR)).resolve()
    chroma_path = Path(chroma_path or os.getenv("CHROMA_PATH", DEFAULT_CHROMA)).resolve()
    collection_name = collection_name or DEFAULT_COLLECTION

    files = _allowed_files(docs_dir)
    if not files:
        return {"indexed_files": 0, "chunks": 0, "message": f"No documents found in {docs_dir}"}

    embed_model = OllamaEmbedding(
        model_name=OLLAMA_EMBED_MODEL,
        base_url=OLLAMA_BASE_URL,
    )
    Settings.embed_model = embed_model

    chroma_path.mkdir(parents=True, exist_ok=True)
    chroma_client = chromadb.PersistentClient(path=str(chroma_path))
    try:
        chroma_client.delete_collection(collection_name)
    except Exception:
        pass

    chroma_collection = chroma_client.get_or_create_collection(collection_name)
    vector_store = ChromaVectorStore(chroma_collection=chroma_collection)
    storage_context = StorageContext.from_defaults(vector_store=vector_store)

    splitter = SentenceSplitter(chunk_size=1024, chunk_overlap=128)
    all_nodes: list = []

    for fp in files:
        text = parse_document(fp)
        if not text.strip():
            continue
        doc_date = guess_doc_date(fp)
        meta = {
            "filename": fp.name,
            "doc_date": doc_date,
            "doc_type": "report",
            "file_path": f"/docs/{fp.name}",
        }
        doc = Document(text=text, metadata=meta)
        all_nodes.extend(splitter.get_nodes_from_documents([doc]))

    if not all_nodes:
        return {"indexed_files": len(files), "chunks": 0, "message": "All files were empty after parsing."}

    VectorStoreIndex(
        all_nodes,
        storage_context=storage_context,
        show_progress=True,
    )

    return {
        "indexed_files": len(files),
        "chunks": len(all_nodes),
        "chroma_path": str(chroma_path),
        "collection": collection_name,
    }


if __name__ == "__main__":
    summary = ingest_docs()
    print(summary)
    sys.exit(0 if summary.get("chunks", 0) else 1)
