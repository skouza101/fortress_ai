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

        # Step 1: Validate structure references
        validation_errors = []
        coverage_metrics = {}
        
        if parsed_doc and "findings" in risk_analysis:
            validation_errors = validate_section_references(risk_analysis, parsed_doc)
            coverage_metrics = calculate_coverage_metrics(risk_analysis, parsed_doc)
            
            if validation_errors:
                logger.warning(f"Validation errors found: {validation_errors}")
        
        # Step 2: Structure validation audit
        validation_prompt = self._build_validation_prompt(
            risk_analysis,
            parsed_doc,
            validation_errors,
            coverage_metrics
        )
        validation_result = await generate(
            validation_prompt,
            system_prompt="You are a meticulous Quality Assurance Auditor for legal analysis. You catch errors that others miss. Your validation ensures only accurate, well-supported findings reach the client. Be rigorous but fair.",
            model=state.get("model"),
        )

        # Step 3: Final report with structure context
        report_prompt = self._build_final_report_prompt(
            risk_analysis,
            parsed_doc,
            validation_result,
            coverage_metrics,
            sources
        )
        final_report = await generate(
            report_prompt,
            system_prompt="You are a senior legal reporting specialist who produces boardroom-ready contract risk assessment reports. Your reports are clear, precise, and actionable — they drive executive decision-making on whether to sign, negotiate, or reject contracts. Use professional formatting with appropriate visual hierarchy.",
            model=state.get("model"),
        )

        # Build structure context for state
        structure_context = self._build_structure_context(parsed_doc) if parsed_doc else ""

        return {
            **state,
            "audit_report": validation_result,
            "final_report_md": final_report,
            "structure_validation": {
                "errors": validation_errors,
                "coverage": coverage_metrics,
                "context": structure_context
            }
        }
    
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
## ⚠️ AUTOMATED VALIDATION ERRORS DETECTED

The following issues were flagged by the automated section-reference validator:
{chr(10).join(f"- {error}" for error in validation_errors)}

**YOUR TASK**: Assess each error — determine if it invalidates the finding or if the finding can be salvaged with a corrected reference.
"""
        
        coverage_context = ""
        if coverage_metrics:
            missing_clauses = coverage_metrics.get("missing_key_clauses", [])
            if missing_clauses:
                coverage_context = f"""
## COVERAGE GAP ANALYSIS

**Current Coverage Metrics:**
- Section Coverage: {coverage_metrics.get('section_coverage_pct', 0)}%
- Key Clause Coverage: {coverage_metrics.get('key_clause_coverage_pct', 0)}%

**Critical Sections NOT Analyzed:**
{chr(10).join(f"- Section {c['section']}: {c['title']} ({c['type']}) — Page {c['page']}" for c in missing_clauses[:5])}

**YOUR TASK**: Flag these gaps prominently in your audit. Missing key clauses represent potential unidentified risks.
"""
        
        doc_context = ""
        if parsed_doc:
            doc_context = f"""
## DOCUMENT STRUCTURE REFERENCE
- Total Pages: {parsed_doc.page_count}
- Total Sections: {len(parsed_doc.sections)}
- Key Clause Types: {', '.join(parsed_doc.structure.get('key_clauses', {}).keys())}
"""
        
        return f"""You are the Quality Assurance Auditor for Fortress AI's multi-agent legal analysis pipeline. Your role is the final quality gate before findings reach the client.

---

{doc_context}

{error_context}

{coverage_context}

## RISK ANALYSIS TO AUDIT
{json.dumps(risk_analysis, indent=2)}

---

## AUDIT CRITERIA

Score each finding against these quality gates (Pass/Fail):

| Criterion | Standard |
|-----------|----------|
| **Section Accuracy** | Section reference matches a real section in the document |
| **Evidence Quality** | Finding includes exact contract language (verbatim quote) |
| **Risk Justification** | Risk level is supported by specific legal/commercial reasoning, not just assertion |
| **Recommendation Specificity** | Recommendation includes concrete revision language, not generic advice |
| **Uniqueness** | No duplicate findings covering the same section and risk |
| **Priority Alignment** | Priority ranking correctly reflects severity and commercial impact |

## ADDITIONAL VALIDATION CHECKS

1. **Logical Consistency**: Do related findings contradict each other?
2. **Severity Calibration**: Are risk levels proportionate? (e.g., a missing comma shouldn't be "High")
3. **Completeness**: Are obvious high-risk clause types (indemnification, limitation of liability, termination, IP, confidentiality) addressed?
4. **Cross-Reference Integrity**: Do `related_sections` references point to valid sections?

---

## OUTPUT FORMAT

Provide a structured audit report with:

### Overall Quality Score
Rate the analysis quality: **Excellent / Good / Needs Improvement / Insufficient**

### Finding-by-Finding Audit
For each finding, provide:
- Finding title and section
- Pass/Fail on each criterion
- Specific issues (if any)
- Recommended corrections

### Coverage Assessment
- Which critical clause types are adequately covered?
- Which are missing and need analysis?

### Improvement Recommendations
- Ordered list of specific improvements the analysis team should make"""
    
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
        
        return f"""You are generating the final Contract Risk Assessment Report for Fortress AI. This report will be presented directly to the end user (legal professional or business executive). It must be polished, authoritative, and immediately actionable.

---

{structure_overview}

{coverage_summary}

## QUALITY AUDIT RESULTS
{validation_result}

## RISK ANALYSIS FINDINGS
{json.dumps(risk_analysis, indent=2)}

## RESEARCH SOURCES
{json.dumps(sources, indent=2) if sources else "No external sources consulted."}

---

## REPORT TEMPLATE

Generate the report using this exact structure:

### 1. Executive Summary
- **Overall Verdict**: Use one of: ✅ **SIGN** (Low risk) | ⚠️ **NEGOTIATE** (Medium risk, revisions needed) | 🚫 **REJECT** (High risk, fundamental issues) | ⚖️ **SEEK COUNSEL** (Complex legal issues requiring attorney review)
- **Risk Distribution**: X Critical / X High / X Medium / X Low findings
- **Top 3 Action Items**: The most urgent issues that must be addressed before signing
- **Overall Risk Score**: Provide a score out of 100 (100 = no risk, 0 = maximum risk)

### 2. Critical & High-Risk Findings
For each finding (ordered by priority):
- **Section Reference**: Section X.X — "Section Title" (Page N)
- **Risk Level**: 🔴 Critical / 🟠 High
- **Issue**: Clear, concise description of the risk
- **Contract Language**: > Exact quote from the contract (blockquote format)
- **Impact**: What happens if this is not addressed
- **Recommended Revision**: Specific replacement language

### 3. Medium & Low-Risk Findings
Same structure as above but grouped separately for readability:
- 🟡 Medium risks
- 🟢 Low risks

### 4. Risk Matrix Summary
Present a Markdown table with columns: Section | Risk Level | Issue | Priority | Status

### 5. Coverage Analysis
- Sections analyzed vs. total sections
- Key clauses identified and assessed
- Any sections NOT reviewed (with recommendation to review)

### 6. Sources & Methodology
- Research sources consulted (with URLs if available)
- Analysis methodology used
- Confidence level for each major finding

---

## FORMATTING RULES
- Use clean Markdown with clear visual hierarchy
- Use emoji risk indicators consistently (🔴🟠🟡🟢)
- Use blockquotes (>) for contract language citations
- Use tables for structured comparisons — NEVER wrap tables in code fences
- Keep paragraphs short and scannable
- Use bold for key terms and findings
- Write in confident, professional tone — no hedging language"""
    
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
