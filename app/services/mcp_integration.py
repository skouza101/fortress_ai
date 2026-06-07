"""
MCP + RAG Integration Module

This module integrates the MCP server and enhanced vector DB
into the existing Fortress AI analysis pipeline.
"""

import logging
import uuid
from typing import Dict, Any, Optional
from pathlib import Path

from app.services.document_parser import ParsedDocument, get_parser
from app.services.mcp_server import get_mcp_server
from app.services.vector_db_enhanced import get_enhanced_vector_db

logger = logging.getLogger(__name__)


class MCPIntegrationService:
    """
    Service to integrate MCP + RAG into existing pipeline.
    
    Handles:
    - Document registration with MCP server
    - Citation chunk creation
    - Enhanced vector DB indexing
    - Session management for audit trails
    """
    
    def __init__(self):
        self.mcp = get_mcp_server()
        self.vector_db = get_enhanced_vector_db()
        self.parser = get_parser()
    
    async def process_uploaded_document(
        self,
        file_id: str,
        pdf_bytes: bytes,
        filename: str,
        conversation_id: str
    ) -> Dict[str, Any]:
        """
        Process uploaded PDF with MCP + RAG integration.
        
        Args:
            file_id: Unique file identifier
            pdf_bytes: Raw PDF bytes
            filename: Original filename
            conversation_id: Conversation ID for session tracking
        
        Returns:
            Dict with parsed_doc, chunks_created, indexed status
        """
        logger.info(f"Processing document {filename} with MCP integration")
        
        try:
            # 1. Parse PDF with structure extraction (existing)
            parsed_doc = self.parser.parse_pdf(pdf_bytes, extract_tables=True)
            logger.info(
                f"Parsed {filename}: {parsed_doc.page_count} pages, "
                f"{len(parsed_doc.sections)} sections"
            )
            
            # 2. Register with MCP server (NEW)
            self.mcp.register_document(file_id, parsed_doc)
            logger.info(f"Registered document {file_id} with MCP server")
            
            # 3. Create citation chunks (NEW)
            chunks = self.mcp.create_citation_chunks(
                doc_id=file_id,
                chunk_size=500,
                overlap=100
            )
            logger.info(f"Created {len(chunks)} citation chunks")
            
            # 4. Index with enhanced vector DB (NEW - optional, requires Qdrant)
            indexed = False
            try:
                await self.vector_db.add_document_with_citations(
                    doc_id=file_id,
                    citation_chunks=chunks,
                    metadata={
                        "filename": filename,
                        "file_id": file_id,
                        "conversation_id": conversation_id
                    }
                )
                indexed = True
                logger.info(f"Indexed {len(chunks)} chunks in vector DB")
            except Exception as e:
                logger.warning(f"Vector DB indexing failed (optional): {e}")
                # Continue without vector DB - MCP tools still work
            
            return {
                "success": True,
                "parsed_doc": parsed_doc,
                "file_id": file_id,
                "chunks_created": len(chunks),
                "indexed": indexed,
                "sections": len(parsed_doc.sections),
                "pages": parsed_doc.page_count
            }
            
        except Exception as e:
            logger.error(f"Document processing failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "file_id": file_id
            }
    
    def get_mcp_tools_for_document(
        self,
        file_id: str,
        session_id: str
    ) -> Dict[str, Any]:
        """
        Get MCP tool access for a document.
        
        Returns dict of tool functions bound to this document.
        """
        return {
            "get_page": lambda page_num: self.mcp.get_page(
                doc_id=file_id,
                page_num=page_num,
                session_id=session_id
            ),
            "search_pdf": lambda query, max_results=5: self.mcp.search_pdf(
                doc_id=file_id,
                query=query,
                session_id=session_id,
                max_results=max_results
            ),
            "get_section": lambda section_ref: self.mcp.get_section(
                doc_id=file_id,
                section_ref=section_ref,
                session_id=session_id
            ),
            "cross_check": lambda claim, source_id: self.mcp.cross_check(
                doc_id=file_id,
                claim=claim,
                source_id=source_id,
                session_id=session_id
            ),
            "get_metadata": lambda: self.mcp.get_metadata(
                doc_id=file_id,
                session_id=session_id
            )
        }
    
    async def search_with_citations(
        self,
        query: str,
        file_id: Optional[str] = None,
        top_k: int = 5,
        similarity_threshold: float = 0.7
    ) -> Dict[str, Any]:
        """
        Search with citation anchoring.
        
        Returns:
            Dict with results and formatted context
        """
        try:
            results = await self.vector_db.search_with_citations(
                query=query,
                doc_id=file_id,
                top_k=top_k,
                similarity_threshold=similarity_threshold
            )
            
            # Format context with citations
            context = self.vector_db.format_context_with_citations(
                results,
                max_context_length=3000
            )
            
            return {
                "success": True,
                "results": [
                    {
                        "content": r.content,
                        "page": r.page_num,
                        "section": r.section_number,
                        "section_title": r.section_title,
                        "citation": r.citation,
                        "score": r.score
                    }
                    for r in results
                ],
                "context": context,
                "count": len(results)
            }
        except Exception as e:
            logger.error(f"Citation search failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "results": [],
                "context": ""
            }
    
    def get_audit_trail(self, session_id: str) -> Dict[str, Any]:
        """Get audit trail for a session"""
        try:
            trail = self.mcp.get_audit_trail(session_id=session_id)
            
            # Calculate metrics
            total_calls = len(trail)
            successful_calls = sum(1 for c in trail if c["success"])
            failed_calls = total_calls - successful_calls
            
            # Tool usage breakdown
            tool_counts = {}
            for call in trail:
                tool_counts[call["tool"]] = tool_counts.get(call["tool"], 0) + 1
            
            return {
                "success": True,
                "total_calls": total_calls,
                "successful_calls": successful_calls,
                "failed_calls": failed_calls,
                "success_rate": successful_calls / total_calls if total_calls > 0 else 0,
                "tool_usage": tool_counts,
                "calls": trail
            }
        except Exception as e:
            logger.error(f"Failed to get audit trail: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def verify_findings(
        self,
        findings: list,
        file_id: str,
        session_id: str
    ) -> Dict[str, Any]:
        """
        Verify high-risk findings using cross_check tool.
        
        Args:
            findings: List of finding dicts with section, justification
            file_id: Document ID
            session_id: Session ID for audit trail
        
        Returns:
            Dict with verified findings and verification stats
        """
        verified_findings = []
        verification_stats = {
            "total": len(findings),
            "verified": 0,
            "unverified": 0,
            "high_confidence": 0,
            "low_confidence": 0
        }
        
        for finding in findings:
            # Only verify high-risk findings
            if finding.get("risk", "").lower() != "high":
                verified_findings.append(finding)
                continue
            
            # Cross-check the claim
            try:
                result = self.mcp.cross_check(
                    doc_id=file_id,
                    claim=finding.get("justification", ""),
                    source_id=finding.get("section", ""),
                    session_id=session_id
                )
                
                if result["success"]:
                    finding["verification"] = {
                        "verified": result["verified"],
                        "confidence": result["confidence"],
                        "discrepancy": result.get("discrepancy")
                    }
                    
                    if result["verified"]:
                        verification_stats["verified"] += 1
                        if result["confidence"] > 0.7:
                            verification_stats["high_confidence"] += 1
                        else:
                            verification_stats["low_confidence"] += 1
                    else:
                        verification_stats["unverified"] += 1
                        logger.warning(
                            f"Finding not verified: {finding.get('title')} - "
                            f"{result.get('discrepancy')}"
                        )
                
            except Exception as e:
                logger.error(f"Verification failed for finding: {e}")
                finding["verification"] = {
                    "verified": False,
                    "error": str(e)
                }
                verification_stats["unverified"] += 1
            
            verified_findings.append(finding)
        
        return {
            "findings": verified_findings,
            "stats": verification_stats
        }


# Singleton instance
_integration_service: Optional[MCPIntegrationService] = None


def get_integration_service() -> MCPIntegrationService:
    """Get or create the singleton integration service"""
    global _integration_service
    if _integration_service is None:
        _integration_service = MCPIntegrationService()
    return _integration_service

# Made with Bob
