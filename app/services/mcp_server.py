"""
MCP Server for PDF Research with Anti-Hallucination Tools

This module implements discrete, auditable tools for PDF access that prevent
hallucination by providing structured, enumerable operations rather than
dumping full PDFs into context.

Architecture:
- Each tool call is logged with session ID for audit trails
- Tools return structured data with source citations
- No tool dumps entire PDF - all access is targeted and traceable
"""

from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime
import logging
import hashlib
from pathlib import Path

from app.services.document_parser import ParsedDocument, DocumentBlock
from app.services.document_structure import Section

logger = logging.getLogger(__name__)


@dataclass
class ToolCall:
    """Audit trail entry for MCP tool calls"""
    tool_name: str
    parameters: Dict[str, Any]
    result: Any
    timestamp: datetime
    session_id: str
    success: bool
    error_message: Optional[str] = None


@dataclass
class CitationChunk:
    """A chunk with full citation metadata for anti-hallucination"""
    content: str
    page_num: int
    section_number: str
    section_title: str
    chunk_id: str
    bbox: Optional[Tuple[float, float, float, float]] = None
    block_index: int = -1


class MCPPDFServer:
    """
    MCP Server providing discrete, auditable PDF access tools.
    
    Each tool is designed to prevent hallucination by:
    1. Returning only requested data (no context dumping)
    2. Including source citations in every response
    3. Logging all calls for audit trails
    4. Failing explicitly when data doesn't exist
    """
    
    def __init__(self):
        self.audit_log: List[ToolCall] = []
        self._document_cache: Dict[str, ParsedDocument] = {}
    
    def register_document(self, doc_id: str, parsed_doc: ParsedDocument) -> None:
        """Register a parsed document for MCP tool access"""
        self._document_cache[doc_id] = parsed_doc
        logger.info(f"Registered document {doc_id} with {parsed_doc.page_count} pages")
    
    def get_page(
        self,
        doc_id: str,
        page_num: int,
        session_id: str
    ) -> Dict[str, Any]:
        """
        Tool: get_page
        Fetch exact page text on demand with citation metadata.
        
        Returns:
            {
                "success": bool,
                "page_num": int,
                "content": str,
                "sections": List[str],  # Sections on this page
                "citation": str,  # [SOURCE: page X]
                "error": Optional[str]
            }
        """
        tool_call = ToolCall(
            tool_name="get_page",
            parameters={"doc_id": doc_id, "page_num": page_num},
            result=None,
            timestamp=datetime.utcnow(),
            session_id=session_id,
            success=False
        )
        
        try:
            doc = self._document_cache.get(doc_id)
            if not doc:
                raise ValueError(f"Document {doc_id} not found")
            
            if page_num < 1 or page_num > doc.page_count:
                raise ValueError(f"Page {page_num} out of range (1-{doc.page_count})")
            
            # Extract blocks for this page
            page_blocks = [b for b in doc.blocks if b.page_num == page_num]
            content = "\n\n".join(b.text for b in page_blocks)
            
            # Find sections on this page
            page_sections = [
                f"{s.number} {s.title}"
                for s in doc.sections
                if s.page_num == page_num
            ]
            
            result = {
                "success": True,
                "page_num": page_num,
                "content": content,
                "sections": page_sections,
                "citation": f"[SOURCE: page {page_num}]",
                "error": None
            }
            
            tool_call.result = result
            tool_call.success = True
            
        except Exception as e:
            error_msg = str(e)
            result = {
                "success": False,
                "page_num": page_num,
                "content": "",
                "sections": [],
                "citation": "",
                "error": error_msg
            }
            tool_call.result = result
            tool_call.error_message = error_msg
            logger.error(f"get_page failed: {error_msg}")
        
        finally:
            self.audit_log.append(tool_call)
        
        return result
    
    def search_pdf(
        self,
        doc_id: str,
        query: str,
        session_id: str,
        max_results: int = 5
    ) -> Dict[str, Any]:
        """
        Tool: search_pdf
        Semantic search over chunked PDF with citation anchoring.
        
        Returns:
            {
                "success": bool,
                "query": str,
                "results": List[{
                    "content": str,
                    "page": int,
                    "section": str,
                    "citation": str,  # [SOURCE: page X, section Y]
                    "relevance_score": float
                }],
                "error": Optional[str]
            }
        """
        tool_call = ToolCall(
            tool_name="search_pdf",
            parameters={"doc_id": doc_id, "query": query, "max_results": max_results},
            result=None,
            timestamp=datetime.utcnow(),
            session_id=session_id,
            success=False
        )
        
        try:
            doc = self._document_cache.get(doc_id)
            if not doc:
                raise ValueError(f"Document {doc_id} not found")
            
            # Simple keyword-based search (can be enhanced with embeddings)
            query_lower = query.lower()
            matches = []
            
            for section in doc.sections:
                if not section.content:
                    continue
                
                content_lower = section.content.lower()
                if query_lower in content_lower:
                    # Calculate simple relevance score
                    score = content_lower.count(query_lower) / len(content_lower.split())
                    
                    matches.append({
                        "content": section.content[:500],  # Limit to 500 chars
                        "page": section.page_num,
                        "section": f"{section.number} {section.title}",
                        "citation": f"[SOURCE: page {section.page_num}, section {section.number}]",
                        "relevance_score": min(score * 100, 1.0)
                    })
            
            # Sort by relevance and limit results
            matches.sort(key=lambda x: x["relevance_score"], reverse=True)
            matches = matches[:max_results]
            
            result = {
                "success": True,
                "query": query,
                "results": matches,
                "error": None
            }
            
            tool_call.result = result
            tool_call.success = True
            
        except Exception as e:
            error_msg = str(e)
            result = {
                "success": False,
                "query": query,
                "results": [],
                "error": error_msg
            }
            tool_call.result = result
            tool_call.error_message = error_msg
            logger.error(f"search_pdf failed: {error_msg}")
        
        finally:
            self.audit_log.append(tool_call)
        
        return result
    
    def get_section(
        self,
        doc_id: str,
        section_ref: str,
        session_id: str
    ) -> Dict[str, Any]:
        """
        Tool: get_section
        Retrieve a specific named section with full context.
        
        Returns:
            {
                "success": bool,
                "section_number": str,
                "section_title": str,
                "page": int,
                "content": str,
                "clause_type": str,
                "citation": str,
                "related_sections": List[str],
                "error": Optional[str]
            }
        """
        tool_call = ToolCall(
            tool_name="get_section",
            parameters={"doc_id": doc_id, "section_ref": section_ref},
            result=None,
            timestamp=datetime.utcnow(),
            session_id=session_id,
            success=False
        )
        
        try:
            doc = self._document_cache.get(doc_id)
            if not doc:
                raise ValueError(f"Document {doc_id} not found")
            
            # Try to find section by number or title
            section = doc.section_map.get(section_ref.lower())
            if not section:
                raise ValueError(f"Section '{section_ref}' not found")
            
            # Find related sections (same clause type)
            related = [
                f"{s.number} {s.title}"
                for s in doc.sections
                if s.clause_type == section.clause_type and s.number != section.number
            ][:3]  # Limit to 3 related sections
            
            result = {
                "success": True,
                "section_number": section.number,
                "section_title": section.title,
                "page": section.page_num,
                "content": section.content,
                "clause_type": section.clause_type,
                "citation": f"[SOURCE: page {section.page_num}, section {section.number}]",
                "related_sections": related,
                "error": None
            }
            
            tool_call.result = result
            tool_call.success = True
            
        except Exception as e:
            error_msg = str(e)
            result = {
                "success": False,
                "section_number": "",
                "section_title": "",
                "page": 0,
                "content": "",
                "clause_type": "",
                "citation": "",
                "related_sections": [],
                "error": error_msg
            }
            tool_call.result = result
            tool_call.error_message = error_msg
            logger.error(f"get_section failed: {error_msg}")
        
        finally:
            self.audit_log.append(tool_call)
        
        return result
    
    def cross_check(
        self,
        doc_id: str,
        claim: str,
        source_id: str,
        session_id: str
    ) -> Dict[str, Any]:
        """
        Tool: cross_check
        Verify a claim against a specific chunk/section.
        
        This is the verification loop tool that prevents hallucination
        by validating LLM claims against actual document content.
        
        Returns:
            {
                "success": bool,
                "claim": str,
                "source_id": str,
                "verified": bool,
                "confidence": float,  # 0.0-1.0
                "actual_content": str,
                "discrepancy": Optional[str],
                "error": Optional[str]
            }
        """
        tool_call = ToolCall(
            tool_name="cross_check",
            parameters={"doc_id": doc_id, "claim": claim, "source_id": source_id},
            result=None,
            timestamp=datetime.utcnow(),
            session_id=session_id,
            success=False
        )
        
        try:
            doc = self._document_cache.get(doc_id)
            if not doc:
                raise ValueError(f"Document {doc_id} not found")
            
            # Parse source_id (format: "page_X_section_Y" or just section number)
            section = None
            if source_id in doc.section_map:
                section = doc.section_map[source_id]
            else:
                # Try to extract section from source_id
                for sec in doc.sections:
                    if sec.number in source_id or sec.title.lower() in source_id.lower():
                        section = sec
                        break
            
            if not section:
                raise ValueError(f"Source '{source_id}' not found")
            
            # Simple verification: check if claim keywords appear in section content
            claim_lower = claim.lower()
            content_lower = section.content.lower()
            
            # Extract key terms from claim (simple approach)
            claim_terms = set(claim_lower.split())
            content_terms = set(content_lower.split())
            
            # Calculate overlap
            overlap = claim_terms & content_terms
            confidence = len(overlap) / len(claim_terms) if claim_terms else 0.0
            
            verified = confidence > 0.5  # Threshold for verification
            
            discrepancy = None
            if not verified:
                discrepancy = f"Claim contains terms not found in source: {claim_terms - content_terms}"
            
            result = {
                "success": True,
                "claim": claim,
                "source_id": source_id,
                "verified": verified,
                "confidence": confidence,
                "actual_content": section.content[:300],  # First 300 chars
                "discrepancy": discrepancy,
                "error": None
            }
            
            tool_call.result = result
            tool_call.success = True
            
        except Exception as e:
            error_msg = str(e)
            result = {
                "success": False,
                "claim": claim,
                "source_id": source_id,
                "verified": False,
                "confidence": 0.0,
                "actual_content": "",
                "discrepancy": None,
                "error": error_msg
            }
            tool_call.result = result
            tool_call.error_message = error_msg
            logger.error(f"cross_check failed: {error_msg}")
        
        finally:
            self.audit_log.append(tool_call)
        
        return result
    
    def get_metadata(
        self,
        doc_id: str,
        session_id: str
    ) -> Dict[str, Any]:
        """
        Tool: get_metadata
        Return document title, author, date, and structure overview.
        
        Returns:
            {
                "success": bool,
                "title": str,
                "author": str,
                "date": str,
                "page_count": int,
                "section_count": int,
                "key_clause_types": List[str],
                "error": Optional[str]
            }
        """
        tool_call = ToolCall(
            tool_name="get_metadata",
            parameters={"doc_id": doc_id},
            result=None,
            timestamp=datetime.utcnow(),
            session_id=session_id,
            success=False
        )
        
        try:
            doc = self._document_cache.get(doc_id)
            if not doc:
                raise ValueError(f"Document {doc_id} not found")
            
            result = {
                "success": True,
                "title": doc.metadata.get("title", "Untitled"),
                "author": doc.metadata.get("author", "Unknown"),
                "date": doc.metadata.get("creationDate", "Unknown"),
                "page_count": doc.page_count,
                "section_count": len(doc.sections),
                "key_clause_types": list(doc.structure.get("key_clauses", {}).keys()),
                "error": None
            }
            
            tool_call.result = result
            tool_call.success = True
            
        except Exception as e:
            error_msg = str(e)
            result = {
                "success": False,
                "title": "",
                "author": "",
                "date": "",
                "page_count": 0,
                "section_count": 0,
                "key_clause_types": [],
                "error": error_msg
            }
            tool_call.result = result
            tool_call.error_message = error_msg
            logger.error(f"get_metadata failed: {error_msg}")
        
        finally:
            self.audit_log.append(tool_call)
        
        return result
    
    def get_audit_trail(self, session_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get audit trail of all tool calls, optionally filtered by session.
        
        This provides full transparency into what the LLM accessed.
        """
        if session_id:
            calls = [c for c in self.audit_log if c.session_id == session_id]
        else:
            calls = self.audit_log
        
        return [
            {
                "tool": c.tool_name,
                "parameters": c.parameters,
                "timestamp": c.timestamp.isoformat(),
                "success": c.success,
                "error": c.error_message
            }
            for c in calls
        ]
    
    def create_citation_chunks(
        self,
        doc_id: str,
        chunk_size: int = 500,
        overlap: int = 100
    ) -> List[CitationChunk]:
        """
        Create citation-anchored chunks for RAG.
        
        Each chunk includes:
        - Full citation metadata (page, section, bbox)
        - Chunk ID for precise reference
        - Overlap for context continuity
        """
        doc = self._document_cache.get(doc_id)
        if not doc:
            return []
        
        chunks: List[CitationChunk] = []
        
        for section in doc.sections:
            if not section.content:
                continue
            
            # Split section content into chunks
            content = section.content
            start = 0
            chunk_idx = 0
            
            while start < len(content):
                end = start + chunk_size
                chunk_text = content[start:end]
                
                # Create unique chunk ID
                chunk_id = f"{doc_id}_{section.number}_{chunk_idx}"
                
                chunks.append(CitationChunk(
                    content=chunk_text,
                    page_num=section.page_num,
                    section_number=section.number,
                    section_title=section.title,
                    chunk_id=chunk_id,
                    block_index=section.start_block_index
                ))
                
                start += chunk_size - overlap
                chunk_idx += 1
        
        logger.info(f"Created {len(chunks)} citation chunks for document {doc_id}")
        return chunks


# Singleton instance
_mcp_server: Optional[MCPPDFServer] = None


def get_mcp_server() -> MCPPDFServer:
    """Get or create the singleton MCP server instance"""
    global _mcp_server
    if _mcp_server is None:
        _mcp_server = MCPPDFServer()
    return _mcp_server


