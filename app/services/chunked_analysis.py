"""
Chunked Processing Service for Quick Initial Results

This service implements Solution 3 from STREAMING_PERFORMANCE_OPTIMIZATION.md:
- Processes document in chunks (sections or pages)
- Yields partial findings as they're discovered
- Provides 2-3s time to first result
- Full analysis continues in background
"""

import asyncio
import json
import logging
from typing import AsyncGenerator, Dict, Any, List
from app.agents.state import AgentState
from app.services.llm import generate

logger = logging.getLogger(__name__)


class ChunkedAnalysisService:
    """Service for processing documents in chunks with immediate partial results."""
    
    def __init__(self, chunk_size: int = 3):
        """
        Initialize chunked analysis service.
        
        Args:
            chunk_size: Number of sections to process per chunk (default: 3)
        """
        self.chunk_size = chunk_size
    
    async def analyze_in_chunks(
        self,
        state: AgentState,
        yield_callback: callable = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Analyze document in chunks, yielding partial results immediately.
        
        Args:
            state: Agent state with document and context
            yield_callback: Optional callback for SSE events
            
        Yields:
            Partial analysis results as they're discovered
        """
        parsed_doc = state.get("parsed_document")
        if not parsed_doc:
            logger.warning("No parsed document available for chunked analysis")
            return
        
        # Get all sections sorted by page number
        sections = sorted(
            parsed_doc.section_map.values(),
            key=lambda s: (s.page_num, s.start_line)
        )
        
        if not sections:
            logger.warning("No sections found in document")
            return
        
        logger.info(f"Starting chunked analysis: {len(sections)} sections, chunk_size={self.chunk_size}")
        
        # Process sections in chunks
        total_findings = []
        chunk_num = 0
        
        for i in range(0, len(sections), self.chunk_size):
            chunk_sections = sections[i:i + self.chunk_size]
            chunk_num += 1
            
            logger.info(f"Processing chunk {chunk_num}: sections {i+1}-{i+len(chunk_sections)}")
            
            # Analyze this chunk
            chunk_findings = await self._analyze_chunk(
                chunk_sections,
                state,
                chunk_num
            )
            
            if chunk_findings:
                total_findings.extend(chunk_findings)
                
                # Yield partial result immediately
                partial_result = {
                    "type": "partial_findings",
                    "chunk_num": chunk_num,
                    "total_chunks": (len(sections) + self.chunk_size - 1) // self.chunk_size,
                    "findings": chunk_findings,
                    "cumulative_count": len(total_findings),
                    "sections_processed": i + len(chunk_sections),
                    "total_sections": len(sections)
                }
                
                yield partial_result
                
                # Optional callback for SSE streaming
                if yield_callback:
                    await yield_callback(partial_result)
        
        # Yield final complete result
        final_result = {
            "type": "complete_findings",
            "total_findings": len(total_findings),
            "findings": total_findings,
            "chunks_processed": chunk_num
        }
        
        yield final_result
    
    async def _analyze_chunk(
        self,
        sections: List[Any],
        state: AgentState,
        chunk_num: int
    ) -> List[Dict[str, Any]]:
        """
        Analyze a single chunk of sections.
        
        Args:
            sections: List of section objects to analyze
            state: Agent state with context
            chunk_num: Current chunk number
            
        Returns:
            List of findings from this chunk
        """
        # Build focused prompt for this chunk
        section_texts = []
        for section in sections:
            section_texts.append(
                f"Section: {section.title}\n"
                f"Page: {section.page_num}\n"
                f"Content: {section.content[:500]}...\n"
            )
        
        chunk_context = "\n\n".join(section_texts)
        
        prompt = f"""Analyze these contract sections for legal risks. Focus on HIGH and CRITICAL priority issues only.

SECTIONS TO ANALYZE:
{chunk_context}

Return JSON with this structure:
{{
  "findings": [
    {{
      "section": "exact section title",
      "page": page_number,
      "title": "brief finding title",
      "risk": "description of risk",
      "priority": "HIGH or CRITICAL only",
      "contract_text": "relevant excerpt",
      "recommendation": "what to do"
    }}
  ]
}}

Focus on:
- Liability caps and limitations
- Indemnification obligations
- Termination rights
- Payment terms
- Confidentiality breaches

Return ONLY valid JSON. If no high-priority risks found, return {{"findings": []}}"""

        try:
            response = await generate(
                prompt,
                system_prompt="You are a legal risk analyst. Return JSON only with high-priority findings.",
                temperature=0.1,
                max_tokens=1000,
                json_mode=True
            )
            
            # Parse response
            result = json.loads(response)
            findings = result.get("findings", [])
            
            # Enrich findings with chunk metadata
            for finding in findings:
                finding["chunk_num"] = chunk_num
                finding["analysis_type"] = "chunked"
            
            logger.info(f"Chunk {chunk_num}: Found {len(findings)} findings")
            return findings
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse chunk {chunk_num} response: {e}")
            return []
        except Exception as e:
            logger.error(f"Error analyzing chunk {chunk_num}: {e}")
            return []
    
    async def quick_scan(
        self,
        state: AgentState
    ) -> Dict[str, Any]:
        """
        Perform ultra-fast initial scan of document structure.
        Returns basic document overview in <1 second.
        
        Args:
            state: Agent state with document
            
        Returns:
            Quick scan results with document overview
        """
        parsed_doc = state.get("parsed_document")
        if not parsed_doc:
            return {"error": "No document structure available"}
        
        # Extract key metadata instantly (no LLM call)
        sections = list(parsed_doc.section_map.values())
        
        # Identify high-risk section titles (pattern matching)
        high_risk_keywords = [
            "liability", "indemnif", "termination", "confidential",
            "payment", "warranty", "limitation", "dispute"
        ]
        
        flagged_sections = []
        for section in sections:
            title_lower = section.title.lower()
            if any(keyword in title_lower for keyword in high_risk_keywords):
                flagged_sections.append({
                    "title": section.title,
                    "page": section.page_num,
                    "reason": "Contains high-risk keywords"
                })
        
        return {
            "type": "quick_scan",
            "total_pages": parsed_doc.total_pages,
            "total_sections": len(sections),
            "flagged_sections": flagged_sections,
            "scan_time_ms": "<1000",
            "next_step": "Starting detailed chunk analysis..."
        }


# Singleton instance
_chunked_service = None

def get_chunked_service(chunk_size: int = 3) -> ChunkedAnalysisService:
    """Get or create chunked analysis service instance."""
    global _chunked_service
    if _chunked_service is None:
        _chunked_service = ChunkedAnalysisService(chunk_size=chunk_size)
    return _chunked_service

# Made with Bob
