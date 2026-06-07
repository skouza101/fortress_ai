"""
Test script for chunked processing feature.

Demonstrates:
1. Quick scan (< 1 second)
2. Partial findings streaming (2-3s to first result)
3. Progressive updates as chunks complete
"""

import asyncio
import sys
import time
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.chunked_analysis import get_chunked_service
from app.services.document_parser import parse_document
from app.agents.state import AgentState


async def test_chunked_processing():
    """Test chunked processing with a real PDF."""
    
    # Find a test PDF
    uploads_dir = Path("uploads")
    pdf_files = list(uploads_dir.glob("*.pdf"))
    
    if not pdf_files:
        print("❌ No PDF files found in uploads/ directory")
        return
    
    test_pdf = pdf_files[0]
    print(f"📄 Testing with: {test_pdf.name}\n")
    
    # Parse document
    print("⏳ Parsing document structure...")
    start_parse = time.time()
    parsed_doc = await parse_document(str(test_pdf))
    parse_time = time.time() - start_parse
    print(f"✅ Parsed in {parse_time:.2f}s")
    print(f"   - {parsed_doc.total_pages} pages")
    print(f"   - {len(parsed_doc.section_map)} sections\n")
    
    # Create state
    state: AgentState = {
        "query": "Analyze contract risks",
        "original_query": "Full contract audit",
        "parsed_document": parsed_doc,
        "merged_context": "",
        "internal_docs": [],
        "web_results": [],
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
    
    # Get chunked service
    chunked_service = get_chunked_service(chunk_size=3)
    
    # 1. Quick Scan
    print("🔍 PHASE 1: Quick Scan")
    print("-" * 50)
    start_scan = time.time()
    quick_scan = await chunked_service.quick_scan(state)
    scan_time = time.time() - start_scan
    
    print(f"✅ Scan complete in {scan_time:.3f}s")
    print(f"   - Total sections: {quick_scan['total_sections']}")
    print(f"   - Flagged sections: {len(quick_scan['flagged_sections'])}")
    
    if quick_scan['flagged_sections']:
        print("\n   High-risk sections detected:")
        for section in quick_scan['flagged_sections'][:5]:
            print(f"     • {section['title']} (Page {section['page']})")
    print()
    
    # 2. Chunked Analysis
    print("🔬 PHASE 2: Chunked Analysis")
    print("-" * 50)
    
    start_chunked = time.time()
    chunk_count = 0
    total_findings = 0
    first_result_time = None
    
    async for result in chunked_service.analyze_in_chunks(state):
        if result["type"] == "partial_findings":
            chunk_count += 1
            findings_count = len(result["findings"])
            total_findings = result["cumulative_count"]
            
            if first_result_time is None:
                first_result_time = time.time() - start_chunked
                print(f"⚡ First results in {first_result_time:.2f}s!\n")
            
            print(f"📦 Chunk {result['chunk_num']}/{result['total_chunks']}")
            print(f"   - Found {findings_count} findings in this chunk")
            print(f"   - Total findings so far: {total_findings}")
            print(f"   - Progress: {result['sections_processed']}/{result['total_sections']} sections")
            
            # Show sample findings
            if result["findings"]:
                print(f"\n   Sample finding:")
                finding = result["findings"][0]
                print(f"     • {finding.get('title', 'N/A')}")
                print(f"       Section: {finding.get('section', 'N/A')} (Page {finding.get('page', 'N/A')})")
                print(f"       Priority: {finding.get('priority', 'N/A')}")
            print()
        
        elif result["type"] == "complete_findings":
            total_time = time.time() - start_chunked
            print("=" * 50)
            print(f"✅ Analysis Complete!")
            print(f"   - Total time: {total_time:.2f}s")
            print(f"   - Time to first result: {first_result_time:.2f}s")
            print(f"   - Chunks processed: {result['chunks_processed']}")
            print(f"   - Total findings: {result['total_findings']}")
            print(f"   - Average time per chunk: {total_time / result['chunks_processed']:.2f}s")
            
            # Performance metrics
            if first_result_time:
                speedup = (total_time / first_result_time) if first_result_time > 0 else 0
                print(f"\n📊 Performance:")
                print(f"   - User saw results {speedup:.1f}x faster than waiting for full analysis")
                print(f"   - Progressive updates every ~{total_time / chunk_count:.1f}s")


async def test_quick_scan_only():
    """Test just the quick scan feature."""
    
    uploads_dir = Path("uploads")
    pdf_files = list(uploads_dir.glob("*.pdf"))
    
    if not pdf_files:
        print("❌ No PDF files found")
        return
    
    test_pdf = pdf_files[0]
    print(f"📄 Quick scan test: {test_pdf.name}\n")
    
    # Parse
    parsed_doc = await parse_document(str(test_pdf))
    
    state: AgentState = {
        "query": "Quick scan",
        "original_query": "Quick scan",
        "parsed_document": parsed_doc,
        "merged_context": "",
        "internal_docs": [],
        "web_results": [],
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
    
    # Quick scan
    chunked_service = get_chunked_service()
    
    print("⚡ Running quick scan...")
    start = time.time()
    result = await chunked_service.quick_scan(state)
    elapsed = time.time() - start
    
    print(f"✅ Complete in {elapsed:.3f}s")
    print(f"\n📊 Results:")
    print(f"   - Pages: {result['total_pages']}")
    print(f"   - Sections: {result['total_sections']}")
    print(f"   - Flagged: {len(result['flagged_sections'])}")
    
    if result['flagged_sections']:
        print(f"\n🚩 High-risk sections:")
        for section in result['flagged_sections']:
            print(f"   • {section['title']} (Page {section['page']})")
            print(f"     Reason: {section['reason']}")


if __name__ == "__main__":
    print("=" * 50)
    print("CHUNKED PROCESSING TEST")
    print("=" * 50)
    print()
    
    # Run tests
    asyncio.run(test_quick_scan_only())
    print("\n" + "=" * 50 + "\n")
    asyncio.run(test_chunked_processing())

# Made with Bob
