"""Document metadata generation with deterministic processing."""

from openai import OpenAI
from typing import Optional
from .models import DocumentMetadata, EnhancedTerminology
from .prompts import METADATA_GENERATION_PROMPT, ENHANCED_TERMINOLOGY_PROMPT
from .config import OPENAI_API_KEY
import json

class MetadataGenerator:
    """Document metadata generation using deterministic AI processing."""
    
    MODEL = "gpt-4o-2024-08-06"
    TEMPERATURE = 0.0
    
    def __init__(self):
        self.client = OpenAI(api_key=OPENAI_API_KEY)
    
    def generate_metadata(self, title: str, content: Optional[str] = None) -> DocumentMetadata:
        """Generate core document metadata from title and content (Step 1)."""
        
        if not title or not title.strip():
            return DocumentMetadata(
                gender="Both",
                keywords=title or "",
                reasoning="Empty title provided"
            )
        
        try:
            analysis_text = content.strip() if content else title.strip()
            
            prompt = METADATA_GENERATION_PROMPT.format(
                title=title.strip(),
                content=analysis_text
            )
            
            response = self.client.chat.completions.create(
                model=self.MODEL,
                messages=[
                    {"role": "system", "content": "You are a medical documentation expert."},
                    {"role": "user", "content": prompt}
                ],
                response_format={
                    "type": "json_schema", 
                    "json_schema": {
                        "name": "document_metadata",
                        "strict": True,
                        "schema": DocumentMetadata.model_json_schema()
                    }
                },
                temperature=self.TEMPERATURE,
                top_p=1.0
            )
            
            result_json = json.loads(response.choices[0].message.content)
            return DocumentMetadata(**result_json)
            
        except Exception:
            return DocumentMetadata(
                gender="Both",
                keywords=title,
                reasoning="Fallback due to processing error"
            )
    
    def generate_enhanced_terminology(self, title: str, base_keywords: str, content: Optional[str] = None) -> EnhancedTerminology:
        """Generate enhanced terminology with synonyms, acronyms, and terms."""
        
        if not title or not title.strip():
            return EnhancedTerminology(
                synonyms="",
                acronyms="",
                misspellings="",
                layman_terms="",
                clinical_terms="",
                reasoning="Empty title provided"
            )
        
        try:
            analysis_text = content.strip() if content else title.strip()
            
            prompt = ENHANCED_TERMINOLOGY_PROMPT.format(
                title=title.strip(),
                core_keywords=base_keywords.strip(),
                content=analysis_text
            )
            
            response = self.client.chat.completions.create(
                model=self.MODEL,
                messages=[
                    {"role": "system", "content": "You are a medical terminology enhancement expert."},
                    {"role": "user", "content": prompt}
                ],
                response_format={
                    "type": "json_schema", 
                    "json_schema": {
                        "name": "enhanced_terminology",
                        "strict": True,
                        "schema": EnhancedTerminology.model_json_schema()
                    }
                },
                temperature=self.TEMPERATURE,
                top_p=1.0
            )
            
            result_json = json.loads(response.choices[0].message.content)
            return EnhancedTerminology(**result_json)
            
        except Exception:
            return EnhancedTerminology(
                synonyms=base_keywords,
                acronyms="",
                misspellings="",
                layman_terms="",
                clinical_terms=base_keywords,
                reasoning="Fallback due to processing error"
            ) 