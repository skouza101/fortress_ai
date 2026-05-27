import logging
from typing import List, Dict, Any
import httpx

from app.core.config import settings
from app.agents.state import AgentState
from app.services.llm import generate

logger = logging.getLogger(__name__)

class HybridResearcher:
    def __init__(self):
        self.tavily_api_key = settings.TAVILY_API_KEY
        # For this implementation, I'll use the existing SearchService logic for Tavily
        self.tavily_url = "https://api.tavily.com/search"

    async def search_internal(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Internal vector search is disabled while Qdrant is not deployed."""
        logger.info("Internal vector search skipped; Qdrant is disabled.")
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

        internal_results = await self.search_internal(query)
        web_results = await self.search_web(query)
        
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

        # Format context for the next agent
        research_context = "\n\n".join([
            f"SOURCE: {res['source']}\n"
            f"TYPE: {res.get('type', 'unknown')}\n"
            f"CONTENT: {res['content']}"
            for res in merged_results
        ])

        document_structure = state.get("document_structure")
        if document_structure:
            research_context = f"DOCUMENT STRUCTURE:\n{document_structure}\n\n{research_context}"

        # Generate a research summary report
        summary_prompt = f"""You are a Senior Legal Research Analyst synthesizing findings for a contract risk assessment.

---

## RESEARCH QUERY
"{query}"

## RAW RESEARCH DATA
{research_context}

---

## YOUR TASK

Analyze the research results above and produce a structured **Legal Research Brief** that will be consumed by a downstream Risk Analyst agent. Your output must be directly actionable — not a summary of summaries.

### Required Sections

**1. Key Legal Precedents**
- Cite specific cases, rulings, or regulatory decisions that are directly relevant
- Note the jurisdiction and year when available
- Explain how each precedent applies to the contract under review

**2. Applicable Regulations & Standards**
- List specific statutes, regulations, or industry standards (e.g., UCC Article 2, GDPR Article 28)
- Note compliance requirements that the contract should satisfy
- Flag any recent regulatory changes that affect enforceability

**3. Industry Benchmarks**
- What are standard market terms for the key clauses in question?
- Provide specific ranges or thresholds (e.g., "standard indemnification caps are typically 1-2x annual contract value")
- Note any deviation from market norms found in the research

**4. Risk Indicators**
- Highlight specific red flags or risk patterns identified in the research
- Note any enforcement trends or common dispute areas
- Flag jurisdiction-specific risks if applicable

**5. Source Reliability Assessment**
- Rate the quality and recency of the sources (High/Medium/Low confidence)
- Note any conflicting information between sources
- Identify gaps where additional research may be needed

---

## FORMAT RULES
- Be precise and cite specific sources by name/URL
- Use bullet points for scanability
- Prioritize findings by relevance to the original query
- Keep total output under 1500 words — density over volume"""
        
        research_report = await generate(
            summary_prompt,
            system_prompt="You are a meticulous legal researcher with expertise in contract law, regulatory compliance, and legal precedent analysis. You produce precise, well-sourced research briefs for senior legal analysts. Never fabricate citations.",
            model=state.get("model"),
        )

        return {
            **state,
            "internal_docs": internal_results,
            "web_results": web_results,
            "sources": sources,
            "research_report": research_report
        }
