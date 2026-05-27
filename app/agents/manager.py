import logging
from app.agents.state import AgentState
from app.services.llm import generate

logger = logging.getLogger(__name__)

class Orchestrator:
    async def run(self, state: AgentState) -> AgentState:
        """Route the query and decide on data sources."""
        logger.info(f"Orchestrator: Routing query '{state['query']}'")

        prompt = f"""You are the Strategic Orchestrator for Fortress AI — a multi-agent legal contract analysis platform.

Your task is to analyze the incoming legal query and produce an optimized research strategy that maximizes the quality and relevance of the downstream analysis.

---

## INPUT QUERY
"{state['query']}"

---

## DECISION FRAMEWORK

### Step 1: Query Optimization
Rewrite the user's query into a precise, search-optimized form. Apply these techniques:
- Expand abbreviations (e.g., "NDA" → "Non-Disclosure Agreement")
- Add relevant legal terminology that improves retrieval (e.g., "confidentiality clause enforceability")
- Remove conversational filler while preserving intent
- If the query mentions a specific jurisdiction, include it explicitly

### Step 2: Research Strategy Selection
Choose the optimal data source strategy:

| Strategy | When to Use |
|----------|-------------|
| **INTERNAL** | Query relates to previously analyzed documents, internal policies, or organizational legal standards |
| **WEB** | Query requires current regulations, recent case law, entity verification, or market-standard benchmarks |
| **BOTH** | Complex queries requiring both historical context AND current legal standards (recommended default for contract analysis) |

### Step 3: Reasoning
Provide a concise explanation (1-2 sentences) of why this strategy is optimal for the given query.

---

## OUTPUT FORMAT
Return ONLY a valid JSON object — no markdown fences, no commentary:
{{
    "optimized_query": "...",
    "strategy": "INTERNAL | WEB | BOTH",
    "reasoning": "..."
}}"""

        response = await generate(
            prompt,
            system_prompt="You are a strategic legal operations planner. You make precise routing decisions for multi-agent legal analysis workflows. Return only valid JSON.",
            model=state.get("model"),
        )
        
        # Simple extraction logic for the demo, can be improved with a proper parser
        import json
        try:
            clean_response = response.strip()
            if clean_response.startswith("```json"):
                clean_response = clean_response[7:-3].strip()
            elif clean_response.startswith("```"):
                clean_response = clean_response[3:-3].strip()
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
