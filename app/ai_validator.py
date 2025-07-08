"""AI-powered validation of ICD-10-CM codes with two-step process"""

from openai import OpenAI, AsyncOpenAI
from .config import OPENAI_API_KEY
from .models import (
    InitialSelectionResponse, ClinicalRefinementResponse, RefinedCodeValidation
)
from .prompts import INITIAL_SELECTION_PROMPT, CLINICAL_REFINEMENT_PROMPT
import json
from pydantic import ValidationError


class AIValidator:
    """Validates ICD-10-CM codes using professional two-step AI process"""
    
    def __init__(self):
        self.client = OpenAI(api_key=OPENAI_API_KEY)
        self.async_client = AsyncOpenAI(api_key=OPENAI_API_KEY)
        self.model = "gpt-4o-2024-08-06"
    
    def _format_simple_codes(self, candidate_codes: list) -> str:
        """Helper to format codes as simple list for initial selection"""
        return "\n".join([f"- {code['icd_code']}: {code['description']}" for code in candidate_codes])

    def _format_selected_codes(self, selected_codes: list, all_candidates: list) -> str:
        """Helper to format selected codes with their descriptions for refinement"""
        # Create lookup for descriptions
        code_lookup = {code['icd_code']: code['description'] for code in all_candidates}
        
        formatted = []
        for code in selected_codes:
            description = code_lookup.get(code, "Description not found")
            formatted.append(f"- {code}: {description}")
        
        return "\n".join(formatted)

    async def initial_selection(self, medical_text: str, candidate_codes: list) -> InitialSelectionResponse:
        """
        Step 1: Initial code selection - select ~50 relevant codes from candidates
        """
        if not candidate_codes:
            return InitialSelectionResponse(selected_codes=[])

        formatted_codes = self._format_simple_codes(candidate_codes)
        prompt = INITIAL_SELECTION_PROMPT.format(
            medical_text=medical_text,
            candidate_codes=formatted_codes
        )
        
        try:
            completion = await self.async_client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a medical coding expert performing initial code selection."},
                    {"role": "user", "content": prompt}
                ],
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "name": "initial_selection",
                        "strict": True,
                        "schema": InitialSelectionResponse.model_json_schema()
                    }
                },
                temperature=0.2,
                top_p=0.1
            )
            
            result_json = json.loads(completion.choices[0].message.content)
            return InitialSelectionResponse(**result_json)
            
        except Exception as e:
            print(f"Error during initial selection: {e}")
            return InitialSelectionResponse(selected_codes=[])

    async def clinical_refinement(self, medical_text: str, selected_codes: list, all_candidates: list) -> ClinicalRefinementResponse:
        """
        Step 2: Clinical refinement - remove irrelevant codes and enhance descriptions with confidence scores
        """
        if not selected_codes:
            return ClinicalRefinementResponse(
                refined_codes=[],
                clinical_summary="No codes provided for refinement."
            )

        formatted_codes = self._format_selected_codes(selected_codes, all_candidates)
        prompt = CLINICAL_REFINEMENT_PROMPT.format(
            medical_text=medical_text,
            selected_codes=formatted_codes
        )
        
        try:
            completion = await self.async_client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a senior medical coding specialist performing clinical validation and enhancement."},
                    {"role": "user", "content": prompt}
                ],
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "name": "clinical_refinement",
                        "strict": True,
                        "schema": ClinicalRefinementResponse.model_json_schema()
                    }
                },
                temperature=0.2,
                top_p=0.1
            )
            
            result_json = json.loads(completion.choices[0].message.content)
            return ClinicalRefinementResponse(**result_json)
            
        except Exception as e:
            print(f"Error during clinical refinement: {e}")
            return ClinicalRefinementResponse(
                refined_codes=[],
                clinical_summary=f"Clinical refinement failed: {e}"
            ) 