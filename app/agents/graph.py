import logging
from typing import Dict, Any
from langgraph.graph import StateGraph, END

from app.agents.state import AgentState
from app.agents.manager import Orchestrator
from app.agents.researcher import HybridResearcher
from app.agents.analyst import LegalRiskAnalyst
from app.agents.auditor import FinalAuditor

logger = logging.getLogger(__name__)

# Initialize agents
orchestrator = Orchestrator()
researcher = HybridResearcher()
analyst = LegalRiskAnalyst()
auditor = FinalAuditor()

# Define node functions that wrap the agent classes
async def orchestrator_node(state: AgentState) -> AgentState:
    return await orchestrator.run(state)

async def researcher_node(state: AgentState) -> AgentState:
    return await researcher.run(state)

async def analyst_node(state: AgentState) -> AgentState:
    return await analyst.run(state)

async def auditor_node(state: AgentState) -> AgentState:
    return await auditor.run(state)

# Build the graph
workflow = StateGraph(AgentState)

# Add nodes
workflow.add_node("orchestrator", orchestrator_node)
workflow.add_node("researcher", researcher_node)
workflow.add_node("analyst", analyst_node)
workflow.add_node("auditor", auditor_node)

# Set entry point
workflow.set_entry_point("orchestrator")

# Define edges (Linear for this complex dependency chain)
workflow.add_edge("orchestrator", "researcher")
workflow.add_edge("researcher", "analyst")
workflow.add_edge("analyst", "auditor")
workflow.add_edge("auditor", END)

# Compile the graph
multi_agent_graph = workflow.compile()

# Helper to run the graph
async def run_legal_audit(query: str, text_context: str = "", model: str | None = None):
    """Entry point for the Multi-Agent Orchestration layer."""
    initial_state: AgentState = {
        "query": query,
        "original_query": query,
        "internal_docs": [],
        "web_results": [],
        "merged_context": text_context,
        "sources": [],
        "research_report": "",
        "risk_analysis": {},
        "audit_report": "",
        "final_report_md": "",
        "next_step": "",
        "model": model,
        "errors": [],
        "iteration_count": 0,
        "reflection_log": []
    }
    
    final_state = await multi_agent_graph.ainvoke(initial_state)
    return final_state
