#!/usr/bin/env python3
"""
Test script to verify PDF structure flows through the entire pipeline.
Run this to check if parsed documents are being cached and passed correctly.
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from pathlib import Path
from app.services.document_parser import get_parser
from app.routes.chat import _parsed_document_cache

def test_pdf_parsing():
    """Test that PDF parsing extracts structure correctly."""
    print("=" * 60)
    print("TEST 1: PDF Parsing")
    print("=" * 60)
    
    # Find a test PDF
    test_pdfs = list(Path("uploads").glob("*.pdf"))
    if not test_pdfs:
        test_pdfs = list(Path("scratch").glob("*.pdf"))
    
    if not test_pdfs:
        print("❌ No test PDFs found in uploads/ or scratch/")
        return False
    
    test_pdf = test_pdfs[0]
    print(f"Testing with: {test_pdf}")
    
    # Parse the PDF
    parser = get_parser()
    with open(test_pdf, 'rb') as f:
        pdf_bytes = f.read()
    
    parsed = parser.parse_pdf(pdf_bytes)
    
    # Check structure
    print(f"\n✅ Parsed successfully:")
    print(f"   - Pages: {parsed.page_count}")
    print(f"   - Blocks: {len(parsed.blocks)}")
    print(f"   - Sections: {len(parsed.sections)}")
    print(f"   - Tables: {len(parsed.tables)}")
    
    if parsed.sections:
        print(f"\n📋 First 5 sections:")
        for sec in parsed.sections[:5]:
            print(f"   - §{sec.number}: {sec.title} (p.{sec.page_num})")
    else:
        print("❌ No sections extracted!")
        return False
    
    return True

def test_cache_mechanism():
    """Test that the cache works."""
    print("\n" + "=" * 60)
    print("TEST 2: Cache Mechanism")
    print("=" * 60)
    
    # Simulate caching
    test_conv_id = "test_conv_123"
    
    # Find a test PDF
    test_pdfs = list(Path("uploads").glob("*.pdf"))
    if not test_pdfs:
        test_pdfs = list(Path("scratch").glob("*.pdf"))
    
    if not test_pdfs:
        print("❌ No test PDFs found")
        return False
    
    # Parse and cache
    parser = get_parser()
    with open(test_pdfs[0], 'rb') as f:
        pdf_bytes = f.read()
    
    parsed = parser.parse_pdf(pdf_bytes)
    _parsed_document_cache[test_conv_id] = parsed
    
    print(f"✅ Cached document for conversation: {test_conv_id}")
    print(f"   - Cache size: {len(_parsed_document_cache)}")
    print(f"   - Cache keys: {list(_parsed_document_cache.keys())}")
    
    # Retrieve from cache
    retrieved = _parsed_document_cache.get(test_conv_id)
    if retrieved:
        print(f"✅ Retrieved from cache:")
        print(f"   - Sections: {len(retrieved.sections)}")
        print(f"   - Pages: {retrieved.page_count}")
        return True
    else:
        print("❌ Failed to retrieve from cache")
        return False

def test_state_structure():
    """Test that AgentState can hold parsed_document."""
    print("\n" + "=" * 60)
    print("TEST 3: AgentState Structure")
    print("=" * 60)
    
    from app.agents.state import AgentState
    
    # Find a test PDF
    test_pdfs = list(Path("uploads").glob("*.pdf"))
    if not test_pdfs:
        test_pdfs = list(Path("scratch").glob("*.pdf"))
    
    if not test_pdfs:
        print("❌ No test PDFs found")
        return False
    
    # Parse PDF
    parser = get_parser()
    with open(test_pdfs[0], 'rb') as f:
        pdf_bytes = f.read()
    
    parsed = parser.parse_pdf(pdf_bytes)
    
    # Create state with parsed_document
    state: AgentState = {
        "query": "Test query",
        "original_query": "Test",
        "internal_docs": [],
        "web_results": [],
        "merged_context": "Test context",
        "sources": [],
        "research_report": "",
        "risk_analysis": {},
        "audit_report": "",
        "final_report_md": "",
        "next_step": "",
        "errors": [],
        "iteration_count": 0,
        "reflection_log": [],
        "parsed_document": parsed,
    }
    
    # Verify it's in the state
    retrieved_doc = state.get("parsed_document")
    if retrieved_doc:
        print(f"✅ parsed_document in AgentState:")
        print(f"   - Sections: {len(retrieved_doc.sections)}")
        print(f"   - Pages: {retrieved_doc.page_count}")
        return True
    else:
        print("❌ parsed_document not in AgentState")
        return False

if __name__ == "__main__":
    print("\n🧪 PDF Structure Flow Test Suite\n")
    
    results = []
    results.append(("PDF Parsing", test_pdf_parsing()))
    results.append(("Cache Mechanism", test_cache_mechanism()))
    results.append(("AgentState Structure", test_state_structure()))
    
    print("\n" + "=" * 60)
    print("RESULTS")
    print("=" * 60)
    
    for name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {name}")
    
    all_passed = all(r[1] for r in results)
    
    if all_passed:
        print("\n🎉 All tests passed!")
        print("\nNext steps:")
        print("1. Upload a PDF through the UI")
        print("2. Check backend logs for:")
        print("   - '✅ UPLOAD: Cached parsed document'")
        print("   - '✅ AUDIT: Retrieved parsed document'")
        print("   - '✅ PIPELINE: Document structure included'")
        print("   - '✅ ANALYST HAS STRUCTURE'")
    else:
        print("\n❌ Some tests failed. Check the output above.")
    
    sys.exit(0 if all_passed else 1)


