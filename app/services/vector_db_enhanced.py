"""
Enhanced Vector Database Service with Citation Anchoring

This module implements RAG with:
- Citation-anchored chunks (page, section, bbox metadata)
- Chunk-level IDs for precise reference
- Similarity threshold filtering
- Cross-encoder reranking support
- Anti-hallucination safeguards
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from qdrant_client import QdrantClient, AsyncQdrantClient
from qdrant_client.http import models
from fastembed import TextEmbedding

from app.core.config import settings
from app.services.mcp_server import CitationChunk, get_mcp_server

logger = logging.getLogger(__name__)


@dataclass
class CitedResult:
    """A search result with full citation metadata"""
    content: str
    page_num: int
    section_number: str
    section_title: str
    chunk_id: str
    score: float
    citation: str  # Formatted citation string
    bbox: Optional[Tuple[float, float, float, float]] = None


class EnhancedVectorDBService:
    """
    Enhanced vector DB with citation anchoring for anti-hallucination RAG.
    
    Key features:
    - Every chunk has page, section, and bbox metadata
    - Chunk-level IDs enable precise citation
    - Similarity threshold prevents low-confidence injection
    - Results include formatted citations
    """
    
    def __init__(self):
        self.client = QdrantClient(
            url=settings.QDRANT_URL if hasattr(settings, 'QDRANT_URL') 
            else getattr(settings, 'QRANT_URL', 'http://localhost:6333')
        )
        self.async_client = AsyncQdrantClient(
            url=settings.QDRANT_URL if hasattr(settings, 'QDRANT_URL')
            else getattr(settings, 'QRANT_URL', 'http://localhost:6333')
        )
        self.collection_name = settings.QDRANT_COLLECTION
        self._model: Optional[TextEmbedding] = None
        self.mcp_server = get_mcp_server()
        
        # Anti-hallucination thresholds
        self.similarity_threshold = 0.7  # Don't inject low-confidence context
        self.min_results = 3  # Minimum results to return
        self.max_results = 5  # Maximum results to return
    
    @property
    def model(self) -> TextEmbedding:
        if self._model is None:
            logger.info(f"Loading embedding model: {settings.EMBEDDING_MODEL}")
            self._model = TextEmbedding(model_name=settings.EMBEDDING_MODEL)
        return self._model
    
    async def init_collection(self):
        """Initialize collection with citation metadata schema"""
        try:
            collections = self.client.get_collections().collections
            exists = any(c.name == self.collection_name for c in collections)
            
            if not exists:
                logger.info(f"Creating collection with citation schema: {self.collection_name}")
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=models.VectorParams(
                        size=1024,  # BGE-M3 dimension
                        distance=models.Distance.COSINE
                    ),
                )
            else:
                logger.info(f"Collection {self.collection_name} already exists")
        except Exception as e:
            logger.error(f"Failed to initialize collection: {e}")
    
    async def add_document_with_citations(
        self,
        doc_id: str,
        citation_chunks: List[CitationChunk],
        metadata: Dict[str, Any]
    ):
        """
        Add document chunks with full citation metadata.
        
        Each chunk includes:
        - content: The actual text
        - page_num: Page number for citation
        - section_number: Section reference
        - section_title: Section title
        - chunk_id: Unique identifier
        - bbox: Bounding box coordinates (optional)
        """
        if not citation_chunks:
            logger.warning(f"No chunks to add for document {doc_id}")
            return
        
        logger.info(f"Embedding {len(citation_chunks)} citation chunks for {doc_id}")
        
        # Extract content for embedding
        contents = [chunk.content for chunk in citation_chunks]
        embeddings = list(self.model.embed(contents))
        
        points = []
        for chunk, vector in zip(citation_chunks, embeddings):
            # Build citation string
            citation = f"[SOURCE: page {chunk.page_num}, section {chunk.section_number}]"
            
            points.append(models.PointStruct(
                id=chunk.chunk_id,
                vector=vector.tolist(),
                payload={
                    **metadata,
                    "content": chunk.content,
                    "page_num": chunk.page_num,
                    "section_number": chunk.section_number,
                    "section_title": chunk.section_title,
                    "chunk_id": chunk.chunk_id,
                    "citation": citation,
                    "bbox": chunk.bbox,
                    "block_index": chunk.block_index,
                    "doc_id": doc_id
                }
            ))
        
        self.client.upsert(
            collection_name=self.collection_name,
            points=points
        )
        logger.info(f"Successfully indexed {len(points)} citation-anchored chunks")
    
    async def search_with_citations(
        self,
        query: str,
        doc_id: Optional[str] = None,
        top_k: int = 5,
        similarity_threshold: Optional[float] = None
    ) -> List[CitedResult]:
        """
        Search with citation anchoring and threshold filtering.
        
        Args:
            query: Search query
            doc_id: Optional document ID to filter by
            top_k: Number of results to return (default: 5)
            similarity_threshold: Minimum similarity score (default: 0.7)
        
        Returns:
            List of CitedResult with full citation metadata
        """
        threshold = similarity_threshold or self.similarity_threshold
        
        # Generate query embedding
        query_vector = list(self.model.embed([query]))[0]
        
        # Build filter if doc_id provided
        query_filter = None
        if doc_id:
            query_filter = models.Filter(
                must=[
                    models.FieldCondition(
                        key="doc_id",
                        match=models.MatchValue(value=doc_id)
                    )
                ]
            )
        
        # Search
        search_result = self.client.search(
            collection_name=self.collection_name,
            query_vector=query_vector.tolist(),
            query_filter=query_filter,
            limit=top_k * 2,  # Get more results for threshold filtering
            score_threshold=threshold  # Qdrant native threshold
        )
        
        # Convert to CitedResult
        results = []
        for hit in search_result:
            if hit.score < threshold:
                continue  # Additional threshold check
            
            payload = hit.payload
            results.append(CitedResult(
                content=payload.get("content", ""),
                page_num=payload.get("page_num", 0),
                section_number=payload.get("section_number", ""),
                section_title=payload.get("section_title", ""),
                chunk_id=payload.get("chunk_id", ""),
                score=hit.score,
                citation=payload.get("citation", ""),
                bbox=payload.get("bbox")
            ))
        
        # Limit to top_k after filtering
        results = results[:top_k]
        
        if len(results) < self.min_results:
            logger.warning(
                f"Only {len(results)} results above threshold {threshold} "
                f"(minimum: {self.min_results})"
            )
        
        return results
    
    def format_context_with_citations(
        self,
        results: List[CitedResult],
        max_context_length: int = 3000
    ) -> str:
        """
        Format search results into context string with citations.
        
        Each chunk is tagged with [SOURCE: page X, section Y] for
        anti-hallucination prompting.
        """
        if not results:
            return ""
        
        context_parts = []
        current_length = 0
        
        for result in results:
            # Format: [SOURCE: ...] content
            chunk_text = f"{result.citation}\n{result.content}\n"
            chunk_length = len(chunk_text)
            
            if current_length + chunk_length > max_context_length:
                break
            
            context_parts.append(chunk_text)
            current_length += chunk_length
        
        return "\n".join(context_parts)
    
    def get_chunk_by_id(self, chunk_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a specific chunk by ID for verification.
        
        Used by the cross_check tool to validate LLM claims.
        """
        try:
            result = self.client.retrieve(
                collection_name=self.collection_name,
                ids=[chunk_id]
            )
            
            if result:
                return result[0].payload
            return None
            
        except Exception as e:
            logger.error(f"Failed to retrieve chunk {chunk_id}: {e}")
            return None
    
    async def rerank_results(
        self,
        query: str,
        results: List[CitedResult],
        top_k: int = 3
    ) -> List[CitedResult]:
        """
        Rerank results using cross-encoder (placeholder for future implementation).
        
        Cross-encoders provide better relevance than bi-encoders alone,
        reducing hallucination from irrelevant context.
        
        TODO: Integrate actual cross-encoder model (e.g., ms-marco-MiniLM)
        """
        # For now, just return top_k results
        # In production, use a cross-encoder model here
        logger.info(f"Reranking {len(results)} results (placeholder)")
        return results[:top_k]
    
    def get_citation_stats(self, doc_id: str) -> Dict[str, Any]:
        """Get statistics about citation coverage for a document"""
        try:
            # Count chunks per section
            scroll_result = self.client.scroll(
                collection_name=self.collection_name,
                scroll_filter=models.Filter(
                    must=[
                        models.FieldCondition(
                            key="doc_id",
                            match=models.MatchValue(value=doc_id)
                        )
                    ]
                ),
                limit=1000
            )
            
            chunks = scroll_result[0]
            
            # Analyze coverage
            sections = set()
            pages = set()
            
            for chunk in chunks:
                payload = chunk.payload
                sections.add(payload.get("section_number", ""))
                pages.add(payload.get("page_num", 0))
            
            return {
                "total_chunks": len(chunks),
                "unique_sections": len(sections),
                "unique_pages": len(pages),
                "avg_chunks_per_section": len(chunks) / len(sections) if sections else 0
            }
            
        except Exception as e:
            logger.error(f"Failed to get citation stats: {e}")
            return {}


# Singleton instance
_enhanced_vector_db: Optional[EnhancedVectorDBService] = None


def get_enhanced_vector_db() -> EnhancedVectorDBService:
    """Get or create the singleton enhanced vector DB instance"""
    global _enhanced_vector_db
    if _enhanced_vector_db is None:
        _enhanced_vector_db = EnhancedVectorDBService()
    return _enhanced_vector_db

# Made with Bob
