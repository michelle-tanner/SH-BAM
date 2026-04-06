from llama_index.core import VectorStoreIndex, StorageContext
from llama_index.core.retrievers import VectorIndexRetriever
from llama_index.vector_stores.chroma import ChromaVectorStore
from llama_index.embeddings.ollama import OllamaEmbedding
import chromadb


# Connect to ChromaDB, run a vector search for a query, and return a clean list of matching document snippets with their source filenames. This is the "surface the right documents" (PoC)

OLLAMA_BASE_URL = "http://localhost:11434"
OLLAMA_MODEL    = "llama3.1"


class RetrievalAgent:
    def __init__(self, chroma_path: str = "query_system/index_store"):
        embed_model = OllamaEmbedding(model_name=OLLAMA_MODEL, base_url=OLLAMA_BASE_URL)

        chroma_client     = chromadb.PersistentClient(path=chroma_path)
        chroma_collection = chroma_client.get_or_create_collection("documents")
        vector_store      = ChromaVectorStore(chroma_collection=chroma_collection)
        storage_context   = StorageContext.from_defaults(vector_store=vector_store)

        self.index = VectorStoreIndex.from_vector_store(
            vector_store    = vector_store,
            storage_context = storage_context,
            embed_model     = embed_model,
        )

    def retrieve(self, query: str, top_k: int = 5, date_range: dict | None = None) -> dict:
        """
        Runs a vector search and returns matching document snippets.

        Returns:
            {
                "type": "retrieval",
                "documents": [
                    {"filename": "...", "snippet": "...", "score": 0.87},
                    ...
                ]
            }
        """
        filters = None
        if date_range:
            from llama_index.core.vector_stores import (
                MetadataFilter, MetadataFilters, FilterOperator, FilterCondition
            )
            filter_list = []
            if date_range.get("start"):
                filter_list.append(MetadataFilter(
                    key      = "document_date",
                    value    = date_range["start"],
                    operator = FilterOperator.GTE,
                ))
            if date_range.get("end"):
                filter_list.append(MetadataFilter(
                    key      = "document_date",
                    value    = date_range["end"],
                    operator = FilterOperator.LTE,
                ))
            if filter_list:
                filters = MetadataFilters(filters=filter_list, condition=FilterCondition.AND)

        retriever = self.index.as_retriever(similarity_top_k=top_k, filters=filters)
        nodes = retriever.retrieve(query)

        if not nodes:
            return {"type": "retrieval", "documents": []}

        documents = [
            {
                "filename": node.metadata.get("filename", "unknown"),
                "snippet" : node.text[:300].strip(),
                "score"   : round(node.score, 4) if node.score is not None else None,
            }
            for node in nodes
        ]

        return {"type": "retrieval", "documents": documents}
