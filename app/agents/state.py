from typing import TypedDict, List, Dict, Any, Optional

class AgentState(TypedDict, total=False):
    """Shared state for the multi-agent system with document structure support."""
    
    # Query and context
    query: str
    original_query: str
    merged_context: str
    
    # Research data
    internal_docs: List[Dict[str, Any]]
    web_results: List[Dict[str, Any]]
    sources: List[Dict[str, str]]
    research_report: str
    
    # Agent outputs
    risk_analysis: Dict[str, Any]
    audit_report: str
    final_report_md: str
    
    # Control flow & metadata
    next_step: str
    model: Optional[str]
    errors: List[str]
    iteration_count: int
    reflection_log: List[str]
    
    # NEW: Document structure fields (Phase 2)
    parsed_document: Optional[Any]  # ParsedDocument type
    document_structure: Dict[str, Any]
    current_section: str
    section_coverage: Dict[str, Any]
    structure_validation: Dict[str, Any]
    analysis_context: str
