# Take a filepath, use unstructured to extract text, and return a list of text chunks with metadata attached

from unstructured.partition.auto import partition
from pathlib import Path
import re
import datetime

# Helper function to extract YYYY-MM-DD date from the filename
# If no date found, falls back to the last-modified timestamp 
# This date gets stored as metadata on every chunk so agents can filter by date range  
def _extract_date(filepath: Path) -> str:
    """Try to extract a YYYY-MM-DD date from the filename, else use file mtime."""
    match = re.search(r"\d{4}-\d{2}-\d{2}", filepath.stem)
    if match:
        return match.group(0)
    mtime = filepath.stat().st_mtime
    return datetime.datetime.fromtimestamp(mtime).strftime("%Y-%m-%d")

# Main function 
# Takes a filepath and gives it to Unstructured library to parse. Packages all elements found (paragraphs, titles, tables, etc.) into a "dict" with raw text and metadata (filename + date).
# Returns a list of these chunks which ingest.py then wraps into LlamaIndex Documents for embedding and storage in ChromaDB. 
def parse_document(filepath: Path) -> list[dict]:
    """
    Parses a document and returns a list of text chunks with metadata.
    Returns: [{"text": "...", "metadata": {"filename": "...", "document_date": "YYYY-MM-DD"}}]
    """
    elements = partition(filename=str(filepath))
    document_date = _extract_date(filepath)
    filename = filepath.name

    chunks = []
    for el in elements:
        text = str(el).strip()
        if text:
            chunks.append({
                "text": text,
                "metadata": {
                    "filename": filename,
                    "document_date": document_date,
                }
            })

    return chunks

