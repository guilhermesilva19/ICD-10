"""
🏥 AI Medical Coding System - Clean & Simple Architecture

Enhanced medical document analysis with two-step AI validation:
1. Direct vector search (no chapter limitations)
2. Initial selection (~50 relevant codes)
3. Clinical refinement (enhanced descriptions + confidence)
"""

from fastapi import FastAPI, HTTPException, File, UploadFile, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
import asyncio
from typing import Dict, Any, List

from .models import SpreadsheetRow, RefinedCodeValidation
from .document_reader import extract_title_from_file
from .title_enricher import TitleEnricher
from .ai_validator import AIValidator
from .vectorstore import VectorStore

# Initialize components
app = FastAPI(title="AI Medical Coding System", version="2.0")
templates = Jinja2Templates(directory="app/templates")
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Initialize AI components
title_enricher = TitleEnricher()
validator = AIValidator()
vectorstore = VectorStore()

@app.get("/", response_class=HTMLResponse)
async def upload_form(request: Request):
    """Single document analysis interface"""
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/spreadsheet", response_class=HTMLResponse)
async def spreadsheet_interface(request: Request):
    """Bulk spreadsheet processing interface"""
    return templates.TemplateResponse("spreadsheet.html", {"request": request})

@app.post("/analyze")
async def analyze_document(file: UploadFile = File(...)) -> Dict[str, Any]:
    """
    LEGACY ENDPOINT: Original single document analysis
    Maintains backward compatibility with existing functionality
    """
    try:
        # Extract content and title
        file_content = await file.read()
        title = extract_title_from_file(file_content, file.filename)
        
        if not title:
            raise HTTPException(
                status_code=400,
                detail=f"Could not extract title from file: {file.filename}"
            )
        
        # AI enrichment for better search
        enrichment_result = title_enricher.enrich_title(title)
        search_text = f"{title} {enrichment_result.enriched_keywords}"
        
        # Direct vector search (no chapter limitations)
        candidates = vectorstore.search_all_codes(search_text, top_k=200)
        
        # Legacy validation for backward compatibility
        validation_result = validator.validate_codes(search_text, candidates)
        high_confidence_codes = validator.get_high_confidence_codes(
            validation_result, threshold=0.4
        )
        
        # Format response
        diagnosis_codes = [code.icd_code for code in high_confidence_codes]
        
        return {
            "title": title,
            "enriched_keywords": enrichment_result.enriched_keywords,
            "diagnosis_codes": diagnosis_codes,
            "total_codes_found": len(high_confidence_codes),
            "validation_summary": validation_result.overall_recommendation
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


@app.post("/process-spreadsheet")
async def process_spreadsheet_document(file: UploadFile = File(...)) -> SpreadsheetRow:
    """
    NEW ENHANCED ENDPOINT: Clean two-step AI validation process
    
    Workflow:
    1. Extract title and AI enrichment
    2. Direct vector search (400-500 codes, no chapter limits)
    3. Step 1: Initial selection (~50 relevant codes)
    4. Step 2: Clinical refinement (enhanced descriptions + confidence)
    5. Return structured spreadsheet row
    """
    try:
        # Step 1: Extract title
        file_content = await file.read()
        title = extract_title_from_file(file_content, file.filename)
        
        if not title:
            raise HTTPException(
                status_code=400,
                detail=f"Could not extract title from file: {file.filename}"
            )
        
        # Step 2: AI Title Enrichment for better vector search
        enrichment_result = title_enricher.enrich_title(title)
        search_text = f"{title} {enrichment_result.enriched_keywords}"
        
        # Step 3: AI Metadata Generation
        metadata_result = title_enricher.generate_metadata(title)
        
        # Step 4: Direct Vector Search (No Chapter Limitations!)
        # Search all codes directly - let AI decide what's relevant
        all_candidates = vectorstore.search_all_codes(search_text, top_k=450)
        
        if not all_candidates:
            raise HTTPException(
                status_code=404,
                detail="No relevant codes found in vector search"
            )
        
        # Step 5: Two-Step AI Validation Process
        
        # Step 5a: Initial Selection (~50 codes)
        selection_result = await validator.initial_selection(search_text, all_candidates)
        
        if not selection_result.selected_codes:
            raise HTTPException(
                status_code=404,
                detail="No codes selected in initial selection step"
            )
        
        # Step 5b: Clinical Refinement (enhanced descriptions + confidence)
        refinement_result = await validator.clinical_refinement(
            search_text, 
            selection_result.selected_codes, 
            all_candidates
        )
        
        if not refinement_result.refined_codes:
            raise HTTPException(
                status_code=404,
                detail="No codes validated in clinical refinement step"
            )
        
        # Step 6: Format Results for Spreadsheet Output
        root_codes = extract_root_codes_simple(refinement_result.refined_codes)
        hierarchy_codes = extract_hierarchy_codes_simple(refinement_result.refined_codes)
        code_descriptions = format_enhanced_descriptions(refinement_result.refined_codes)
        code_scores = format_confidence_scores(refinement_result.refined_codes)
        
        # Generate unique name
        unique_name = title.replace(" ", "_").replace(",", "").replace("(", "").replace(")", "")
        
        # Step 7: Return Clean Spreadsheet Row
        return SpreadsheetRow(
            filepath=file.filename,
            title=title,
            icd_code_root=root_codes,
            icd_code_hierarchy=hierarchy_codes,
            details_description=code_descriptions,
            details_score=code_scores,
            gender=metadata_result.gender,
            unique_name=unique_name,
            keywords=metadata_result.keywords,
            diagnosis_codes=hierarchy_codes,  # For backward compatibility
            cpt_codes="",  # Leave blank as requested
            language="English",
            source="AI Medical Coding System v2.0",
            document_type="Patient Education"
        )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")


# ===== CLEAN HELPER FUNCTIONS =====

def extract_root_codes_simple(codes: List[RefinedCodeValidation]) -> str:
    """Extract unique root codes (first 3 characters)"""
    root_codes = set()
    for code in codes:
        if len(code.icd_code) >= 3:
            root_code = code.icd_code[:3]
            root_codes.add(root_code)
    return ", ".join(sorted(root_codes))

def extract_hierarchy_codes_simple(codes: List[RefinedCodeValidation]) -> str:
    """Extract full hierarchy codes"""
    hierarchy_codes = [code.icd_code for code in codes]
    return ", ".join(hierarchy_codes)

def format_enhanced_descriptions(codes: List[RefinedCodeValidation]) -> str:
    """Format enhanced descriptions as 'CODE: Enhanced Description'"""
    descriptions = []
    for code in codes:
        descriptions.append(f"{code.icd_code}: {code.enhanced_description}")
    return ", ".join(descriptions)

def format_confidence_scores(codes: List[RefinedCodeValidation]) -> str:
    """Format confidence scores as 'CODE: XX%'"""
    scores = []
    for code in codes:
        percentage = int(code.confidence_score * 100)
        scores.append(f"{code.icd_code}: {percentage}%")
    return ", ".join(scores)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 