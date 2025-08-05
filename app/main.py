"""Medical coding system with deterministic processing and official ICD validation."""

import logging
import os
from fastapi import FastAPI, HTTPException, File, UploadFile, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, Any, List, Optional
from bs4 import BeautifulSoup
import json

from .models import SpreadsheetRow, RefinedCodeValidation
from .document_reader import extract_title_from_file, extract_text_from_file, extract_first_page_content
from .medical_engine import MedicalCodingEngine
from .metadata_generator import MetadataGenerator
from .metadata_extractor import extract_embedded_metadata
from .cpt_generator import CPTGenerator  # Import the new CPT generator

# Configure professional logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
    ]
)
logger = logging.getLogger(__name__)

# Initialize FastAPI
app = FastAPI(title="Medical Coding System", version="4.0.0")  # Bumped version to 4.0.0 for major update

# Add CORS middleware for AWS compatibility
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure this properly for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    max_age=3600,
)

# Get absolute paths for reliable file serving
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATES_DIR = os.path.join(BASE_DIR, "app", "templates")
STATIC_DIR = os.path.join(BASE_DIR, "app", "static")

# Debug logging for deployment troubleshooting
logger.info(f"Base directory: {BASE_DIR}")
logger.info(f"Templates directory: {TEMPLATES_DIR}")
logger.info(f"Static directory: {STATIC_DIR}")

# Initialize templates and static files
try:
    templates = Jinja2Templates(directory=TEMPLATES_DIR)
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
except Exception as e:
    logger.error(f"Template/static file initialization error: {str(e)}")
    raise

# Initialize engines
medical_engine = MedicalCodingEngine()
cpt_generator = CPTGenerator()  # Initialize the CPT generator

# ===== ROUTES =====

@app.get("/", response_class=HTMLResponse)
async def upload_form(request: Request):
    """Single document analysis interface."""
    return templates.TemplateResponse("index.html", {"request": request, "active_tab": "single"})

@app.get("/spreadsheet", response_class=HTMLResponse)
async def spreadsheet_interface(request: Request):
    """Bulk spreadsheet processing interface."""
    return templates.TemplateResponse("spreadsheet.html", {"request": request, "active_tab": "spreadsheet"})

@app.get("/cpt", response_class=HTMLResponse)
async def cpt_interface(request: Request):
    """CPT code generator interface."""
    return templates.TemplateResponse("cpt.html", {"request": request, "active_tab": "cpt"})

@app.post("/api/analyze")
async def analyze_document(file: UploadFile = File(..., max_size=1024 * 1024 * 1024)):
    """Analyze single document - preserving exact response format."""
    try:
        # Read file content
        file_content = await file.read()
        
        # Extract text from the document
        text_content = extract_text_from_file(file_content, file.filename)
        if not text_content:
            raise HTTPException(status_code=400, detail="Unsupported file format or empty file")
        
        # Generate CPT codes (temporarily disable if causing issues)
        cpt_codes = []
        try:
            cpt_generator = CPTGenerator()
            cpt_codes = await cpt_generator.generate_cpt_codes(text_content)
        except Exception as e:
            logger.error(f"Error generating CPT codes: {str(e)}", exc_info=True)
            # Continue with empty CPT codes if generation fails
            
        # Process with existing medical engine for ICD-10 codes
        title = extract_title_from_file(file_content, file.filename) or "Untitled Document"
        first_page = extract_first_page_content(file_content, file.filename)
        
        # Get ICD-10 codes
        icd_response = await medical_engine.extract_codes_for_spreadsheet(
            title=title,
            content=text_content
        )
        
        # Combine results
        result = {
            "status": "success",
            "document_title": title,
            "cpt_codes": cpt_codes,
            "icd_codes": {
                "root_codes": extract_root_codes_simple(icd_response.refined_codes),
                "hierarchy_codes": extract_hierarchy_codes_simple(icd_response.refined_codes),
                "enhanced_descriptions": format_enhanced_descriptions(icd_response.refined_codes),
                "confidence_scores": format_confidence_scores(icd_response.refined_codes),
                "structured_codes": format_structured_codes(icd_response.refined_codes)
            },
            "metadata": {
                "document_type": file.content_type,
                "file_name": file.filename,
                "file_size": len(file_content)
            }
        }
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing document: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error processing document: {str(e)}")

@app.post("/api/analyze-cpt")
async def analyze_cpt_only(file: UploadFile = File(..., max_size=1024 * 1024 * 1024)):
    """Analyze document and return only CPT codes."""
    try:
        # Read file content
        file_content = await file.read()
        
        # Extract text from the document
        text_content = extract_text_from_file(file_content, file.filename)
        if not text_content:
            raise HTTPException(status_code=400, detail="Unsupported file format or empty file")
        
        # Generate CPT codes (synchronously)
        cpt_codes = []
        try:
            cpt_generator = CPTGenerator()
            cpt_codes = cpt_generator.generate_cpt_codes(text_content)
        except Exception as e:
            logger.error(f"Error generating CPT codes: {str(e)}", exc_info=True)
            # Continue with empty CPT codes if generation fails
            
        return {
            "status": "success",
            "cpt_codes": cpt_codes,
            "metadata": {
                "document_type": file.content_type,
                "file_name": file.filename,
                "file_size": len(file_content)
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing document for CPT codes: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error processing document: {str(e)}")

# ===== HELPER FUNCTIONS =====

def extract_root_codes_simple(codes: List[RefinedCodeValidation]) -> List[str]:
    """Extract unique root codes (first 3 characters)"""
    root_codes = set()
    for code in codes:
        if hasattr(code, 'icd_code') and code.icd_code and len(code.icd_code) >= 3:
            # Extract root code (first 3 characters before any dot)
            root_code = code.icd_code.split('.')[0]
            if len(root_code) >= 3:
                root_codes.add(root_code[:3])
    return sorted(root_codes)

def extract_hierarchy_codes_simple(codes: List[RefinedCodeValidation]) -> List[str]:
    """Extract full hierarchy codes"""
    return [code.icd_code for code in codes if hasattr(code, 'icd_code') and code.icd_code]

def format_enhanced_descriptions(codes: List[RefinedCodeValidation]) -> List[str]:
    """Format enhanced descriptions as 'CODE: Enhanced Description'"""
    return [
        f"{code.icd_code}: {code.enhanced_description}"
        for code in codes
        if hasattr(code, 'icd_code') and code.icd_code and hasattr(code, 'enhanced_description') and code.enhanced_description
    ]

def format_confidence_scores(codes: List[RefinedCodeValidation]) -> Dict[str, float]:
    """Format confidence scores as 'CODE: XX%'"""
    return {
        code.icd_code: round(code.confidence_score * 100)
        for code in codes
        if hasattr(code, 'icd_code') and code.icd_code and hasattr(code, 'confidence_score') and code.confidence_score is not None
    }

def format_structured_codes(codes: List[RefinedCodeValidation]) -> List[Dict[str, Any]]:
    """Format codes as structured data for enhanced export capabilities"""
    return [
        {
            'code': code.icd_code,
            'description': code.original_description,
            'enhanced_description': code.enhanced_description if hasattr(code, 'enhanced_description') else '',
            'confidence': round(code.confidence_score * 100, 2) if hasattr(code, 'confidence_score') else 0.0
        }
        for code in codes
        if hasattr(code, 'icd_code') and code.icd_code
    ]

if __name__ == "__main__":
    import uvicorn
    logger.info("Starting Medical Coding System server...")
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)