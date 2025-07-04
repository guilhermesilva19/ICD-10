"""AI-powered validation of ICD-10-CM codes"""

from openai import OpenAI, AsyncOpenAI
from .config import OPENAI_API_KEY
from .models import ValidationResponse, CodeValidation
from .prompts import VALIDATION_PROMPT
import json
from pydantic import ValidationError


class AIValidator:
    """Validates ICD-10-CM codes against medical text using AI"""
    
    def __init__(self):
        self.client = OpenAI(api_key=OPENAI_API_KEY)
        self.async_client = AsyncOpenAI(api_key=OPENAI_API_KEY)
        self.model = "gpt-4o-2024-08-06"
    
    def _format_candidate_codes(self, candidate_codes: list) -> str:
        """Helper to format candidate codes for the prompt"""
        return "\n".join([f"- {code['icd_code']}: {code['description']}" for code in candidate_codes])

    def validate_codes(self, medical_text: str, candidate_codes: list) -> ValidationResponse:
        """
        Synchronously validates a list of candidate codes.
        Used by the original /analyze endpoint.
        """
        if not candidate_codes:
            return ValidationResponse(validated_codes=[], overall_recommendation="No candidates provided.")

        formatted_codes = self._format_candidate_codes(candidate_codes)
        prompt = VALIDATION_PROMPT.format(
            medical_text=medical_text,
            candidate_codes=formatted_codes
        )
        
        completion = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "🚨 CRITICAL CODE VALIDATION 🚨 You are an expert medical coder. Your task is to evaluate how well ICD codes match the documentation."},
                {"role": "user", "content": prompt}
            ],
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "code_validation",
                    "strict": True,
                    "schema": ValidationResponse.model_json_schema()
                }
            },
            temperature=0.0,
            top_p=0.1
        )
        
        try:
            result_json = json.loads(completion.choices[0].message.content)
            return ValidationResponse(**result_json)
        except (json.JSONDecodeError, ValidationError) as e:
            raise ValueError(f"Failed to parse OpenAI validation response: {e}")

    async def validate_codes_async(self, medical_text: str, candidate_codes: list) -> ValidationResponse:
        """
        Asynchronously validates a list of candidate codes.
        Used for parallel processing in the /process-spreadsheet endpoint.
        """
        if not candidate_codes:
            return ValidationResponse(validated_codes=[], overall_recommendation="No candidates provided.")

        formatted_codes = self._format_candidate_codes(candidate_codes)
        prompt = VALIDATION_PROMPT.format(
            medical_text=medical_text,
            candidate_codes=formatted_codes
        )

        try:
            completion = await self.async_client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "🚨 CRITICAL CODE VALIDATION 🚨 You are an expert medical coder. Your task is to evaluate how well ICD codes match the documentation."},
                    {"role": "user", "content": prompt}
                ],
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "name": "code_validation",
                        "strict": True,
                        "schema": ValidationResponse.model_json_schema()
                    }
                },
                temperature=0.0,
                top_p=0.1
            )
            result_json = json.loads(completion.choices[0].message.content)
            return ValidationResponse(**result_json)
        except Exception as e:
            print(f"Error during async validation: {e}")
            return ValidationResponse(validated_codes=[], overall_recommendation=f"API call failed: {e}")

    def get_high_confidence_codes(self, validation_result: ValidationResponse, 
                                    threshold: float = 0.5) -> list[CodeValidation]:
        """Filters a validation result for codes above a given confidence threshold."""
        if not validation_result or not validation_result.validated_codes:
            return []
        
        return [
            code for code in validation_result.validated_codes 
            if code.confidence_score >= threshold
        ] 