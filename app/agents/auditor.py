import json
import logging
from typing import List, Dict, Any
from app.agents.state import AgentState
from app.services.llm import generate
from app.services.section_utils import (
    validate_section_references,
    get_section_context,
    calculate_coverage_metrics,
    format_section_reference
)

logger = logging.getLogger(__name__)

class FinalAuditor:
    async def run(self, state: AgentState) -> AgentState:
        """Audit analysis and generate final report in a single LLM call."""
        logger.info("FinalAuditor: Generating final report")

        risk_analysis = state.get("risk_analysis", {})
        parsed_doc = state.get("parsed_document")
        sources = state.get("sources", [])

        # Step 1: Validate structure references (no LLM needed — pure logic)
        validation_errors = []
        coverage_metrics = {}
        
        if parsed_doc and "findings" in risk_analysis:
            validation_errors = validate_section_references(risk_analysis, parsed_doc)
            coverage_metrics = calculate_coverage_metrics(risk_analysis, parsed_doc)
            
            if validation_errors:
                logger.warning(f"Validation errors found: {validation_errors}")
        
        # Step 2: Single combined LLM call — validate + generate final report together
        combined_prompt = self._build_combined_prompt(
            risk_analysis,
            parsed_doc,
            validation_errors,
            coverage_metrics,
            sources
        )
        final_report = await generate(
            combined_prompt,
            system_prompt="You are a professional Legal Auditor and Reporter. Validate findings and produce an actionable report."
        )

        # Build structure context for state
        structure_context = self._build_structure_context(parsed_doc) if parsed_doc else ""

        return {
            **state,
            "audit_report": final_report,
            "final_report_md": final_report,
            "structure_validation": {
                "errors": validation_errors,
                "coverage": coverage_metrics,
                "context": structure_context
            }
        }

    def _build_combined_prompt(
        self,
        risk_analysis: Dict,
        parsed_doc,
        validation_errors: List,
        coverage_metrics: Dict,
        sources: List
    ) -> str:
        """Single prompt that validates findings AND generates the final report."""

        error_context = ""
        if validation_errors:
            error_context = f"""
VALIDATION ERRORS (flag these in your report):
{chr(10).join(f"- {e}" for e in validation_errors)}
"""

        coverage_context = ""
        if coverage_metrics:
            missing = coverage_metrics.get("missing_key_clauses", [])
            coverage_context = f"""
COVERAGE: {coverage_metrics.get('key_clause_coverage_pct', 0)}% key clauses analyzed.
{f"MISSING CRITICAL CLAUSES: {', '.join(c['section'] + ' ' + c['title'] for c in missing[:5])}" if missing else ""}
"""

        doc_context = ""
        if parsed_doc:
            doc_context = f"DOCUMENT: {parsed_doc.page_count} pages, {len(parsed_doc.sections)} sections."

        sources_text = ""
        if sources:
            sources_text = "\n".join(f"- {s.get('title', s.get('url', ''))}" for s in sources[:5])

        return f"""
You are a Senior Legal Auditor. Review the risk analysis below, note any validation issues, then generate a concise professional report.

{doc_context}
{error_context}
{coverage_context}

RISK ANALYSIS:
{json.dumps(risk_analysis, indent=2)[:4000]}

SOURCES:
{sources_text or "None"}

Generate a professional Markdown report with:
1. **Executive Summary** — overall verdict (High Risk / Conditional / Compliant), key finding count
2. **Key Findings** — top risks organized by severity, with section refs and recommendations
3. **Coverage Notes** — any missing critical clauses or validation errors
4. **Sources** — list research sources used

Be concise and actionable. Skip findings with invalid section references.
"""

    def _build_validation_prompt(
        self,
        risk_analysis: Dict,
        parsed_doc,
        validation_errors: List[str],
        coverage_metrics: Dict
    ) -> str:
        """Build prompt to validate structure references and completeness."""
        
        error_context = ""
        if validation_errors:
            error_context = f"""
VALIDATION ERRORS DETECTED:
{chr(10).join(f"- {error}" for error in validation_errors)}

YOU MUST:
1. Flag these invalid references in your audit
2. Suggest corrections based on actual document sections
3. Verify all findings reference valid sections
"""
        
        coverage_context = ""
        if coverage_metrics:
            missing_clauses = coverage_metrics.get("missing_key_clauses", [])
            if missing_clauses:
                coverage_context = f"""
COVERAGE ANALYSIS:
- Section Coverage: {coverage_metrics.get('section_coverage_pct', 0)}%
- Key Clause Coverage: {coverage_metrics.get('key_clause_coverage_pct', 0)}%

MISSING KEY CLAUSES (Not Analyzed):
{chr(10).join(f"- Section {c['section']}: {c['title']} ({c['type']}) on Page {c['page']}" for c in missing_clauses[:5])}
"""
        
        doc_context = ""
        if parsed_doc:
            doc_context = f"""
DOCUMENT STRUCTURE:
- Total Pages: {parsed_doc.page_count}
- Total Sections: {len(parsed_doc.sections)}
- Key Clause Types: {', '.join(parsed_doc.structure.get('key_clauses', {}).keys())}
"""
        
        return f"""
You are a Senior Legal Analysis Auditor. Review the risk analysis for:
1. Valid section references
2. Logical consistency
3. Complete coverage of key clauses
4. Specific, actionable recommendations
5. Proper risk justification

{doc_context}

{error_context}

{coverage_context}

RISK ANALYSIS TO AUDIT:
{json.dumps(risk_analysis, indent=2)}

AUDIT TASKS:
1. Verify all section references are valid
2. Check that findings include specific contract language
3. Ensure risk levels are justified with clear reasoning
4. Confirm recommendations are actionable and specific
5. Identify any duplicate findings for the same section
6. Note any critical clauses that were not analyzed
7. Assess overall quality and completeness

Provide a structured audit report with:
- Validation status (Pass/Fail for each criterion)
- Specific issues found
- Recommendations for improvement
- Overall assessment
"""
    
    def _build_final_report_prompt(
        self,
        risk_analysis: Dict,
        parsed_doc,
        validation_result: str,
        coverage_metrics: Dict,
        sources: List
    ) -> str:
        """Build final report with structure context."""
        
        structure_overview = ""
        if parsed_doc:
            structure_overview = f"""
## Document Structure Overview

- **Total Pages**: {parsed_doc.page_count}
- **Total Sections**: {len(parsed_doc.sections)}
- **Hierarchy Levels**: {len(parsed_doc.structure.get('hierarchy', []))}

### Key Clauses Identified:
{self._format_key_clauses_summary(parsed_doc)}
"""
        
        coverage_summary = ""
        if coverage_metrics:
            coverage_summary = f"""
## Analysis Coverage

- **Sections Analyzed**: {coverage_metrics.get('analyzed_sections', 0)} of {coverage_metrics.get('total_sections', 0)} ({coverage_metrics.get('section_coverage_pct', 0)}%)
- **Key Clauses Covered**: {coverage_metrics.get('covered_key_sections', 0)} of {coverage_metrics.get('total_key_sections', 0)} ({coverage_metrics.get('key_clause_coverage_pct', 0)}%)

{self._format_missing_clauses(coverage_metrics.get('missing_key_clauses', []))}
"""
        
        return f"""
You are a Legal Reporting Expert. Generate a comprehensive, professional report.

{structure_overview}

{coverage_summary}

AUDITOR VALIDATION:
{validation_result}

RISK ANALYSIS FINDINGS:
{json.dumps(risk_analysis, indent=2)}

SOURCES:
{json.dumps(sources, indent=2) if sources else "No external sources"}

REPORT REQUIREMENTS:

1. **Executive Summary**
   - Overall verdict (Compliant/Conditional/High Risk)
   - Key findings count and severity distribution
   - Critical action items

2. **Findings by Section**
   - Organize findings by document section order
   - Include section number, title, and page reference
   - Show risk level, justification, and recommendations
   - Quote specific contract language

3. **Risk Assessment**
   - Categorize by risk level (High/Medium/Low)
   - Prioritize by urgency
   - Provide clear remediation steps

4. **Coverage Analysis**
   - Note which key clauses were analyzed
   - Highlight any critical sections not reviewed
   - Suggest areas for deeper analysis if needed

5. **Sources & References**
   - List all research sources
   - Include relevant legal standards or regulations

FORMAT: Professional Markdown with clear headers, bullet points, and tables where appropriate.
TONE: Clear, actionable, and business-focused.
"""
    
    def _format_key_clauses_summary(self, parsed_doc) -> str:
        """Format key clauses for report."""
        if not parsed_doc or not hasattr(parsed_doc, 'structure'):
            return "None identified"
        
        key_clauses = parsed_doc.structure.get("key_clauses", {})
        if not key_clauses:
            return "None identified"
        
        lines = []
        for clause_type, sections in key_clauses.items():
            lines.append(f"- **{clause_type.title()}**: {len(sections)} sections")
        
        return "\n".join(lines)
    
    def _format_missing_clauses(self, missing_clauses: List[Dict]) -> str:
        """Format missing key clauses."""
        if not missing_clauses:
            return ""
        
        lines = ["### Key Clauses Not Analyzed:"]
        for clause in missing_clauses[:5]:
            lines.append(
                f"- Section {clause['section']}: {clause['title']} "
                f"({clause['type']}) on Page {clause['page']}"
            )
        
        if len(missing_clauses) > 5:
            lines.append(f"- ... and {len(missing_clauses) - 5} more")
        
        return "\n".join(lines)
    
    def _build_structure_context(self, parsed_doc) -> str:
        """Build structure context summary."""
        if not parsed_doc:
            return ""
        
        context = [
            "## Document Structure Context",
            f"- **Pages**: {parsed_doc.page_count}",
            f"- **Total Sections**: {len(parsed_doc.sections)}",
            f"- **Hierarchy Levels**: {len(parsed_doc.structure.get('hierarchy', []))}",
            "",
            "### Key Clauses by Type:"
        ]
        
        for clause_type, sections in parsed_doc.structure.get('key_clauses', {}).items():
            context.append(f"- **{clause_type.title()}**: {len(sections)} sections")
            for sec_ref in sections[:2]:  # Show first 2 of each type
                context.append(f"  - {sec_ref}")
            if len(sections) > 2:
                context.append(f"  - ... and {len(sections) - 2} more")
        
        return "\n".join(context)
