from pydantic import BaseModel, Field, ConfigDict
from typing import List


class ChapterPrediction(BaseModel):
    """Single chapter prediction with probability score"""
    model_config = ConfigDict(extra='forbid')
    
    chapter_name: str = Field(description="Full chapter name with code range")
    probability: float = Field(description="Probability score from 0.0 to 1.0")
    reasoning: str = Field(description="Brief explanation why this chapter matches")


class ChapterClassification(BaseModel):
    """AI Chapter Classification Response"""
    model_config = ConfigDict(extra='forbid')
    
    predictions: List[ChapterPrediction] = Field(
        description="List of up to 5 chapter predictions with probability scores",
        max_items=5
    )


class CodeValidation(BaseModel):
    """Single ICD code validation result"""
    model_config = ConfigDict(extra='forbid')
    
    icd_code: str = Field(description="The ICD-10-CM code")
    description: str = Field(description="Official code description")
    confidence_score: float = Field(description="Confidence score from 0.0 to 1.0")
    reasoning: str = Field(description="Explanation of why this code matches or doesn't match")


class ValidationResponse(BaseModel):
    """AI Validation Response for ICD codes"""
    model_config = ConfigDict(extra='forbid')
    
    validated_codes: List[CodeValidation] = Field(
        description="List of validated ICD codes with confidence scores"
    )
    overall_recommendation: str = Field(
        description="Summary recommendation about the best matching codes"
    )


# New models for spreadsheet functionality
class TitleEnrichment(BaseModel):
    """AI Title Enrichment Response"""
    model_config = ConfigDict(extra='forbid')
    
    enriched_keywords: str = Field(description="Additional medical keywords for better vector search")
    reasoning: str = Field(description="Brief explanation of enrichment")


class DocumentMetadata(BaseModel):
    """AI Document Metadata Generation Response"""
    model_config = ConfigDict(extra='forbid')
    
    gender: str = Field(description="Gender applicability: Male, Female, or Both")
    keywords: str = Field(description="Comma-separated medical keywords extracted from content")
    reasoning: str = Field(description="Brief explanation of metadata generation")


class SpreadsheetRow(BaseModel):
    """Single row for spreadsheet output"""
    filepath: str
    title: str
    gender: str
    unique_name: str
    keywords: str
    diagnosis_codes: str
    cpt_codes: str = ""  # Leave blank for now
    language: str = "English"
    source: str = "AI Medical Coding System"
    document_type: str = "Patient Education" 