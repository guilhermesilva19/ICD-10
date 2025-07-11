"""Deterministic AI code selection with root family validation."""

from typing import List, Dict, Set
from openai import AsyncOpenAI
from .models import InitialSelectionResponse
from .prompts import CODE_SELECTION_PROMPT
from .config import OPENAI_API_KEY
import json
import logging

# Configure professional logging
logger = logging.getLogger(__name__)

class AICodeSelector:
    """Deterministic AI selector with root family focus validation."""
    
    MODEL = "gpt-4o-2024-08-06"
    TEMPERATURE = 0.0
    SEED = 42
    MAX_ROOT_FAMILIES = 2
    PRIMARY_FAMILY_THRESHOLD = 0.8
    
    def __init__(self):
        self.client = AsyncOpenAI(api_key=OPENAI_API_KEY)
    
    async def select_relevant_codes(self, medical_text: str, candidates: List[Dict]) -> List[str]:
        """Select relevant codes with deterministic root family validation."""
        
        if not candidates:
            logger.warning("No candidate codes provided for selection")
            return []
        
        # Ensure deterministic candidate ordering
        sorted_candidates = self._ensure_deterministic_ordering(candidates)
        
        # Format candidates for AI processing
        formatted_candidates = self._format_candidates_for_ai(sorted_candidates)
        
        # Execute AI selection with strict parameters
        initial_selection = await self._execute_ai_selection(medical_text, formatted_candidates)
        
        if not initial_selection:
            logger.warning("AI selection returned no codes")
            return []
        
        # Validate and enforce root family focus
        validated_codes = self._validate_root_family_focus(initial_selection)
        
        # Final hierarchy validation
        final_codes = self._validate_hierarchy_requirements(validated_codes)
        
        logger.info(f"Code selection complete: {len(final_codes)} codes from {len(self._get_root_families(final_codes))} families")
        return final_codes
    
    def _ensure_deterministic_ordering(self, candidates: List[Dict]) -> List[Dict]:
        """Ensure consistent candidate ordering for deterministic results."""
        # Sort by score (descending) then by code (ascending) for consistency
        return sorted(candidates, key=lambda x: (-x['score'], x['icd_code']))
    
    async def _execute_ai_selection(self, medical_text: str, formatted_candidates: str) -> List[str]:
        """Execute AI selection with strict deterministic parameters."""
        
        prompt = CODE_SELECTION_PROMPT.format(
            medical_text=medical_text,
            candidate_codes=formatted_candidates
        )
        
        try:
            response = await self.client.chat.completions.create(
                model=self.MODEL,
                messages=[
                    {"role": "system", "content": "You are a medical coding expert performing precise root family-focused code selection."},
                    {"role": "user", "content": prompt}
                ],
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "name": "code_selection",
                        "strict": True,
                        "schema": InitialSelectionResponse.model_json_schema()
                    }
                },
                temperature=self.TEMPERATURE,
                top_p=1.0,
                seed=self.SEED
            )
            
            result_json = json.loads(response.choices[0].message.content)
            selection_result = InitialSelectionResponse(**result_json)
            
            logger.info(f"AI selected {len(selection_result.selected_codes)} codes for validation")
            return selection_result.selected_codes
            
        except Exception as e:
            logger.error(f"AI selection failed: {e}")
            return []
    
    def _validate_root_family_focus(self, selected_codes: List[str]) -> List[str]:
        """Validate and enforce 1-2 root family focus requirement."""
        
        if not selected_codes:
            return []
        
        # Analyze root family distribution
        family_distribution = self._analyze_root_family_distribution(selected_codes)
        
        # Sort families by code count (descending)
        sorted_families = sorted(family_distribution.items(), key=lambda x: x[1], reverse=True)
        
        # Enforce maximum 2 families rule
        allowed_families = set([family[0] for family in sorted_families[:self.MAX_ROOT_FAMILIES]])
        
        # Filter codes to allowed families
        validated_codes = [code for code in selected_codes if self._extract_root_family(code) in allowed_families]
        
        # Log validation results
        primary_family = sorted_families[0][0] if sorted_families else "None"
        primary_count = sorted_families[0][1] if sorted_families else 0
        total_count = len(validated_codes)
        primary_percentage = (primary_count / total_count) if total_count > 0 else 0
        
        logger.info(f"Root family validation - Primary: {primary_family} ({primary_count}/{total_count} = {primary_percentage:.1%})")
        
        if len(allowed_families) > 1:
            secondary_family = sorted_families[1][0]
            secondary_count = sorted_families[1][1]
            logger.info(f"Secondary family: {secondary_family} ({secondary_count} codes)")
        
        return validated_codes
    
    def _validate_hierarchy_requirements(self, codes: List[str]) -> List[str]:
        """Ensure no root codes (3-character codes) are included in final selection."""
        
        hierarchy_codes = []
        filtered_root_codes = []
        
        for code in codes:
            if self._is_root_code(code):
                filtered_root_codes.append(code)
                logger.warning(f"Filtered out root code: {code}")
            else:
                hierarchy_codes.append(code)
        
        if filtered_root_codes:
            logger.info(f"Removed {len(filtered_root_codes)} root codes, kept {len(hierarchy_codes)} hierarchy codes")
        
        return hierarchy_codes
    
    def _analyze_root_family_distribution(self, codes: List[str]) -> Dict[str, int]:
        """Analyze distribution of codes across root families."""
        family_counts = {}
        for code in codes:
            root_family = self._extract_root_family(code)
            family_counts[root_family] = family_counts.get(root_family, 0) + 1
        return family_counts
    
    def _extract_root_family(self, code: str) -> str:
        """Extract root family (first 3 characters) from ICD code."""
        return code[:3] if len(code) >= 3 else code
    
    def _get_root_families(self, codes: List[str]) -> Set[str]:
        """Get unique root families from code list."""
        return set([self._extract_root_family(code) for code in codes])
    
    def _is_root_code(self, code: str) -> bool:
        """Check if code is a root code (3 characters without decimal)."""
        return len(code) == 3 and code.isalnum()
    
    def _format_candidates_for_ai(self, candidates: List[Dict]) -> str:
        """Format candidates for AI consumption with consistent ordering."""
        formatted_lines = []
        for candidate in candidates:
            line = f"- {candidate['icd_code']}: {candidate['description']}"
            formatted_lines.append(line)
        return "\n".join(formatted_lines) 