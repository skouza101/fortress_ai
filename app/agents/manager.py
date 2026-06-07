import logging
from app.agents.state import AgentState
from app.services.llm import generate

logger = logging.getLogger(__name__)

class Orchestrator:
    async def run(self, state: AgentState) -> AgentState:
        """Route the query and decide on data sources."""
        logger.info(f"Orchestrator: Routing query '{state['query']}'")

        # CRITICAL: Use directive style to prevent reasoning loops
        prompt = f"""Query: {state['query']}

Output JSON with these exact keys:
- optimized_query: Rewrite query for search (string)
- strategy: Choose "INTERNAL" or "WEB" or "BOTH" (string)
- reasoning: Brief explanation (string, max 50 words)

Example:
{{"optimized_query": "vendor agreement payment terms individual contractor", "strategy": "BOTH", "reasoning": "Legal query needs both internal precedents and current web standards"}}

Your JSON:"""

        response = await generate(
            prompt,
            system_prompt="Output valid JSON only. No explanations.",
            temperature=0.1,
            max_tokens=300,
            json_mode=True
        )
        
        # Simple extraction logic for the demo, can be improved with a proper parser
        import json
        try:
            clean_response = response.strip()
            if clean_response.startswith("```json"):
                clean_response = clean_response[7:-3].strip()
            decision = json.loads(clean_response)
            
            optimized_query = decision.get("optimized_query", state["query"])
            strategy = decision.get("strategy", "BOTH")
        except:
            optimized_query = state["query"]
            strategy = "BOTH"

        return {
            **state,
            "query": optimized_query,
            "next_step": "researcher", # Control flow indicator
            "reflection_log": state.get("reflection_log", []) + [f"Orchestrator chose {strategy} strategy."]
        }
