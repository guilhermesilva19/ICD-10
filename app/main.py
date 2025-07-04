"""FastAPI application for AI-powered ICD-10 medical coding"""

from fastapi import FastAPI, File, UploadFile, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import os
from typing import Dict, Any

from .document_reader import extract_text_from_file, validate_and_clean_text, extract_title_from_file
from .chapter_classifier import ChapterClassifier
from .vectorstore import VectorStore
from .ai_validator import AIValidator
from .title_enricher import TitleEnricher
from .models import SpreadsheetRow


app = FastAPI(title="AI Medical Coding System", version="1.0.0")

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
    New endpoint: Process single document for spreadsheet output
    
    Workflow:
    1. Extract title from document (first line/H1)
    2. AI title enrichment for better vector search
    3. AI metadata generation (gender, keywords)
    4. Vector search using enriched title
    5. AI validation for multiple codes
    6. Return spreadsheet row format
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
        
        # Step 4: Enhanced Chapter Classification (more chapters for better coverage)
        chapter_classification = classifier.classify_chapters(search_text)
        
        # Get more chapters with lower threshold for broader coverage
        target_chapters = classifier.get_high_probability_chapters(
            chapter_classification, threshold=0.3
        )
        
        # Step 5: Enhanced Vector search (more results per chapter)
        if target_chapters:
            search_results = vectorstore.search_codes_by_chapter(
                search_text, target_chapters, top_k=30  # More results per chapter
            )
            
            # Flatten results for validation
            all_candidates = []
            for chapter_results in search_results.values():
                all_candidates.extend(chapter_results)
        else:
            # Fallback: search all chapters with more results
            all_candidates = vectorstore.search_all_codes(search_text, top_k=150)
        
        # Step 6: AI Validation with lower threshold for more codes
        diagnosis_codes = ""
        if all_candidates:
            validation_result = validator.validate_codes(search_text, all_candidates)
            
            # Get codes with lower confidence threshold for broader coverage
            final_codes = validator.get_high_confidence_codes(
                validation_result, threshold=0.3  # Lower threshold for more codes
            )
            
            # Format diagnosis codes as comma-separated string
            diagnosis_codes = ", ".join([code.icd_code for code in final_codes])
        
        # Step 7: Generate unique name (title with underscores)
        unique_name = title.replace(" ", "_").replace(",", "").replace("(", "").replace(")", "")
        
        # Step 8: Return spreadsheet row
        return SpreadsheetRow(
            filepath=file.filename,
            title=title,
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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 