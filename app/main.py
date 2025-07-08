"""FastAPI application for AI-powered ICD-10 medical coding"""

from fastapi import FastAPI, File, UploadFile, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import os
from typing import Dict, Any, List
import asyncio

from .document_reader import extract_text_from_file, validate_and_clean_text, extract_title_from_file
from .chapter_classifier import ChapterClassifier
from .vectorstore import VectorStore
from .ai_validator import AIValidator
from .title_enricher import TitleEnricher
from .models import SpreadsheetRow, CodeValidation


app = FastAPI(title="ICD-10-CM Medical Coding System", version="1.0.0")

# Mount static files and templates
app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")

# Initialize components
classifier = ChapterClassifier()
vectorstore = VectorStore()
validator = AIValidator()
title_enricher = TitleEnricher()


@app.get("/", response_class=HTMLResponse)
async def upload_form(request: Request):
    """Serve the upload form"""
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/spreadsheet", response_class=HTMLResponse)
async def spreadsheet_interface(request: Request):
    """Serve the bulk processing spreadsheet interface"""
    return templates.TemplateResponse("spreadsheet.html", {"request": request})


@app.post("/analyze")
async def analyze_document(file: UploadFile = File(...)) -> Dict[str, Any]:
    """
    Main endpoint: Analyze medical document and return ICD codes
    
    Workflow:
    1. Extract text from document
    2. AI chapter classification
    3. Vector search in relevant chapters
    4. AI validation of candidate codes
    5. Return high-confidence results
    """
    try:
        # Step 1: Extract and validate text
        file_content = await file.read()
        medical_text = extract_text_from_file(file_content, file.filename)
        
        if not medical_text:
            raise HTTPException(
                status_code=400, 
                detail=f"Unsupported file type: {file.filename.split('.')[-1]}"
            )
        
        medical_text = validate_and_clean_text(medical_text)
        
        # Step 2: AI Chapter Classification using structured outputs
        chapter_classification = classifier.classify_chapters(medical_text)
        
        # Get chapters with probability > 0.5
        target_chapters = classifier.get_high_probability_chapters(
            chapter_classification, threshold=0.5
        )
        
        # Step 3: Vector search in target chapters
        if target_chapters:
            search_results = vectorstore.search_codes_by_chapter(
                medical_text, target_chapters, top_k=50
            )
            
            # Flatten results for validation
            all_candidates = []
            for chapter_results in search_results.values():
                all_candidates.extend(chapter_results)
        else:
            # Fallback: search all chapters
            all_candidates = vectorstore.search_all_codes(medical_text, top_k=100)
        
        # Step 4: AI Validation using structured outputs
        if all_candidates:
            validation_result = validator.validate_codes(medical_text, all_candidates)
            
            # Get high confidence codes
            final_codes = validator.get_high_confidence_codes(
                validation_result, threshold=0.5
            )
        else:
            validation_result = None
            final_codes = []
        
        # Step 5: Return structured response
        return {
            "chapter_predictions": [
                {
                    "chapter_name": pred.chapter_name,
                    "probability": pred.probability,
                    "reasoning": pred.reasoning
                }
                for pred in chapter_classification.predictions
            ],
            "final_codes": [
                {
                    "icd_code": code.icd_code,
                    "description": code.description,
                    "confidence_score": code.confidence_score,
                    "reasoning": code.reasoning
                }
                for code in final_codes
            ],
            "overall_recommendation": validation_result.overall_recommendation if validation_result else "No recommendations available."
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


@app.post("/process-spreadsheet")
async def process_spreadsheet_document(file: UploadFile = File(...)) -> SpreadsheetRow:
    """
    Enhanced endpoint: Process single document for comprehensive spreadsheet output
    
    Workflow:
    1. Extract title from document (first line/H1)
    2. AI title enrichment for better vector search
    3. AI metadata generation (gender, keywords)
    4. Enhanced chapter classification (max 3 chapters, min 1)
    5. Comprehensive vector search (100 codes per chapter)
    6. AI validation for strongly related codes (~30 codes)
    7. Return structured spreadsheet row with root/hierarchy/descriptions
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
        
        # Step 2: AI Title Enrichment for vector search
        enrichment_result = title_enricher.enrich_title(title)
        search_text = f"{title} {enrichment_result.enriched_keywords}"
        
        # Step 3: AI Metadata Generation
        metadata_result = title_enricher.generate_metadata(title)
        
        # Step 4: Focused Chapter Classification (1 main + 1 optional if >50%)
        chapter_classification = classifier.classify_chapters(search_text)
        target_chapters = classifier.get_high_probability_chapters(
            chapter_classification, threshold=0.5, max_chapters=2
        )
        
        # Step 5: Comprehensive vector search (100 codes per chapter)
        all_candidates = []
        search_results = {}
        if target_chapters:
            search_results = vectorstore.search_codes_by_chapter(
                search_text, target_chapters, top_k=100
            )
        else:
            # Fallback if no chapters are identified
            all_candidates = vectorstore.search_all_codes(search_text, top_k=300)

        # Step 6: AI Validation for strongly related codes (parallel processing)
        final_codes = []
        if search_results:
            # Create a validation task for each chapter's results
            validation_tasks = [
                validator.validate_codes_async(search_text, candidates)
                for candidates in search_results.values() if candidates
            ]
            
            if validation_tasks:
                # Run all validation tasks concurrently
                validation_results = await asyncio.gather(*validation_tasks)
                
                # Collect codes with confidence >= 0.4 (40%)
                for result in validation_results:
                    high_confidence_codes = validator.get_high_confidence_codes(
                        result, threshold=0.4
                    )
                    final_codes.extend(high_confidence_codes)
        
        # Handle the fallback case using the original synchronous method
        elif all_candidates:
            validation_result = validator.validate_codes(search_text, all_candidates)
            final_codes = validator.get_high_confidence_codes(
                validation_result, threshold=0.4
            )
        
        # Step 7: Process and structure results, ensuring uniqueness and order
        # Use a dictionary to get unique codes, preserving the one with the highest score
        diagnosis_codes_map = {}
        for code in final_codes:
            if code.icd_code not in diagnosis_codes_map or \
               code.confidence_score > diagnosis_codes_map[code.icd_code].confidence_score:
                diagnosis_codes_map[code.icd_code] = code
        
        unique_final_codes = sorted(
            diagnosis_codes_map.values(), 
            key=lambda x: x.confidence_score, 
            reverse=True
        )
        
        # Step 8: Extract structured code data
        root_codes = extract_root_codes(unique_final_codes)
        hierarchy_codes = extract_hierarchy_codes(unique_final_codes)
        code_descriptions = format_code_descriptions(unique_final_codes)
        code_scores = format_code_scores(unique_final_codes)
        diagnosis_codes = hierarchy_codes  # For backward compatibility
        
        # Step 9: Generate unique name (title with underscores)
        unique_name = title.replace(" ", "_").replace(",", "").replace("(", "").replace(")", "")
        
        # Step 10: Return enhanced spreadsheet row
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
            diagnosis_codes=diagnosis_codes,
            cpt_codes="",  # Leave blank as requested
            language="English",
            source="AI Medical Coding System",
            document_type="Patient Education"
        )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Spreadsheet processing failed: {str(e)}")


def extract_root_codes(codes: List[CodeValidation]) -> str:
    """
    Extract unique root codes (first 3 characters) from ICD codes
    
    Args:
        codes: List of CodeValidation objects
        
    Returns:
        str: Comma-separated unique root codes (e.g., "Z0, R34, F84")
    """
    root_codes = set()
    for code in codes:
        if len(code.icd_code) >= 3:
            root_code = code.icd_code[:3]
            root_codes.add(root_code)
    
    return ", ".join(sorted(root_codes))


def extract_hierarchy_codes(codes: List[CodeValidation]) -> str:
    """
    Extract hierarchy codes only (no descriptions, no confidence)
    
    Args:
        codes: List of CodeValidation objects
        
    Returns:
        str: Comma-separated hierarchy codes (e.g., "Z12.344, R34.3, F84.0")
    """
    hierarchy_codes = [code.icd_code for code in codes]
    return ", ".join(hierarchy_codes)


def format_code_descriptions(codes: List[CodeValidation]) -> str:
    """
    Format code descriptions as 'CODE: Description, CODE: Description'
    
    Args:
        codes: List of CodeValidation objects
        
    Returns:
        str: Formatted descriptions (e.g., "Z12.44: blah blah, R34.3: another description")
    """
    descriptions = []
    for code in codes:
        descriptions.append(f"{code.icd_code}: {code.description}")
    
    return ", ".join(descriptions)


def format_code_scores(codes: List[CodeValidation]) -> str:
    """
    Format code confidence scores as 'CODE: XX%, CODE: XX%'
    
    Args:
        codes: List of CodeValidation objects
        
    Returns:
        str: Formatted scores (e.g., "Z123.2: 60%, R34.3: 75%")
    """
    scores = []
    for code in codes:
        percentage = int(code.confidence_score * 100)
        scores.append(f"{code.icd_code}: {percentage}%")
    
    return ", ".join(scores)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 