import json
import logging
from typing import Dict, Any, List
from app.agents.state import AgentState
from app.services.llm import generate
from app.services.section_utils import (
    get_section_context,
    get_related_sections,
    validate_section_references,
    format_section_reference
)

logger = logging.getLogger(__name__)

class LegalRiskAnalyst:
    async def run(self, state: AgentState) -> AgentState:
        """Analyze legal risks with document structure awareness."""
        logger.info("LegalRiskAnalyst: Analyzing risks with structure context")
        
        # Get document structure if available
        parsed_doc = state.get("parsed_document")
        context = state.get("merged_context", "")
        research = state.get("research_report", "")
        query = state.get("original_query", "")
        
        # Build structure-aware prompt
        if parsed_doc:
            prompt = self._build_structure_aware_prompt(state, parsed_doc)
        else:
            # Fallback to basic prompt if no structure available
            prompt = self._build_basic_prompt(query, research, context)
        
        response = await generate(
            prompt,
            system_prompt="You are an elite Legal Risk Analyst with 20+ years of experience in contract litigation and risk assessment. You identify risks that junior analysts miss. You never fabricate section references. Return JSON only.",
            model=state.get("model"),
        )
        
        # Parse and validate response
        risk_analysis = self._parse_and_validate_response(response, parsed_doc)
        
        return {
            **state,
            "risk_analysis": risk_analysis
        }
    
    def _build_structure_aware_prompt(self, state: AgentState, parsed_doc) -> str:
        """Build prompt requiring structure-aware analysis with PDF-extracted sections only."""
        query = state.get("original_query", "")
        research = state.get("research_report", "")
        context = state.get("merged_context", "")
        
        # Build document overview
        doc_overview = self._build_document_overview(parsed_doc)
        
        # Get key clauses summary
        key_clauses_text = self._format_key_clauses(parsed_doc)

        # PHASE 4: Create explicit list of valid sections from PDF
        valid_sections = sorted(parsed_doc.section_map.keys())
        sections_list = "\n".join([
            f"  - {sec}: {parsed_doc.section_map[sec].title} (Page {parsed_doc.section_map[sec].page_num})"
            for sec in valid_sections[:20]  # Show first 20 to avoid overwhelming prompt
        ])

        if len(valid_sections) > 20:
            sections_list += f"\n  - ...and {len(valid_sections) - 20} more sections"

        return f"""You are a Senior Legal Risk Analyst performing a clause-level risk assessment on a contract with full document structure awareness.

---

## DOCUMENT METADATA

{doc_overview}

{key_clauses_text}

---

## VALIDATED SECTION INDEX (Extracted from PDF)

**CRITICAL**: You MUST only reference sections from this exact list. Any fabricated or modified section reference will be rejected by the downstream validation system.

{sections_list}

---

## ANALYSIS QUERY
{query}

## RESEARCH BRIEF (from Legal Researcher agent)
{research[:2000] if research else "No external research available."}

## DOCUMENT TEXT CONTEXT
{context[:3000]}

---

## ANALYSIS METHODOLOGY

Apply the following risk assessment framework to each relevant section:

### Risk Classification Criteria

| Level | Definition | Examples |
|-------|-----------|----------|
| **High** | Immediate legal exposure, uncapped financial liability, or regulatory non-compliance | Unlimited indemnification, missing limitation of liability, one-sided IP assignment |
| **Medium** | Significant commercial risk that creates unfavorable terms but is not immediately dangerous | Aggressive auto-renewal, broad non-compete, above-market payment terms |
| **Low** | Minor deviations from best practice that should be noted but are not urgent | Missing governing law specification, informal amendment procedures |

### Analysis Checklist
For each finding, you MUST address:
1. ☐ **What** — The specific contractual provision creating risk
2. ☐ **Why** — The legal/commercial reasoning for the risk classification
3. ☐ **How bad** — Quantify impact where possible (e.g., "uncapped vs. industry standard of 1-2x annual value")
4. ☐ **What to do** — Provide specific, implementable revision language (not "consult counsel")
5. ☐ **Related exposure** — Identify cross-references to other sections that amplify or mitigate this risk

---

## VALIDATION REQUIREMENTS (STRICTLY ENFORCED)

1. **Section references** — MUST exactly match the Validated Section Index above
2. **Page numbers** — MUST match the PDF-extracted page for that section
3. **Contract text** — MUST be exact verbatim quotes from the document, not paraphrased
4. **No invented sections** — Do NOT create, modify, or approximate section numbers
5. **Findings without valid section references will be REJECTED**

---

## OUTPUT FORMAT

Return ONLY valid JSON (no markdown fences):
{{
  "findings": [
    {{
      "section": "3.2",
      "page": 5,
      "title": "Uncapped Indemnification Obligation",
      "risk": "High",
      "justification": "Section 3.2 imposes unlimited indemnification on the receiving party for 'any and all claims arising from' the agreement. This exceeds market standard, which typically caps indemnification at 1-2x the annual contract value. The absence of a liability cap creates unbounded financial exposure, particularly concerning given the broad 'arising from' trigger language which could include third-party claims unrelated to the core services.",
      "contract_text": "Party B shall indemnify, defend, and hold harmless Party A from and against any and all claims, damages, losses, and expenses arising from or related to this Agreement.",
      "recommendation": "Replace with: 'Party B's aggregate liability for indemnification under this Section shall not exceed [2x] the total fees paid under this Agreement in the twelve (12) months preceding the claim. Indemnification obligations shall be limited to third-party claims directly caused by Party B's material breach or gross negligence.'",
      "priority": 1,
      "related_sections": ["7.1", "9.2"],
      "clause_type": "indemnification"
    }}
  ]
}}

IMPORTANT: Prioritize findings by severity and commercial impact (priority 1 = most critical). Include ALL identified risks, not just the top 3."""
    
    def _build_basic_prompt(self, query: str, research: str, context: str) -> str:
        """Fallback prompt when no document structure is available."""
        return f"""You are a Senior Legal Risk Analyst performing a comprehensive contract risk assessment.

---

## ANALYSIS QUERY
{query}

## RESEARCH BRIEF (from Legal Researcher agent)
{research[:2000] if research else "No external research available."}

## CONTRACT TEXT
{context[:30000]}

---

## ANALYSIS FRAMEWORK

Perform a systematic risk assessment covering these categories:

### 1. Red Flags (Highest Priority)
Identify provisions that create immediate legal exposure:
- Uncapped liability or indemnification
- One-sided termination rights
- Broad IP assignment clauses
- Non-compete overreach
- Waiver of jury trial / class action waiver
- Automatic renewal traps with unfavorable terms

### 2. Financial Penalties & Exposure
Identify all provisions with financial consequences:
- Late payment penalties and interest rates
- Early termination fees
- Liquidated damages clauses
- Audit rights and cost allocation
- Insurance requirements

### 3. Compliance Obligations
Identify all material obligations and deadlines:
- Reporting requirements and frequencies
- Data protection and privacy obligations (GDPR, CCPA)
- Regulatory compliance representations
- Certification or licensing requirements
- Record retention obligations

### Risk Classification
For each item, classify as:
- **High**: Immediate legal or financial exposure
- **Medium**: Significant commercial disadvantage
- **Low**: Minor concern or best-practice deviation

---

## OUTPUT FORMAT

Return ONLY valid JSON (no markdown fences):
{{
    "red_flags": [
        {{"issue": "...", "severity": "High/Med/Low", "description": "Detailed explanation of the risk and its commercial impact", "recommendation": "Specific suggested revision language"}}
    ],
    "penalties": [
        {{"type": "...", "severity": "High/Med/Low", "impact": "Quantified financial impact where possible"}}
    ],
    "obligations": [
        {{"task": "...", "deadline": "...", "description": "Specific compliance requirement with consequences for non-compliance"}}
    ],
    "summary": "2-3 sentence executive summary of the overall risk posture"
}}"""
    
    def _build_document_overview(self, parsed_doc) -> str:
        """Build document overview section."""
        if not parsed_doc:
            return ""
        
        structure = parsed_doc.structure if hasattr(parsed_doc, 'structure') else {}
        key_clauses = structure.get("key_clauses", {})
        
        overview = [
            "DOCUMENT OVERVIEW:",
            f"- Total Pages: {parsed_doc.page_count}",
            f"- Total Sections: {len(parsed_doc.sections)}",
            f"- Key Clause Types: {', '.join(key_clauses.keys()) if key_clauses else 'None identified'}"
        ]
        
        return "\n".join(overview)
    
    def _format_key_clauses(self, parsed_doc) -> str:
        """Format key clauses for prompt context."""
        if not parsed_doc or not hasattr(parsed_doc, 'structure'):
            return ""
        
        key_clauses = parsed_doc.structure.get("key_clauses", {})
        if not key_clauses:
            return ""
        
        lines = ["KEY CLAUSES TO ANALYZE:"]
        for clause_type, sections in key_clauses.items():
            lines.append(f"\n{clause_type.upper()}:")
            for sec_ref in sections[:3]:  # Show first 3 of each type
                lines.append(f"  - {sec_ref}")
            if len(sections) > 3:
                lines.append(f"  - ... and {len(sections) - 3} more")
        
        return "\n".join(lines)
    
    def _format_related_sections(self, sections: List[Dict]) -> str:
        """Format related sections for prompt context."""
        if not sections:
            return "None"
        
        return "\n".join([
            f"- {sec['number']} {sec['title']} (Page {sec['page']}) [{sec.get('relationship', 'related')}]"
            for sec in sections
        ])
    
    def _parse_and_validate_response(self, response: str, parsed_doc) -> Dict:
        """Parse response and validate section references with strict enforcement."""
        try:
            # Clean response
            clean_response = response.strip()
            if clean_response.startswith("```json"):
                clean_response = clean_response[7:-3].strip()
            elif clean_response.startswith("```"):
                clean_response = clean_response[3:-3].strip()

            analysis = json.loads(clean_response)

            # PHASE 3: Strict validation of section references
            if parsed_doc and "findings" in analysis:
                # Track findings with missing/invalid section references
                validated_findings = []
                validation_errors = []

                for finding in analysis["findings"]:
                    section_ref = finding.get("section")
                    page_num = finding.get("page")
                    contract_text = finding.get("contract_text")

                    # PHASE 4: Enforce mandatory section references
                    if not section_ref:
                        validation_errors.append(
                            f"Finding missing section reference: {finding.get('title', 'Untitled')}"
                        )
                        logger.warning(f"Rejecting finding without section reference: {finding.get('title', 'Untitled')}")
                        continue

                    # Validate section exists in document
                    if section_ref and hasattr(parsed_doc, 'section_map') and section_ref not in parsed_doc.section_map:
                        validation_errors.append(
                            f"Invalid section reference '{section_ref}' in finding: {finding.get('title', 'Untitled')}"
                        )
                        # Still include but mark as invalid
                        if 'validation_errors' not in finding:
                            finding['validation_errors'] = []
                        finding['validation_errors'].append(f"Section {section_ref} not found in document")

                    # Validate page number if section reference exists
                    if section_ref and not page_num:
                        validation_errors.append(
                            f"Finding for section {section_ref} missing page number: {finding.get('title', 'Untitled')}"
                        )
                        if 'validation_errors' not in finding:
                            finding['validation_errors'] = []
                        finding['validation_errors'].append("Missing page number")

                    # Validate contract text if section reference exists
                    if section_ref and not contract_text:
                        validation_errors.append(
                            f"Finding for section {section_ref} missing contract text: {finding.get('title', 'Untitled')}"
                        )
                        if 'validation_errors' not in finding:
                            finding['validation_errors'] = []
                        finding['validation_errors'].append("Missing specific contract language")

                    validated_findings.append(finding)

                # Update analysis with validated findings
                analysis["findings"] = validated_findings

                # Add validation summary
                if validation_errors:
                    analysis["validation_errors"] = validation_errors
                    logger.warning(f"Section reference validation errors: {validation_errors}")

            return analysis

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse analysis JSON: {e}")
            return {
                "error": "Failed to parse analysis",
                "raw_output": response,
                "findings": [],
                "red_flags": [],
                "penalties": [],
                "obligations": [],
                "summary": "Analysis failed to format correctly."
            }
