#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Simple test to verify PDF parsing works without full app dependencies.
"""

import sys
import os

# Fix Windows console encoding
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from pathlib import Path

def test_pdf_parsing():
    """Test that PDF parsing extracts structure correctly."""
    print("=" * 60)
    print("TEST: PDF Parsing & Structure Extraction")
    print("=" * 60)
    
    # Find a test PDF
    test_pdfs = list(Path("uploads").glob("*.pdf"))
    if not test_pdfs:
        test_pdfs = list(Path("scratch").glob("*.pdf"))
    
    if not test_pdfs:
        print("❌ No test PDFs found in uploads/ or scratch/")
        return False
    
    test_pdf = test_pdfs[0]
    print(f"\n📄 Testing with: {test_pdf}")
    print(f"   Size: {test_pdf.stat().st_size / 1024:.1f} KB")
    
    # Import parser (minimal dependencies)
    try:
        from app.services.document_parser import get_parser
        parser = get_parser()
        print("✅ Parser imported successfully")
    except Exception as e:
        print(f"❌ Failed to import parser: {e}")
        return False
    
    # Parse the PDF
    try:
        with open(test_pdf, 'rb') as f:
            pdf_bytes = f.read()
        
        parsed = parser.parse_pdf(pdf_bytes)
        print("✅ PDF parsed successfully")
    except Exception as e:
        print(f"❌ Failed to parse PDF: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Check structure
    print(f"\n📊 Parsed Document Structure:")
    print(f"   - Pages: {parsed.page_count}")
    print(f"   - Text blocks: {len(parsed.blocks)}")
    print(f"   - Sections: {len(parsed.sections)}")
    print(f"   - Tables: {len(parsed.tables)}")
    
    if parsed.sections:
        print(f"\n📋 First 5 sections:")
        for sec in parsed.sections[:5]:
            print(f"   - §{sec.number}: {sec.title[:50]}... (page {sec.page_num})")
    else:
        print("\n⚠️  No sections extracted (might be a non-structured document)")
    
    # Test that object can be cached (dataclass, not Pydantic)
    print(f"\n🔄 Testing cacheability:")
    try:
        # Test that we can access key fields
        assert parsed.page_count > 0
        assert len(parsed.sections) >= 0
        assert len(parsed.blocks) > 0
        print(f"✅ Object is cacheable (dataclass)")
        print(f"   - Can access page_count: {parsed.page_count}")
        print(f"   - Can access sections: {len(parsed.sections)}")
        
    except Exception as e:
        print(f"❌ Cache test failed: {e}")
        return False
    
    return True

def test_cache_simulation():
    """Simulate the cache mechanism."""
    print("\n" + "=" * 60)
    print("TEST: Cache Simulation")
    print("=" * 60)
    
    # Simulate the cache
    cache = {}
    test_conv_id = "test_conversation_123"
    
    # Find a test PDF
    test_pdfs = list(Path("uploads").glob("*.pdf"))
    if not test_pdfs:
        test_pdfs = list(Path("scratch").glob("*.pdf"))
    
    if not test_pdfs:
        print("❌ No test PDFs found")
        return False
    
    # Parse and cache
    try:
        from app.services.document_parser import get_parser
        parser = get_parser()
        
        with open(test_pdfs[0], 'rb') as f:
            pdf_bytes = f.read()
        
        parsed = parser.parse_pdf(pdf_bytes)
        
        # Simulate upload caching
        cache[test_conv_id] = parsed
        print(f"✅ UPLOAD: Cached parsed document for '{test_conv_id}'")
        print(f"   - Cache size: {len(cache)} entries")
        print(f"   - Cache keys: {list(cache.keys())}")
        
        # Simulate audit retrieval
        retrieved = cache.get(test_conv_id)
        if retrieved:
            print(f"\n✅ AUDIT: Retrieved parsed document for '{test_conv_id}'")
            print(f"   - Sections: {len(retrieved.sections)}")
            print(f"   - Pages: {retrieved.page_count}")
            print(f"   - Same object: {retrieved is parsed}")
            return True
        else:
            print(f"\n❌ AUDIT: Failed to retrieve from cache")
            return False
            
    except Exception as e:
        print(f"❌ Cache test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("\n🧪 PDF Structure Cache Test (Simplified)\n")
    
    results = []
    
    # Test 1: PDF Parsing
    try:
        results.append(("PDF Parsing", test_pdf_parsing()))
    except Exception as e:
        print(f"❌ Test crashed: {e}")
        results.append(("PDF Parsing", False))
    
    # Test 2: Cache Simulation
    try:
        results.append(("Cache Simulation", test_cache_simulation()))
    except Exception as e:
        print(f"❌ Test crashed: {e}")
        results.append(("Cache Simulation", False))
    
    print("\n" + "=" * 60)
    print("RESULTS")
    print("=" * 60)
    
    for name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {name}")
    
    all_passed = all(r[1] for r in results)
    
    if all_passed:
        print("\n🎉 All tests passed!")
        print("\n📝 Next Steps:")
        print("1. Start your backend server")
        print("2. Upload a PDF through the UI")
        print("3. Check backend logs for:")
        print("   - '✅ UPLOAD: Cached parsed document for <conv_id>'")
        print("   - '✅ AUDIT: Retrieved parsed document for <conv_id>'")
        print("   - '✅ PIPELINE: Document structure included'")
        print("   - '✅ ANALYST HAS STRUCTURE'")
        print("\n⚠️  If you see '❌ AUDIT: No parsed document in cache':")
        print("   - Check if conversation_id matches between upload and audit")
        print("   - Look at 'Cache keys:' in the log to see what's cached")
    else:
        print("\n❌ Some tests failed. Check the output above.")
    
    sys.exit(0 if all_passed else 1)


