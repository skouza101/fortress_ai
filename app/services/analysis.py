"""
Analysis pipeline service.

Orchestrates a multi-step legal contract audit using a Multi-Agent system:
  1. Ingestion (Parsing document structure)
  2. Extraction (Identifying key clauses & entities)
  3. Legal Research (Tavily + Qdrant search)
  4. Risk Audit (Analyzing liabilities & red flags)
  5. Final Synthesis (Professional Markdown report)

Each step streams SSE progress events to the frontend.
Integrated with LangGraph for robust orchestration.
"""

from __future__ import annotations

import json
import logging
import re
from typing import AsyncGenerator, Dict, Any, List

from app.agents.graph import multi_agent_graph
from app.agents.state import AgentState
from app.services.section_utils import (
    validate_section_references,
    calculate_coverage_metrics
)

logger = logging.getLogger(__name__)

async def run_pipeline(
    text: str,
    contract_type: str | None = None,
    user_type: str | None = None,
) -> AsyncGenerator[str, None]:
    """
    Run the full audit pipeline using the LangGraph orchestration layer,
    yielding SSE events for each step.
    """

    # 1. Initialize steps for the frontend UI
    steps = [
        {"id": "orchestrator", "label": "Orchestrator", "description": "Routing and planning search strategy"},
        {"id": "researcher", "label": "Hybrid Researcher", "description": "Querying Tavily and Qdrant"},
        {"id": "analyst", "label": "Risk Analyst", "description": "Extracting clauses and liabilities"},
        {"id": "auditor", "label": "Final Auditor", "description": "Synthesizing and auditing report"},
    ]
    yield _sse({"event": "steps_init", "data": {"steps": steps}})

    # 2. Setup initial state for LangGraph
    initial_state: AgentState = {
        "query": f"Analyze this {contract_type or 'contract'} for a {user_type or 'user'}.",
        "original_query": f"Full audit of contract ({contract_type or 'unknown type'})",
        "internal_docs": [],
        "web_results": [],
        "merged_context": text,
        "sources": [],
        "research_report": "",
        "risk_analysis": {},
        "audit_report": "",
        "final_report_md": "",
        "next_step": "",
        "errors": [],
        "iteration_count": 0,
        "reflection_log": []
    }

    # 3. Execute Graph with state updates
    try:
        # LangGraph can run nodes sequentially. We'll listen for state changes.
        # Note: In a production environment with complex streaming, you'd use a custom
        # callback or event handler. For now, we simulate the step progression.
        
        current_node = None
        final_risk_analysis = {}
        final_report = ""
        final_sources = []
        
        async for output in multi_agent_graph.astream(initial_state):
            # output is a dict where keys are node names and values are the state updates
            for node_name, state_update in output.items():
                logger.info(f"Pipeline Node: {node_name} finished.")
                
                # Map LangGraph nodes to frontend steps
                step_id = node_name # orchestrator, researcher, analyst, auditor
                
                # Mark previous step as completed if any
                if current_node:
                    yield _sse({"event": "step_update", "data": {"step_id": current_node, "status": "completed"}})
                
                # Mark current step as processing
                yield _sse({"event": "step_update", "data": {"step_id": step_id, "status": "processing"}})
                current_node = step_id

                # Stream specific content chunks based on the node
                if node_name == "orchestrator":
                    log = state_update.get("reflection_log", [])
                    content = log[-1] if log else "Orchestrating strategy..."
                    yield _sse({"event": "content_chunk", "data": {"chunk": content, "step_id": "orchestrator"}})
                
                elif node_name == "researcher":
                    content = state_update.get("research_report", "")
                    final_sources = state_update.get("sources", [])
                    yield _sse({"event": "content_chunk", "data": {"chunk": content, "step_id": "researcher"}})
                
                elif node_name == "analyst":
                    risk_json = state_update.get("risk_analysis", {})
                    parsed_doc = state_update.get("parsed_document")
                    
                    # Apply deduplication and validation if document structure available
                    if parsed_doc and "findings" in risk_json:
                        # Canonicalize section references and page numbers from PDF map first.
                        risk_json["findings"] = _normalize_and_enrich_findings(
                            risk_json.get("findings", []),
                            parsed_doc,
                        )

                        # Validate section references (informational only — do NOT drop findings)
                        validation_errors = validate_section_references(risk_json, parsed_doc)
                        if validation_errors:
                            logger.warning(f"Validation warnings (findings kept): {validation_errors}")

                        # Deduplicate findings — keeps all, even with imperfect section refs
                        risk_json["findings"] = _deduplicate_findings(
                            risk_json["findings"],
                            parsed_doc
                        )
        
                        # Add validation and coverage metrics
                        coverage = calculate_coverage_metrics(risk_json, parsed_doc)
        
                        risk_json["validation"] = {
                            "errors": validation_errors,
                            "coverage": coverage,
                            "status": "valid" if not validation_errors else "invalid"
                        }
                    
                    final_risk_analysis = risk_json
                    content = json.dumps(risk_json, indent=2)
                    yield _sse({"event": "content_chunk", "data": {"chunk": content, "step_id": "analyst"}})
                
                elif node_name == "auditor":
                    report_md = state_update.get("final_report_md", "")
                    final_report = report_md
                    yield _sse({"event": "content_chunk", "data": {"chunk": report_md, "step_id": "auditor"}})

        # Final completion for the last node
        if current_node:
            yield _sse({"event": "step_update", "data": {"step_id": current_node, "status": "completed"}})

        # Send the final 'done' event with the full report
        yield _sse({
            "event": "done",
            "data": {
                "risk_analysis": final_risk_analysis,
                "report": final_report,
                "sources": final_sources,
            },
        })

    except Exception as e:
        logger.error(f"Pipeline execution failed: {e}")
        if current_node:
            yield _sse({"event": "step_update", "data": {"step_id": current_node, "status": "error"}})
        yield _sse({"event": "error", "data": {"message": f"Multi-agent pipeline failed: {str(e)}"}})

def _sse(payload: dict) -> str:
    """Format a dict as an SSE data line."""
    return f"data: {json.dumps(payload)}\n\n"


def _deduplicate_findings(findings: List[dict], parsed_doc) -> List[dict]:
    """
    Remove duplicate findings for same sections and enforce section references.

    Args:
        findings: List of finding dictionaries
        parsed_doc: ParsedDocument with section map

    Returns:
        Deduplicated list of findings with validated section references
    """
    if not findings:
        return findings

    seen = {}
    deduplicated = []
    section_map = parsed_doc.section_map if parsed_doc else {}

    for finding in findings:
        section_ref = finding.get("section")

        # PHASE 3: Enforce section references - don't allow findings without them
        if not section_ref:
            logger.warning(f"Finding without section reference: {finding.get('title', 'Untitled')}")
            # Add validation error and skip this finding
            if 'validation_errors' not in finding:
                finding['validation_errors'] = []
            finding['validation_errors'].append("Missing section reference")
            continue

        # PHASE 4: Validate section exists in document structure
        if section_ref and section_ref not in section_map:
            logger.warning(f"Invalid section reference: {section_ref}")
            if 'validation_errors' not in finding:
                finding['validation_errors'] = []
            finding['validation_errors'].append(f"Section {section_ref} not found in document")
            # Still include it but mark as invalid

        # Use section + title (normalized) as unique key
        title = finding.get("title", "").lower().strip()
        key = (section_ref.lower(), title)

        if key not in seen:
            seen[key] = finding
            deduplicated.append(finding)
        else:
            # Keep the higher risk version
            existing = seen[key]
            if _compare_risk_level(finding.get("risk", "Medium"), existing.get("risk", "Medium")) > 0:
                # Replace with higher risk version
                idx = deduplicated.index(existing)
                deduplicated[idx] = finding
                seen[key] = finding
                logger.info(f"Replaced duplicate finding for {section_ref} with higher risk version")

    logger.info(f"Deduplication: {len(findings)} -> {len(deduplicated)} findings")
    return deduplicated


def _normalize_and_enrich_findings(findings: List[dict], parsed_doc) -> List[dict]:
    """
    Normalize finding section references and align page values to PDF-extracted sections.
    """
    if not findings or not parsed_doc or not getattr(parsed_doc, "section_map", None):
        return findings

    normalized: List[dict] = []
    section_map = parsed_doc.section_map

    for finding in findings:
        item = dict(finding)
        raw_section = item.get("section")
        canonical_section = _resolve_section_ref(raw_section, section_map)

        if canonical_section:
            item["section"] = canonical_section
            section = section_map.get(canonical_section)
            if section is not None:
                # Always trust PDF structure as source of truth for page mapping.
                item["page"] = section.page_num

        normalized.append(item)

    return normalized


def _resolve_section_ref(section_ref: Any, section_map: Dict[str, Any]) -> str | None:
    """
    Resolve a model-provided section reference to a canonical section number from section_map.
    Handles forms like "Section 3.2" and "3.2 Payment Terms".
    """
    if not section_ref:
        return None

    text = str(section_ref).strip()
    if not text:
        return None

    # Direct hit.
    if text in section_map:
        sec = section_map[text]
        return getattr(sec, "number", text)

    lowered = text.lower()
    if lowered in section_map:
        sec = section_map[lowered]
        return getattr(sec, "number", lowered)

    # Extract numeric section token from longer text.
    match = re.search(r"\b(\d+(?:\.\d+)*)\b", text)
    if match:
        token = match.group(1)
        if token in section_map:
            sec = section_map[token]
            return getattr(sec, "number", token)
        token_lower = token.lower()
        if token_lower in section_map:
            sec = section_map[token_lower]
            return getattr(sec, "number", token_lower)

    return None


def _compare_risk_level(a: str, b: str) -> int:
    """
    Compare risk levels.
    
    Returns:
        Positive if a > b, negative if a < b, 0 if equal
    """
    levels = {"Critical": 4, "High": 3, "Medium": 2, "Low": 1}
    return levels.get(a, 0) - levels.get(b, 0)
