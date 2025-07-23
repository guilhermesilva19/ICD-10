"""Medical coding system with deterministic processing and official ICD validation."""

import logging
import os
from fastapi import FastAPI, HTTPException, File, UploadFile, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, Any, List
from bs4 import BeautifulSoup

from .models import SpreadsheetRow, RefinedCodeValidation
from .document_reader import extract_title_from_file, extract_text_from_file, extract_first_page_content
from .medical_engine import MedicalCodingEngine
from .metadata_generator import MetadataGenerator
from .metadata_extractor import extract_embedded_metadata

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
app = FastAPI(title="Medical Coding System", version="3.0.0")

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
logger.info(f"Static directory exists: {os.path.exists(STATIC_DIR)}")
if os.path.exists(STATIC_DIR):
    logger.info(f"Static files: {os.listdir(STATIC_DIR)}")

templates = Jinja2Templates(directory=TEMPLATES_DIR)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# Initialize components with logging
logger.info("Initializing medical coding system components...")
try:
    coding_engine = MedicalCodingEngine()
    metadata_generator = MetadataGenerator()
    logger.info("All system components initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize components: {e}")
    raise

@app.get("/", response_class=HTMLResponse)
async def upload_form(request: Request):
    """Single document analysis interface."""
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/spreadsheet", response_class=HTMLResponse)
async def spreadsheet_interface(request: Request):
    """Bulk spreadsheet processing interface."""
    return templates.TemplateResponse("spreadsheet.html", {"request": request})

@app.post("/analyze")
async def analyze_document(file: UploadFile = File(..., max_size=1024 * 1024 * 1024)) -> Dict[str, Any]:  # 1GB limit
    """Analyze single document - preserving exact response format."""
    try:
        logger.info(f"Processing single document analysis for: {file.filename}")
        
        # Validate file
        if not file.filename:
            raise HTTPException(status_code=400, detail="No filename provided")
        
        # Extract document data
        clean_filename = file.filename.split('/')[-1] if '/' in file.filename else file.filename
        file_content = await file.read()
        
        # Validate file content
        if not file_content or len(file_content) == 0:
            raise HTTPException(status_code=400, detail="Empty file provided")
        title = extract_title_from_file(file_content, clean_filename)
        
        if not title:
            logger.warning(f"Failed to extract title from file: {clean_filename}")
            raise HTTPException(status_code=400, detail=f"Could not extract title from file: {clean_filename}")
        
        # Enhanced vector search - title + first page content for better semantic matching
        first_page_content = extract_first_page_content(file_content, clean_filename)
        if first_page_content:
            search_text = f"{title} {first_page_content}"
            logger.info(f"Using enhanced search with first page content: {len(search_text)} chars")
        else:
            search_text = f"{title} {title}"
            logger.info(f"Fallback to title duplication - first page extraction failed")
        
        # For HTML: extract embedded metadata, for others: use AI
        extracted_gender, extracted_unique = extract_embedded_metadata(file_content, clean_filename)
        
        # AI metadata generation for keywords (and gender/unique for non-HTML)
        full_content = extract_text_from_file(file_content, clean_filename)
        metadata_result = metadata_generator.generate_metadata(title, full_content)
        
        # Use extracted metadata for HTML, AI metadata for others
        gender = extracted_gender if extracted_gender else metadata_result.gender
        unique_name = extracted_unique if extracted_unique else title.replace(" ", "_").replace(",", "_").replace("(", "").replace(")", "")
        
        # AI metadata generation - Enhanced terminology (synonyms, acronyms, terms)
        terminology_result = metadata_generator.generate_enhanced_terminology(
            title, metadata_result.keywords, full_content
        )
        
        # Combine all terminology into comprehensive keywords
        keyword_parts = []
        seen_keywords = set()  # Track keywords to prevent duplicates
        
        # Helper function to add unique keywords
        def add_unique_keywords(keyword_string):
            if not keyword_string:
                return []
            keywords = [k.strip().lower() for k in keyword_string.split(',') if k.strip()]
            unique_keywords = []
            for keyword in keywords:
                if keyword not in seen_keywords:
                    seen_keywords.add(keyword)
                    unique_keywords.append(keyword)
            return unique_keywords
        
        # Add keywords from each category, removing duplicates
        if metadata_result.keywords:
            unique_base = add_unique_keywords(metadata_result.keywords)
            if unique_base:
                keyword_parts.append(', '.join(unique_base))
                
        if terminology_result.synonyms:
            unique_synonyms = add_unique_keywords(terminology_result.synonyms)
            if unique_synonyms:
                keyword_parts.append(', '.join(unique_synonyms))
                
        if terminology_result.acronyms:
            unique_acronyms = add_unique_keywords(terminology_result.acronyms)
            if unique_acronyms:
                keyword_parts.append(', '.join(unique_acronyms))
                
        if terminology_result.misspellings:
            unique_misspellings = add_unique_keywords(terminology_result.misspellings)
            if unique_misspellings:
                keyword_parts.append(', '.join(unique_misspellings))
                
        if terminology_result.layman_terms:
            unique_layman = add_unique_keywords(terminology_result.layman_terms)
            if unique_layman:
                keyword_parts.append(', '.join(unique_layman))
                
        if terminology_result.clinical_terms:
            unique_clinical = add_unique_keywords(terminology_result.clinical_terms)
            if unique_clinical:
                keyword_parts.append(', '.join(unique_clinical))
        
        # Create comprehensive keyword string
        final_keywords = ", ".join(keyword_parts) if keyword_parts else metadata_result.keywords
        
        logger.info(f"Metadata generation complete - Base: {len(metadata_result.keywords)} chars, Final: {len(final_keywords)} chars, Unique terms: {len(seen_keywords)}")
        
        # Extract codes using new engine
        coding_result = await coding_engine.extract_codes_for_spreadsheet(title, search_text)
        
        if not coding_result.refined_codes:
            logger.warning("No codes validated after analysis")
            raise HTTPException(status_code=404, detail="No codes validated after clinical review")
        
        # Format response - exact same format as before
        diagnosis_codes = [code.icd_code for code in coding_result.refined_codes]
        
        code_details = []
        for code in coding_result.refined_codes:
            confidence_pct = int(code.confidence_score * 100)
            code_details.append({
                "code": code.icd_code,
                "enhanced_description": code.enhanced_description,
                "confidence": f"{confidence_pct}%"
            })
        
        logger.info(f"Analysis complete - {len(diagnosis_codes)} codes generated")
        
        return {
            "title": title,
            "enriched_keywords": final_keywords,
            "diagnosis_codes": diagnosis_codes,
            "total_codes_found": len(coding_result.refined_codes),
            "code_details": code_details,
            "clinical_summary": coding_result.clinical_summary
        }
        
    except ValueError as e:
        logger.error(f"Document processing validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected analysis failure: {e}")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


@app.post("/process-spreadsheet")
async def process_spreadsheet_document(file: UploadFile = File(..., max_size=1024 * 1024 * 1024)) -> SpreadsheetRow:  # 1GB limit
    """Process document for spreadsheet - preserving exact response format."""
    try:
        logger.info(f"Processing spreadsheet document: {file.filename}")
        
        # Validate file
        if not file.filename:
            raise HTTPException(status_code=400, detail="No filename provided")
        
        # Extract document data
        clean_filename = file.filename.split('/')[-1] if '/' in file.filename else file.filename
        file_content = await file.read()
        
        # Validate file content
        if not file_content or len(file_content) == 0:
            raise HTTPException(status_code=400, detail="Empty file provided")
        title = extract_title_from_file(file_content, clean_filename)
        
        if not title:
            logger.warning(f"Failed to extract title from spreadsheet file: {clean_filename}")
            raise HTTPException(status_code=400, detail=f"Could not extract title from file: {clean_filename}")
        
        # Extract full content
        full_content = extract_text_from_file(file_content, clean_filename)
        
        # Enhanced vector search - title + first page content for better semantic matching
        first_page_content = extract_first_page_content(file_content, clean_filename)
        if first_page_content:
            #give more weight for the title
            search_text = f"{title} {title} {title} {title} {first_page_content}"
            logger.info(f"Using enhanced search with first page content: {len(search_text)} chars")
        else:
            search_text = f"{title} {title} {title} {title}"
            logger.info(f"Fallback to title duplication - first page extraction failed")
        
        # For HTML: extract embedded metadata, for others: use AI
        extracted_gender, extracted_unique = extract_embedded_metadata(file_content, clean_filename)
        
        # AI metadata generation for keywords (and gender/unique for non-HTML)
        metadata_result = metadata_generator.generate_metadata(title, full_content)
        
        # Use extracted metadata for HTML, AI metadata for others
        gender = extracted_gender if extracted_gender else metadata_result.gender
        unique_name = extracted_unique if extracted_unique else title.replace(" ", "_").replace(",", "_").replace("(", "").replace(")", "")
        
        # AI metadata generation - Enhanced terminology (synonyms, acronyms, terms)
        terminology_result = metadata_generator.generate_enhanced_terminology(
            title, metadata_result.keywords, full_content
        )
        
        # Combine all terminology into comprehensive keywords
        keyword_parts = []
        seen_keywords = set()  # Track keywords to prevent duplicates
        
        # Helper function to add unique keywords
        def add_unique_keywords(keyword_string):
            if not keyword_string:
                return []
            keywords = [k.strip().lower() for k in keyword_string.split(',') if k.strip()]
            unique_keywords = []
            for keyword in keywords:
                if keyword not in seen_keywords:
                    seen_keywords.add(keyword)
                    unique_keywords.append(keyword)
            return unique_keywords
        
        # Add keywords from each category, removing duplicates
        if metadata_result.keywords:
            unique_base = add_unique_keywords(metadata_result.keywords)
            if unique_base:
                keyword_parts.append(', '.join(unique_base))
                
        if terminology_result.synonyms:
            unique_synonyms = add_unique_keywords(terminology_result.synonyms)
            if unique_synonyms:
                keyword_parts.append(', '.join(unique_synonyms))
                
        if terminology_result.acronyms:
            unique_acronyms = add_unique_keywords(terminology_result.acronyms)
            if unique_acronyms:
                keyword_parts.append(', '.join(unique_acronyms))
                
        if terminology_result.misspellings:
            unique_misspellings = add_unique_keywords(terminology_result.misspellings)
            if unique_misspellings:
                keyword_parts.append(', '.join(unique_misspellings))
                
        if terminology_result.layman_terms:
            unique_layman = add_unique_keywords(terminology_result.layman_terms)
            if unique_layman:
                keyword_parts.append(', '.join(unique_layman))
                
        if terminology_result.clinical_terms:
            unique_clinical = add_unique_keywords(terminology_result.clinical_terms)
            if unique_clinical:
                keyword_parts.append(', '.join(unique_clinical))
        
        # Create comprehensive keyword string
        final_keywords = ", ".join(keyword_parts) if keyword_parts else metadata_result.keywords
        
        logger.info(f"Metadata generation complete - Base: {len(metadata_result.keywords)} chars, Final: {len(final_keywords)} chars, Unique terms: {len(seen_keywords)}")
        
        # Extract codes using new engine
        coding_result = await coding_engine.extract_codes_for_spreadsheet(title, title)
        
        if not coding_result.refined_codes:
            logger.warning("No codes validated for spreadsheet processing")
            raise HTTPException(status_code=404, detail="No codes validated in clinical refinement step")
        
        # Format results - exact same format as before
        root_codes = extract_root_codes_simple(coding_result.refined_codes)
        hierarchy_codes = extract_hierarchy_codes_simple(coding_result.refined_codes)
        code_descriptions = format_enhanced_descriptions(coding_result.refined_codes)
        code_scores = format_confidence_scores(coding_result.refined_codes)
        structured_codes = format_structured_codes(coding_result.refined_codes)
        
        # Generate unique name - match client spreadsheet pattern
#         file_extension = clean_filename.lower().split('.')[-1]
#         gender = ""
#         if file_extension in ['html', 'htm']:
#             # Try different encodings
#             for encoding in ['utf-8', 'latin-1', 'cp1252']:
#                 try:
#                     html_content = file_content.decode(encoding)
#                     break
#                 except UnicodeDecodeError:
#                     continue
            
#             soup = BeautifulSoup(html_content, 'html.parser')
#             meta_tag = soup.find('meta', attrs={'name': 'Unique'})
#             unique_name = meta_tag['content'] if meta_tag and 'content' in meta_tag.attrs else None
#             meta_tag = soup.find('meta', attrs={'name': 'Gender'})
#             gender = meta_tag['content'] if meta_tag and 'content' in meta_tag.attrs else ""
#         else:
#             unique_name = title.replace(" ", "_").replace(",", "_").replace("(", "").replace(")", "")

        logger.info(f"Spreadsheet processing complete - {len(coding_result.refined_codes)} codes generated")
        logger.info(f"Using metadata - Gender: {gender}, Unique Name: {unique_name}")
        
        # Return exact same SpreadsheetRow format using extracted metadata
        return SpreadsheetRow(
            filepath=file.filename,
            title=title,
            icd_code_root=root_codes,
            icd_code_hierarchy=hierarchy_codes,
            details_description=code_descriptions,
            details_score=code_scores,
            gender=gender,  # Use extracted metadata instead of AI
            unique_name=unique_name,  # Use extracted metadata instead of AI
            keywords=final_keywords,
            diagnosis_codes=hierarchy_codes,
            cpt_codes="",
            language="English",
            source="Medical Coding System v3.0",
            document_type="Patient Education",
            icd_codes_structured=structured_codes
        )
        
    except ValueError as e:
        logger.error(f"Spreadsheet processing validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected spreadsheet processing failure: {e}")
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")


# =====  HELPER FUNCTIONS =====

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

def format_structured_codes(codes: List[RefinedCodeValidation]) -> List[Dict[str, Any]]:
    """Format codes as structured data for enhanced export capabilities"""
    structured_codes = []
    for code in codes:
        structured_codes.append({
            "icd_code": code.icd_code,
            "root_code": code.icd_code[:3] if len(code.icd_code) >= 3 else code.icd_code,
            "enhanced_description": code.enhanced_description,
            "original_description": code.original_description,
            "confidence_score": code.confidence_score,
            "confidence_percentage": f"{int(code.confidence_score * 100)}%"
        })
    return structured_codes


if __name__ == "__main__":
    import uvicorn
    logger.info("Starting Medical Coding System server...")
    uvicorn.run(app, host="0.0.0.0", port=8000) 