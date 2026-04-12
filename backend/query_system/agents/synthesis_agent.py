# query_system/agents/synthesis_agent.py
# Generates a structured markdown report from retrieved chunks using Ollama via LlamaIndex.

from llama_index.core import VectorStoreIndex, StorageContext
from llama_index.vector_stores.chroma import ChromaVectorStore
from llama_index.embeddings.ollama import OllamaEmbedding
from llama_index.llms.ollama import Ollama as LlamaOllama
import chromadb
from crewai import Agent, Task, Crew, LLM

OLLAMA_BASE_URL = "http://localhost:11434"
OLLAMA_MODEL    = "llama3.1"

SYNTHESIS_SYSTEM_PROMPT = """You are a medical research synthesis agent for AbbVie.
Generate structured, accurate summaries based ONLY on the source documents provided.

Rules:
1. Use ONLY information from the provided source documents. Do not use outside knowledge.
2. If the documents do not contain enough information, clearly say so.
3. Cite the source filename for each claim using the format: [source: filename]
4. Output well-structured markdown with clear headings and bullet points.
5. Never fabricate data, statistics, or conclusions not present in the sources.
"""


class SynthesisAgent:
    def __init__(self, chroma_path: str = "query_system/index_store"):
        # ── LLM for LlamaIndex (retrieval) ────────────────────────────────────
        self.llama_llm = LlamaOllama(
            model           = OLLAMA_MODEL,
            base_url        = OLLAMA_BASE_URL,
            request_timeout = 120.0,
        )

        # ── LLM for CrewAI — must use crewai.LLM with ollama/ prefix ──────────
        self.crewai_llm = LLM(
            model    = f"ollama/{OLLAMA_MODEL}",
            base_url = OLLAMA_BASE_URL,
        )

        # ── Embeddings (local via Ollama) ─────────────────────────────────────
        self.embed_model = OllamaEmbedding(
            model_name = OLLAMA_MODEL,
            base_url   = OLLAMA_BASE_URL,
        )

        # ── ChromaDB + LlamaIndex storage ─────────────────────────────────────
        chroma_client     = chromadb.PersistentClient(path=chroma_path)
        chroma_collection = chroma_client.get_or_create_collection("documents")
        vector_store      = ChromaVectorStore(chroma_collection=chroma_collection)
        storage_context   = StorageContext.from_defaults(vector_store=vector_store)

        self.index = VectorStoreIndex.from_vector_store(
            vector_store    = vector_store,
            storage_context = storage_context,
            embed_model     = self.embed_model,
        )

        # ── CrewAI agent — explicitly using Ollama LLM ────────────────────────
        self.crewai_agent = Agent(
            role      = "Medical Research Synthesis Specialist",
            goal      = "Generate accurate, cited markdown summaries from AbbVie research documents",
            backstory = (
                "You are an expert at synthesizing pharmaceutical research. "
                "You only draw conclusions from provided source documents and always cite your sources."
            ),
            llm       = self.crewai_llm,
            verbose   = False,
        )

    def generate_report(self, query: str, date_range: dict | None = None) -> dict:
        """
        Retrieves relevant chunks and synthesizes a markdown report.

        Args:
            query      : The user's synthesis question.
            date_range : Optional {"start": "YYYY-MM-DD", "end": "YYYY-MM-DD"}

        Returns:
            {
                "type"   : "synthesis",
                "content": <markdown report string>,
                "sources": [<filename>, ...]
            }
        """
        # ── Build metadata filters for date range ─────────────────────────────
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
                filters = MetadataFilters(
                    filters   = filter_list,
                    condition = FilterCondition.AND,
                )

        # ── Retrieve top chunks ────────────────────────────────────────────────
        retriever = self.index.as_retriever(
            similarity_top_k  = 8,
            filters           = filters,
        )
        nodes = retriever.retrieve(query)

        if not nodes:
            return {
                "type"   : "synthesis",
                "content": "No documents matched your query and date range.",
                "sources": [],
            }

        # ── Build sources block for prompt ────────────────────────────────────
        sources_block = ""
        filenames     = []
        for node in nodes:
            filename = node.metadata.get("filename", "unknown")
            filenames.append(filename)
            sources_block += f'\n<source filename="{filename}">\n{node.text}\n</source>\n'

        # ── CrewAI task + crew ────────────────────────────────────────────────
        task = Task(
            description = (
                f"Query: {query}\n\n"
                f"Source documents:\n{sources_block}\n\n"
                "Using ONLY the source documents above, generate a comprehensive markdown report. "
                "Include a 'Sources' section at the end listing all filenames you drew from."
            ),
            expected_output = "A structured markdown report with headings, bullet points, and a Sources section.",
            agent           = self.crewai_agent,
        )

        crew   = Crew(agents=[self.crewai_agent], tasks=[task], verbose=False)
        result = crew.kickoff()

        # Strip CrewAI internal reasoning lines from output
        content = str(result)
        content = "\n".join(
            line for line in content.splitlines()
            if not line.strip().startswith("Thought:")
        ).strip()

        synthesis_result = {
            "type"   : "synthesis",
            "content": content,
            "sources": list(set(filenames)),
        }

        # Save as formatted .docx in generated_docs/
        try:
            from query_system.docx_writer import save_as_docx
            docx_path = save_as_docx(synthesis_result, query=query)
            synthesis_result["docx_path"] = str(docx_path)
        except Exception as e:
            synthesis_result["docx_path"] = None
            synthesis_result["docx_error"] = str(e)

        return synthesis_result
