from llama_index.llms.ollama import Ollama
from query_system.agents.retrieval_agent import RetrievalAgent
from query_system.agents.synthesis_agent import SynthesisAgent

# Receive the user's query, use the LLM to classify intent as either "retrieval" or "synthesis",
# then call the right agent and return whatever it returns. This is the "boss".

OLLAMA_BASE_URL = "http://localhost:11434"
OLLAMA_MODEL    = "llama3.1"

CLASSIFICATION_PROMPT = """You are a query router for a medical research system.

Given the user query below, decide whether to:
- Return a list of relevant source documents ("retrieval"), OR
- Generate a synthesized summary report ("synthesis")

Rules:
- If the user is asking to find, list, or show documents → answer: retrieval
- If the user is asking to summarize, explain, compare, or analyze → answer: synthesis
- Answer with exactly one word: retrieval or synthesis

Query: {query}
Answer:"""


class RouterAgent:
    def __init__(self, chroma_path: str = "query_system/index_store"):
        self.llm              = Ollama(model=OLLAMA_MODEL, base_url=OLLAMA_BASE_URL, request_timeout=60.0)
        self.retrieval_agent  = RetrievalAgent(chroma_path=chroma_path)
        self.synthesis_agent  = SynthesisAgent(chroma_path=chroma_path)

    def route(self, query: str, date_range: dict | None = None) -> dict:
        """
        Classifies the query and delegates to the appropriate agent.

        Returns whatever the delegated agent returns:
          - RetrievalAgent  → {"type": "retrieval", "documents": [...]}
          - SynthesisAgent  → {"type": "synthesis", "content": "...", "sources": [...]}
        """
        prompt   = CLASSIFICATION_PROMPT.format(query=query)
        response = self.llm.complete(prompt)
        intent   = response.text.strip().lower()

        # Normalize — if the LLM returns anything other than the two expected words, default to synthesis
        if "retrieval" in intent:
            intent = "retrieval"
        else:
            intent = "synthesis"

        if intent == "retrieval":
            return self.retrieval_agent.retrieve(query=query, date_range=date_range)
        else:
            return self.synthesis_agent.generate_report(query=query, date_range=date_range)
