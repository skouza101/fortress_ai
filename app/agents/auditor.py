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
        """Audit analysis with structure validation and generate final report."""
        logger.info("FinalAuditor: Validating structure-aware analysis")

        research = state.get("research_report", "")
        risk_analysis = state.get("risk_analysis", {})
        parsed_doc = state.get("parsed_document")
        sources = state.get("sources", [])

        # Step 1: Validate structure references (pure logic, no LLM)
        validation_errors = []
        coverage_metrics = {}
        
        if parsed_doc and "findings" in risk_analysis:
            validation_errors = validate_section_references(risk_analysis, parsed_doc)
            coverage_metrics = calculate_coverage_metrics(risk_analysis, parsed_doc)
            
            if validation_errors:
                logger.warning(f"Validation errors found: {validation_errors}")
        
        # Step 2: Generate report from template (no LLM calls - instant)
        final_report = self._generate_template_report(
            risk_analysis,
            validation_errors,
            coverage_metrics,
            sources
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
    
    def _generate_template_report(
        self,
        risk_analysis: Dict,
        validation_errors: List,
        coverage_metrics: Dict,
        sources: List
    ) -> str:
        """Generate report from template without LLM call."""
        findings = risk_analysis.get("findings", [])
        
        report = "# Contract Risk Analysis Report\n\n"
        report += "## Executive Summary\n\n"
        report += f"**Total Findings:** {len(findings)}\n\n"
        
        # Group by risk level
        high_risk = [f for f in findings if f.get("risk", "").lower() == "high"]
        medium_risk = [f for f in findings if f.get("risk", "").lower() == "medium"]
        low_risk = [f for f in findings if f.get("risk", "").lower() == "low"]
        
        report += f"- **High Risk:** {len(high_risk)}\n"
        report += f"- **Medium Risk:** {len(medium_risk)}\n"
        report += f"- **Low Risk:** {len(low_risk)}\n\n"
        
        report += "## Findings\n\n"
        for i, finding in enumerate(findings, 1):
            report += f"### {i}. {finding.get('title', 'Untitled')}\n\n"
            report += f"- **Section:** {finding.get('section', 'N/A')}\n"
            report += f"- **Page:** {finding.get('page', 'N/A')}\n"
            report += f"- **Risk Level:** {finding.get('risk', 'Medium')}\n"
            report += f"- **Issue:** {finding.get('justification', '')}\n"
            report += f"- **Recommendation:** {finding.get('recommendation', '')}\n\n"
            
            if finding.get('contract_text'):
                report += f"**Contract Language:**\n> {finding['contract_text']}\n\n"
        
        if validation_errors:
            report += "## Validation Notes\n\n"
            for error in validation_errors[:5]:
                report += f"- {error}\n"
            report += "\n"
        
        if sources:
            report += "## Sources\n\n"
            for source in sources[:5]:
                report += f"- {source.get('title', source.get('url', 'Unknown'))}\n"
        
        return report
    
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
