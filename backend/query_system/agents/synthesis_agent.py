"""
synthesis_agent.py
------------------
Generates a structured, cited markdown report from retrieved document chunks
using a local Ollama LLM via CrewAI.

Called from query_router._run_synthesis() when the router classifies the
query as synthesis intent.

Design notes:
- Uses nomic-embed-text (same model as ingest.py) so vector similarity is valid.
- All metadata keys and collection name match ingest.py conventions.
- The SYNTHESIS_SYSTEM_PROMPT explicitly grounds the LLM in source documents only,
  preventing hallucination — critical for pharmaceutical/research use.
- SynthesisAgent is instantiated lazily on first call to avoid connecting to
  ChromaDB and Ollama at import time (safe if services are not yet running).
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Optional

import chromadb
from crewai import LLM, Agent, Crew, Task
from llama_index.core import Settings, StorageContext, VectorStoreIndex
from llama_index.embeddings.ollama import OllamaEmbedding
from llama_index.vector_stores.chroma import ChromaVectorStore

# ---------------------------------------------------------------------------
# Configuration — all overridable via environment variables, matching
# the conventions used in ingest.py and retrieval_agent.py.
# ---------------------------------------------------------------------------
BACKEND_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_CHROMA = BACKEND_ROOT / "index_store" / "chroma"

CHROMA_PATH = Path(os.getenv("CHROMA_PATH", DEFAULT_CHROMA)).resolve()
CHROMA_COLLECTION = os.getenv("CHROMA_COLLECTION", "reports")   # must match ingest.py

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_EMBED_MODEL = os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text")  # must match ingest.py
OLLAMA_LLM_MODEL = os.getenv("OLLAMA_LLM_MODEL", "llama3.1")

SYNTHESIS_TOP_K = int(os.getenv("SYNTHESIS_TOP_K", "8"))

# ---------------------------------------------------------------------------
# System prompt — grounds the LLM strictly in provided source documents.
# "Never fabricate" is load-bearing for a research/pharma context.
# ---------------------------------------------------------------------------
SYNTHESIS_SYSTEM_PROMPT = """You are a medical research synthesis agent for AbbVie.
Generate structured, accurate summaries based ONLY on the source documents provided.

Rules:
1. Use ONLY information from the provided source documents. Do not use outside knowledge.
2. If the documents do not contain enough information, clearly say so.
3. Cite the source filename for each claim using the format: [source: filename]
4. Output well-structured markdown with clear headings and bullet points.
5. Never fabricate data, statistics, or conclusions not present in the sources.
"""


class _SynthesisAgent:
    """
    Internal class — do not instantiate directly. Use run_synthesis() instead.
    Connects to ChromaDB and sets up the CrewAI agent on first use.
    """

    def __init__(self) -> None:
        # Embedding model — must be nomic-embed-text to match the vectors
        # written by ingest.py. Using a different model here would make all
        # cosine similarity scores meaningless.
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

        self.index = VectorStoreIndex.from_vector_store(
            vector_store=vector_store,
            storage_context=storage_context,
            embed_model=embed_model,
        )

        # CrewAI LLM — separate from the embedding model. Uses ollama/ prefix
        # as required by CrewAI's LiteLLM backend.
        self.crewai_llm = LLM(
            model=f"ollama/{OLLAMA_LLM_MODEL}",
            base_url=OLLAMA_BASE_URL,
        )

        self.crewai_agent = Agent(
            role="Medical Research Synthesis Specialist",
            goal="Generate accurate, cited markdown summaries from AbbVie research documents",
            backstory=(
                "You are an expert at synthesizing pharmaceutical research. "
                "You only draw conclusions from provided source documents and always cite your sources."
            ),
            llm=self.crewai_llm,
            system_template=SYNTHESIS_SYSTEM_PROMPT,
            verbose=False,
        )

    def generate_report(
        self,
        query: str,
        date_range: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """
        Retrieves the most relevant chunks for the query, then asks the LLM
        to synthesize a grounded markdown report from them.
        """
        # Build optional date range filters using the same metadata key
        # ("doc_date") that ingest.py writes. Sandra's branch used "document_date"
        # which would silently skip all filtering — this is the corrected version.
        filters = None
        if date_range:
            from llama_index.core.vector_stores import (
                FilterCondition,
                FilterOperator,
                MetadataFilter,
                MetadataFilters,
            )
            filter_list = []
            date_from = date_range.get("from") or date_range.get("start")
            date_to = date_range.get("to") or date_range.get("end")
            if date_from:
                filter_list.append(
                    MetadataFilter(
                        key="doc_date",
                        value=date_from,
                        operator=FilterOperator.GTE,
                    )
                )
            if date_to:
                filter_list.append(
                    MetadataFilter(
                        key="doc_date",
                        value=date_to,
                        operator=FilterOperator.LTE,
                    )
                )
            if filter_list:
                filters = MetadataFilters(filters=filter_list, condition=FilterCondition.AND)

        retriever_kwargs: dict[str, Any] = {"similarity_top_k": SYNTHESIS_TOP_K}
        if filters:
            retriever_kwargs["filters"] = filters

        retriever = self.index.as_retriever(**retriever_kwargs)
        nodes = retriever.retrieve(query)

        if not nodes:
            return {
                "type": "synthesis",
                "content": "No documents matched your query. Try broadening your search or adding more documents.",
                "sources": [],
            }

        # Build the sources block injected into the prompt. Each chunk is wrapped
        # in a <source> tag so the LLM can cleanly attribute claims.
        sources_block = ""
        filenames: list[str] = []
        for node in nodes:
            meta = node.metadata or {}
            filename = meta.get("filename", "unknown")
            filenames.append(filename)
            sources_block += f'\n<source filename="{filename}">\n{node.get_content()}\n</source>\n'

        task = Task(
            description=(
                f"Query: {query}\n\n"
                f"Source documents:\n{sources_block}\n\n"
                "Using ONLY the source documents above, generate a comprehensive markdown report. "
                "Include a 'Sources' section at the end listing all filenames you drew from."
            ),
            expected_output=(
                "A structured markdown report with headings, bullet points, and a Sources section."
            ),
            agent=self.crewai_agent,
        )

        crew = Crew(agents=[self.crewai_agent], tasks=[task], verbose=False)
        result = crew.kickoff()

        # TODO: Save generated report to docs/generated_reports/ once pipeline is stable.
        # When ready:
        #   1. Add "Match the section structure of the source documents above" to the task.
        #   2. After kickoff(), write str(result) to a timestamped .md file.
        #   3. Keep docs/generated_reports/ excluded from ingest_docs() to prevent
        #      the LLM from synthesizing from its own prior outputs (hallucination drift).

        return {
            "type": "synthesis",
            "content": str(result),
            "sources": list(set(filenames)),
        }


# ---------------------------------------------------------------------------
# Lazy singleton — agent is created only on first synthesis call so the
# server starts up even if ChromaDB or Ollama isn't ready yet.
# ---------------------------------------------------------------------------
_agent_instance: Optional[_SynthesisAgent] = None


def run_synthesis(
    query: str,
    date_range: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """
    Module-level entry point called by query_router._run_synthesis().
    Initializes the agent on first call; subsequent calls reuse the instance.
    """
    global _agent_instance

    try:
        if _agent_instance is None:
            _agent_instance = _SynthesisAgent()
        return _agent_instance.generate_report(query, date_range=date_range)
    except Exception as exc:  # noqa: BLE001
        return {
            "type": "synthesis",
            "content": (
                f"Synthesis failed: {exc}\n\n"
                "Check that Ollama is running and the index has been populated "
                "(`python -m query_system.ingest`)."
            ),
            "sources": [],
        }
