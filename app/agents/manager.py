import logging
from app.agents.state import AgentState
from app.services.llm import generate

logger = logging.getLogger(__name__)

class Orchestrator:
    async def run(self, state: AgentState) -> AgentState:
        """Route the query and decide on data sources (no LLM call needed)."""
        query = state["query"]
        logger.info(f"Orchestrator: Routing query '{query}' → BOTH strategy (fast path)")

        return {
            **state,
            "query": query,
            "next_step": "researcher",
            "reflection_log": state.get("reflection_log", []) + ["Orchestrator chose BOTH strategy."]
        }
