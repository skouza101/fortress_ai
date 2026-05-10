import asyncio
import logging
from typing import List, Dict, Any
from qdrant_client import AsyncQdrantClient
from fastembed import TextEmbedding
import httpx

from app.core.config import settings
from app.agents.state import AgentState

logger = logging.getLogger(__name__)

class HybridResearcher:
    def __init__(self):
        self.qdrant_client = AsyncQdrantClient(url=settings.QDRANT_URL)
        self.collection_name = settings.QDRANT_COLLECTION
        self._model = None
        self.tavily_api_key = settings.TAVILY_API_KEY
        # For this implementation, I'll use the existing SearchService logic for Tavily
        self.tavily_url = "https://api.tavily.com/search"

    @property
    def model(self):
        if self._model is None:
            self._model = TextEmbedding(model_name=settings.EMBEDDING_MODEL)
        return self._model

    async def search_internal(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Search internal Qdrant vector store."""
        try:
            # Generate embedding
            query_vector = list(self.model.embed([query]))[0].tolist()
            
            search_result = await self.qdrant_client.search(
                collection_name=self.collection_name,
                query_vector=query_vector,
                limit=limit
            )
            
            return [
                {
                    "content": hit.payload.get("content", ""),
                    "source": hit.payload.get("filename", "Internal Doc"),
                    "score": hit.score,
                    "type": "internal"
                }
                for hit in search_result
            ]
        except Exception as e:
            logger.error(f"Internal search failed: {e}")
            return []

    async def search_web(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Search web using Tavily."""
        # Using a hardcoded key if not found in settings for now, 
        # but in production it should be in env.
        api_key = self.tavily_api_key
        if not api_key:
            import os
            api_key = os.getenv("TAVILY_API_KEY")

        if not api_key:
            logger.warning("TAVILY_API_KEY not found.")
            return []

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.tavily_url,
                    json={
                        "api_key": api_key,
                        "query": query,
                        "search_depth": "advanced",
                        "max_results": limit,
                    },
                    timeout=15.0
                )
                response.raise_for_status()
                data = response.json()
                results = data.get("results", [])
                
                return [
                    {
                        "content": r.get("content", ""),
                        "source": r.get("url", "Web"),
                        "title": r.get("title", ""),
                        "type": "web"
                    }
                    for r in results
                ]
        except Exception as e:
            logger.error(f"Web search failed: {e}")
            return []

    async def run(self, state: AgentState) -> AgentState:
        """Execute hybrid research."""
        query = state.get("query") or state.get("original_query")
        logger.info(f"HybridResearcher: Searching for '{query}'")

        # Run both searches in parallel
        internal_task = self.search_internal(query)
        web_task = self.search_web(query)
        
        internal_results, web_results = await asyncio.gather(internal_task, web_task)
        
        # Merge and remove duplicates (simple content-based deduplication)
        seen_content = set()
        merged_results = []
        sources = []

        for res in internal_results + web_results:
            content_snippet = res["content"][:200]
            if content_snippet not in seen_content:
                seen_content.add(content_snippet)
                merged_results.append(res)
                sources.append({"title": res.get("title", res["source"]), "url": res["source"]})

        # Format context for the next agent (no LLM summarization needed — analyst uses raw context)
        context_str = "\n\n".join([
            f"SOURCE: {res['source']}\n"
            f"TYPE: {res.get('type', 'unknown')}\n"
            f"CONTENT: {res['content']}"
            for res in merged_results
        ])

        document_structure = state.get("document_structure")
        if document_structure:
            context_str = f"DOCUMENT STRUCTURE:\n{document_structure}\n\n{context_str}"

        return {
            **state,
            "internal_docs": internal_results,
            "web_results": web_results,
            "merged_context": context_str,
            "sources": sources,
            "research_report": context_str  # Pass raw context; analyst will use it directly
        }
