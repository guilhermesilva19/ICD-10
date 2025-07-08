"""
🧪 AI Medical Coding System - Test Suite

Tests the two-step AI validation process:
1. Initial selection (~50 codes from vector search)
2. Clinical refinement (enhanced descriptions + confidence)
"""

import asyncio
from .title_enricher import TitleEnricher
from .ai_validator import AIValidator
from .vectorstore import VectorStore


async def test_two_step_process():
    """Test the complete two-step AI validation process"""
    
    print("🧪 Testing Two-Step AI Validation Process...")
    print("=" * 60)
    
    # Initialize components
    enricher = TitleEnricher()
    validator = AIValidator()
    vectorstore = VectorStore()
    
    # Test data
    test_text = "Patient education about chest pain and diabetes management"
    
    try:
        print(f"📄 Test Input: {test_text}")
        print()
        
        # Step 1: Title enrichment
        print("🔍 Step 1: Title Enrichment...")
        enrichment = enricher.enrich_title(test_text)
        search_text = f"{test_text} {enrichment.enriched_keywords}"
        print(f"✅ Enhanced search text: {search_text}")
        print()
        
        # Step 2: Vector search
        print("📊 Step 2: Vector Search...")
        candidates = vectorstore.search_all_codes(search_text, top_k=200)
        print(f"✅ Found {len(candidates)} candidate codes")
        print()
        
        # Step 3: Initial selection
        print("🎯 Step 3: Initial Selection...")
        selection_result = await validator.initial_selection(search_text, candidates)
        print(f"✅ Selected {len(selection_result.selected_codes)} codes for review")
        print()
        
        # Step 4: Clinical refinement
        print("🩺 Step 4: Clinical Refinement...")
        refinement_result = await validator.clinical_refinement(
            search_text, 
            selection_result.selected_codes, 
            candidates
        )
        print(f"✅ Final validated codes: {len(refinement_result.refined_codes)}")
        print()
        
        # Display results
        print("📋 Final Results:")
        print("-" * 40)
        for code in refinement_result.refined_codes[:5]:  # Show top 5
            confidence_pct = int(code.confidence_score * 100)
            print(f"• {code.icd_code} ({confidence_pct}%): {code.enhanced_description}")
        
        print()
        print(f"🏥 Clinical Summary: {refinement_result.clinical_summary}")
        
        print("\n✅ Two-step process completed successfully!")
        
    except Exception as e:
        print(f"❌ Test failed: {str(e)}")
        raise


async def test_spreadsheet_workflow():
    """Test the complete spreadsheet processing workflow"""
    
    print("\n🧪 Testing Spreadsheet Workflow...")
    print("=" * 60)
    
    # Initialize components
    enricher = TitleEnricher()
    validator = AIValidator()
    vectorstore = VectorStore()
    
    # Test data
    title = "Chest Pain and Diabetes"
    test_content = "This document provides patient education about managing chest pain symptoms in diabetic patients. It covers cardiovascular risks, blood sugar monitoring, and when to seek emergency care."
    
    try:
        print(f"📄 Test Title: {title}")
        print(f"📝 Test Content: {test_content[:100]}...")
        print()
        
        # Step 1: Title enrichment for search
        print("🔍 Step 1: Title Enrichment...")
        enrichment_result = enricher.enrich_title(title)
        search_text = f"{title} {enrichment_result.enriched_keywords}"
        print(f"✅ Search terms: {search_text}")
        print()
        
        # Step 2: Metadata generation from full content
        print("📊 Step 2: Metadata Generation...")
        metadata = enricher.generate_metadata(title, test_content)
        print(f"✅ Gender: {metadata.gender}")
        print(f"✅ Keywords: {metadata.keywords}")
        print()
        
        # Step 3: Vector search and AI validation
        print("🎯 Step 3: Vector Search & AI Validation...")
        candidates = vectorstore.search_all_codes(search_text, top_k=450)
        
        selection_result = await validator.initial_selection(search_text, candidates)
        refinement_result = await validator.clinical_refinement(
            search_text, 
            selection_result.selected_codes, 
            candidates
        )
        
        print(f"✅ Processed {len(candidates)} → {len(selection_result.selected_codes)} → {len(refinement_result.refined_codes)} codes")
        print()
        
        # Display results
        print("📋 Spreadsheet Row Data:")
        print("-" * 40)
        
        # Extract root codes
        root_codes = set()
        for code in refinement_result.refined_codes:
            if len(code.icd_code) >= 3:
                root_codes.add(code.icd_code[:3])
        
        hierarchy_codes = [code.icd_code for code in refinement_result.refined_codes]
        
        print(f"• Root Codes: {', '.join(sorted(root_codes))}")
        print(f"• Hierarchy Codes: {', '.join(hierarchy_codes)}")
        print(f"• Gender: {metadata.gender}")
        print(f"• Keywords: {metadata.keywords[:100]}...")
        
        print("\n✅ Spreadsheet workflow completed successfully!")
        
    except Exception as e:
        print(f"❌ Spreadsheet test failed: {str(e)}")
        raise


if __name__ == "__main__":
    asyncio.run(test_two_step_process())
    asyncio.run(test_spreadsheet_workflow()) 