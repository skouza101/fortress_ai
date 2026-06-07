"""
HybridResearcher agent.

Strategy:
- When contract text is present in merged_context (the normal case), SKIP Tavily web
  search entirely. Web search for legal contract terms returns generic templates that
  pollute the analyst's context and cause hallucination.
- Instead, search Qdrant for internal precedents (useful if the user has seeded their
  own legal document library), and generate a structural pre-analysis of the contract
  to help the analyst focus on the right areas.
- Tavily is only used when there is NO contract text and the query is genuinely a
  legal research question (e.g., "What are Maryland's MBE requirements?").
"""

import asyncio
import logging
from typing import List, Dict, Any

from qdrant_client import AsyncQdrantClient
from fastembed import TextEmbedding
import httpx

from app.core.config import settings
from app.agents.state import AgentState
from app.services.llm import generate

logger = logging.getLogger(__name__)


class HybridResearcher:
    def __init__(self):
        self.qdrant_client = AsyncQdrantClient(url=settings.QDRANT_URL)
        self.collection_name = settings.QDRANT_COLLECTION
        self._model = None
        self.tavily_api_key = settings.TAVILY_API_KEY
        self.tavily_url = "https://api.tavily.com/search"

    @property
    def model(self):
        if self._model is None:
            self._model = TextEmbedding(model_name=settings.EMBEDDING_MODEL)
        return self._model

    async def _embed(self, query: str) -> list:
        """Run blocking fastembed in a thread pool so we don't block the event loop."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            lambda: list(self.model.embed([query]))[0].tolist()
        )

    async def search_internal(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Search internal Qdrant vector store for precedent documents."""
        try:
            query_vector = await self._embed(query)
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
            logger.warning(f"Qdrant search failed (likely not seeded yet): {e}")
            return []

    async def search_web(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Web search via Tavily.
        Only called when there is NO contract text to analyze — i.e., pure
        legal research questions. Never called during contract audit pipelines.
        """
        api_key = self.tavily_api_key
        if not api_key:
            import os
            api_key = os.getenv("TAVILY_API_KEY")
        if not api_key:
            logger.warning("TAVILY_API_KEY not set — skipping web search")
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
                return [
                    {
                        "content": r.get("content", ""),
                        "source": r.get("url", "Web"),
                        "title": r.get("title", ""),
                        "type": "web"
                    }
                    for r in data.get("results", [])
                ]
        except Exception as e:
            logger.error(f"Web search failed: {e}")
            return []

    async def _generate_contract_pre_analysis(
        self, contract_text: str, query: str
    ) -> str:
        """
        Instead of searching the web, read the contract and produce a structured
        summary of what clause types are present, what's missing, and what the
        analyst should pay close attention to.

        This replaces Tavily for contract audit pipelines and eliminates hallucination
        from irrelevant web results.
        """
        prompt = f"""You are a legal document classifier. Read the contract excerpt and produce a structured pre-analysis.

CONTRACT EXCERPT:
{contract_text[:3000]}

Return ONLY this JSON. Be concise and factual.
Rules:
- "clause_types_present": only clause types explicitly present in the text
- "clause_types_missing": clause types typically expected but absent from the excerpt
- "high_attention_areas": specific section NUMBERS with risky language (e.g. "Section 4.1 — uncapped indemnification"). Do NOT flag OCR artifacts, typos, or formatting issues.
- "regulatory_context": only regulations explicitly named in the text

{{
  "contract_type": "...",
  "parties": ["...", "..."],
  "governing_law": "...",
  "contract_duration": "...",
  "clause_types_present": ["..."],
  "clause_types_missing": ["..."],
  "high_attention_areas": ["..."],
  "regulatory_context": ["..."]
}}

Return ONLY the JSON. No markdown. No invented citations. No commentary on typos or OCR artifacts."""
        response = await generate(
            prompt,
            system_prompt=(
                "You are a legal document classifier. "
                "Return only valid JSON. Do not invent case citations or statute numbers."
            ),
            temperature=0.1,
            max_tokens=2000,
            json_mode=True,
        )

        # Parse and reformat as readable research report
        import json, re
        try:
            clean = re.sub(r'^```(?:json)?\s*|\s*```$', '', response.strip(), flags=re.MULTILINE).strip()
            data = json.loads(clean)

            lines = [
                f"Contract Type: {data.get('contract_type', 'Unknown')}",
                f"Parties: {', '.join(data.get('parties', ['Not identified']))}",
                f"Governing Law: {data.get('governing_law', 'Not specified')}",
                f"Duration: {data.get('contract_duration', 'Not specified')}",
                "",
                "Clause Types Present:",
                *[f"  - {c}" for c in data.get("clause_types_present", [])],
                "",
                "Clause Types Missing (compared to standard practice):",
                *[f"  - {c}" for c in data.get("clause_types_missing", [])],
                "",
                "High-Attention Areas for Risk Analysis:",
                *[f"  - {a}" for a in data.get("high_attention_areas", [])],
                "",
                "Regulatory Context:",
                *[f"  - {r}" for r in data.get("regulatory_context", [])],
            ]
            return "\n".join(lines)

        except (json.JSONDecodeError, ValueError):
            # If parsing fails, return the raw response rather than nothing
            logger.warning("Pre-analysis JSON parse failed — using raw response")
            return response[:2000]

    async def run(self, state: AgentState) -> AgentState:
        """
        Execute research.

        Decision logic:
        - If contract text is present in merged_context → pre-analyse the contract
          structure + search Qdrant for internal precedents. Skip Tavily.
        - If no contract text → use Tavily for legal research questions.

        CRITICAL: Never overwrite merged_context. That field holds the contract text
        and must be preserved unchanged for the analyst.
        """
        query = state.get("query") or state.get("original_query", "")
        contract_text = state.get("merged_context", "").strip()

        has_contract = bool(contract_text)
        logger.info(
            f"HybridResearcher: has_contract={has_contract}, query='{query[:80]}'"
        )

        internal_results: List[Dict] = []
        web_results: List[Dict] = []
        sources: List[Dict] = []
        research_report: str = ""

        if has_contract:
            # ── Contract audit mode ──────────────────────────
            # 1. Search Qdrant for any internal precedent documents
            internal_results = await self.search_internal(query)

            # 2. Generate a structured pre-analysis of the contract itself
            #    This gives the analyst focused guidance without any hallucination risk
            research_report = await self._generate_contract_pre_analysis(
                contract_text, query
            )

            # Add internal Qdrant hits as sources if any exist
            for r in internal_results:
                sources.append({"title": r.get("source", "Internal Doc"), "url": r["source"]})

            logger.info(
                f"HybridResearcher: contract pre-analysis complete, "
                f"internal_hits={len(internal_results)}"
            )

        else:
            # ── Pure research mode (no contract uploaded) ────
            # Use both Qdrant and Tavily for open-ended legal questions
            internal_task = self.search_internal(query)
            web_task = self.search_web(query)
            internal_results, web_results = await asyncio.gather(internal_task, web_task)

            all_results = internal_results + web_results
            if not all_results:
                research_report = "No research results found. Proceeding with available context."
            else:
                seen = set()
                for res in all_results:
                    snippet = res["content"][:200]
                    if snippet not in seen:
                        seen.add(snippet)
                        sources.append({
                            "title": res.get("title", res["source"]),
                            "url": res["source"]
                        })

                context_str = "\n\n".join([
                    f"SOURCE: {r['source']}\nCONTENT: {r['content']}"
                    for r in all_results[:8]
                ])
                summary_prompt = f"""You are a legal researcher. Summarize the following sources for the query: "{query}"

SOURCES:
{context_str[:4000]}

Provide a concise summary of relevant legal standards, precedents, and obligations.
Only cite information actually present in the sources above. Do not invent case citations or statute numbers.
"""
                research_report = await generate(
                    summary_prompt,
                    system_prompt=(
                        "You are a legal researcher. Summarize only what the sources contain. "
                        "Never invent citations, case names, or statute numbers."
                    ),
                    temperature=0.2,
                )

        # Return only researcher-owned fields. Never touch merged_context.
        return {
            "internal_docs": internal_results,
            "web_results":   web_results,
            "sources":       sources,
            "research_report": research_report,
        }

# Made with Bob
