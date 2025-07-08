"""Test script for the AI Medical Coding System - Clean Two-Step Process"""

import asyncio
from .vectorstore import VectorStore
from .ai_validator import AIValidator
from .title_enricher import TitleEnricher


async def test_new_two_step_process():
    """Test the new clean two-step AI validation process"""
    
    # Sample medical text for testing
    test_text = """
    Patient presents with chest pain and shortness of breath. 
    History of diabetes mellitus type 2. 
    Physical examination reveals elevated blood pressure and irregular heartbeat.
    EKG shows signs consistent with myocardial infarction.
    Blood glucose levels are elevated at 250 mg/dL.
    Patient reports recent weight loss and frequent urination.
    """
    
    print("🧪 Testing AI Medical Coding System - Clean Two-Step Process")
    print("=" * 70)
    
    try:
        # Test 1: Title Enrichment
        print("\n1️⃣ Testing Title Enrichment...")
        enricher = TitleEnricher()
        enrichment_result = enricher.enrich_title("Chest Pain and Diabetes")
        
        print(f"✅ Original: Chest Pain and Diabetes")
        print(f"✅ Enriched: {enrichment_result.enriched_keywords}")
        
        # Enhanced search text
        enhanced_text = f"{test_text} {enrichment_result.enriched_keywords}"
        
        # Test 2: Direct Vector Search (No Chapter Limitations)
        print("\n2️⃣ Testing Direct Vector Search...")
        vectorstore = VectorStore()
        
        all_candidates = vectorstore.search_all_codes(enhanced_text, top_k=450)
        print(f"✅ Found {len(all_candidates)} candidate codes across ALL chapters")
        
        # Show sample candidates
        print(f"\n📋 Sample candidate codes:")
        for i, candidate in enumerate(all_candidates[:5]):
            print(f"   {i+1}. {candidate['icd_code']} - {candidate['description'][:80]}...")
            print(f"      Similarity: {candidate['score']:.3f} | Chapter: {candidate['chapter']}")
        
        # Test 3: Step 1 - Initial Selection (~50 codes)
        print("\n3️⃣ Testing Step 1: Initial Selection...")
        validator = AIValidator()
        
        selection_result = await validator.initial_selection(enhanced_text, all_candidates)
        
        print(f"✅ Step 1 Complete!")
        print(f"📊 Selected {len(selection_result.selected_codes)} codes from {len(all_candidates)} candidates")
        
        print(f"\n🎯 Selected codes for clinical review:")
        for i, code in enumerate(selection_result.selected_codes[:10]):
            print(f"   {i+1}. {code}")
        if len(selection_result.selected_codes) > 10:
            print(f"   ... and {len(selection_result.selected_codes) - 10} more codes")
        
        # Test 4: Step 2 - Clinical Refinement
        print("\n4️⃣ Testing Step 2: Clinical Refinement...")
        
        refinement_result = await validator.clinical_refinement(
            enhanced_text, 
            selection_result.selected_codes, 
            all_candidates
        )
        
        print(f"✅ Step 2 Complete!")
        print(f"📊 Refined to {len(refinement_result.refined_codes)} clinically relevant codes")
        
        print(f"\n🏆 Final Clinically Relevant Codes:")
        for code in refinement_result.refined_codes:
            conf_percent = code.confidence_score * 100
            print(f"   ✓ {code.icd_code} - {conf_percent:.1f}%")
            print(f"     Original: {code.original_description[:80]}...")
            print(f"     Enhanced: {code.enhanced_description[:80]}...")
            print()
        
        print(f"💡 Clinical Summary:")
        print(f"   {refinement_result.clinical_summary}")
        
        # Test 5: Metadata Generation
        print("\n5️⃣ Testing Metadata Generation...")
        metadata_result = enricher.generate_metadata("Chest Pain and Diabetes")
        
        print(f"✅ Gender Applicability: {metadata_result.gender}")
        print(f"✅ Keywords: {metadata_result.keywords}")
        
        print("\n" + "=" * 70)
        print("🎉 NEW TWO-STEP PROCESS TEST COMPLETED SUCCESSFULLY!")
        print("✨ Clean, Simple, and Powerful Architecture Working!")
        
        # Summary
        print(f"\n📈 PROCESS SUMMARY:")
        print(f"   📤 Input: {len(all_candidates)} vector search results")
        print(f"   🔽 Step 1: Filtered to {len(selection_result.selected_codes)} relevant codes")
        print(f"   🔽 Step 2: Refined to {len(refinement_result.refined_codes)} final codes")
        print(f"   📊 Efficiency: {len(refinement_result.refined_codes)/len(all_candidates)*100:.1f}% final selection rate")
        
    except Exception as e:
        print(f"❌ Test failed: {str(e)}")
        import traceback
        traceback.print_exc()


async def test_legacy_compatibility():
    """Test that legacy /analyze endpoint still works"""
    
    print("\n🧪 Testing Legacy Compatibility...")
    
    test_text = "Patient with diabetes and heart problems"
    
    try:
        vectorstore = VectorStore()
        validator = AIValidator()
        
        # Legacy flow
        candidates = vectorstore.search_all_codes(test_text, top_k=200)
        validation_result = validator.validate_codes(test_text, candidates)
        high_confidence = validator.get_high_confidence_codes(validation_result, 0.4)
        
        print(f"✅ Legacy system working: {len(high_confidence)} codes found")
        
    except Exception as e:
        print(f"❌ Legacy test failed: {str(e)}")


if __name__ == "__main__":
    asyncio.run(test_new_two_step_process())
    asyncio.run(test_legacy_compatibility()) 