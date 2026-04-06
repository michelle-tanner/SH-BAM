# Scan the docs/ folder, parse every file, and load everything into ChromaDB via LlamaIndex. You run this once to populate the vector store

from llama_index.core import VectorStoreIndex, StorageContext
from llama_index.vector_stores.chroma import ChromaVectorStore
from llama_index.embeddings.ollama import OllamaEmbedding
import chromadb
from pathlib import Path
from query_system.parser import parse_document

OLLAMA_BASE_URL = "http://localhost:11434"
OLLAMA_MODEL    = "llama3.1"
CHROMA_PATH     = "query_system/index_store"

# One-time (or on-demand) function that populates the ChromaDB vector store
# Steps: 
    # 1. Scan the docs/ folder for any files (skips hidden files) 
    # 2. Calls parse_document() in parser.py on each file to extract text chunks + metadata
    # 3. Wraps each chunk as a LlamaIndex Document object 
    # 4. Embeds the documents using the local Ollama embedding model 
    # 5. Stores the embedded vectors in ChromaDB under the "documents" collection 
# Returns the total number of chunks written so we can confirm ingestion works. 
# Whenever new documents are added, this function runs. 
def ingest_docs(docs_path: str = "query_system/docs") -> int:
    """
    Scans docs_path for files, parses each one, embeds the chunks,
    and stores them in ChromaDB. Returns the total number of chunks ingested.
    """
    docs_dir = Path(docs_path)
    files = [f for f in docs_dir.iterdir() if f.is_file() and not f.name.startswith(".")]

    if not files:
        print(f"No files found in {docs_path}")
        return 0

    embed_model = OllamaEmbedding(model_name=OLLAMA_MODEL, base_url=OLLAMA_BASE_URL)

    chroma_client     = chromadb.PersistentClient(path=CHROMA_PATH)
    chroma_collection = chroma_client.get_or_create_collection("documents")
    vector_store      = ChromaVectorStore(chroma_collection=chroma_collection)
    storage_context   = StorageContext.from_defaults(vector_store=vector_store)

    from llama_index.core import Document

    total_chunks = 0
    for filepath in files:
        print(f"Ingesting: {filepath.name}")
        chunks = parse_document(filepath)
        if not chunks:
            print(f"  No content extracted from {filepath.name}, skipping.")
            continue

        documents = [
            Document(text=chunk["text"], metadata=chunk["metadata"])
            for chunk in chunks
        ]

        VectorStoreIndex.from_documents(
            documents,
            storage_context=storage_context,
            embed_model=embed_model,
        )
        total_chunks += len(documents)
        print(f"  {len(documents)} chunks ingested from {filepath.name}")

    print(f"Ingestion complete. Total chunks: {total_chunks}")
    return total_chunks