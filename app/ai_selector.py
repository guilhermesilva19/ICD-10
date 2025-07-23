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
    MAX_ROOT_FAMILIES = 6
    PRIMARY_FAMILY_THRESHOLD = 0.8
    
    def __init__(self):
        self.client = AsyncOpenAI(api_key=OPENAI_API_KEY)
    
    async def select_relevant_codes(self, medical_text: str, candidates: List[Dict]) -> List[str]:
        """Select relevant codes with deterministic root family validation."""
        
        if not candidates:
            logger.warning("No candidate codes provided for selection")
            return []
        
        # Smart ordering by prefix and keyword relevance
        ordered_candidates = self._smart_candidate_ordering(candidates, medical_text)
        
        # Format candidates for AI processing
        formatted_candidates = self._format_candidates_for_ai(ordered_candidates)
        
        # Execute AI selection with strict parameters
        initial_selection = await self._execute_ai_selection(medical_text, formatted_candidates, ordered_candidates)
        
        if not initial_selection:
            logger.warning("AI selection returned no codes")
            return []
        
        # Validate and enforce root family focus
        validated_codes = self._validate_root_family_focus(initial_selection)
        
        
        logger.info(f"Code selection complete: {len(validated_codes)} codes from {len(self._get_root_families(validated_codes))} families")
        return validated_codes

    
    async def _execute_ai_selection(self, medical_text: str, formatted_candidates: str, candidates: List[Dict] = None) -> List[str]:
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
    
    def _smart_candidate_ordering(self, candidates: List[Dict], medical_text: str) -> List[Dict]:
        """Order candidates by relevance: prefix match between title keywords and code descriptions."""
        
        # Clean title: case insensitive, remove punctuation, handle multi-word intelligently
        title_clean = medical_text.lower().strip()
        title_clean = title_clean.replace(',', '').replace('.', '').replace('-', ' ')
        
        # Extract main medical term (first meaningful word if multi-word)
        title_words = [word for word in title_clean.split() if len(word) > 3]
        primary_term = title_words[0] if title_words else title_clean
        
        def calculate_relevance_score(candidate):
            code = candidate['icd_code']
            description = candidate['description'].lower()
            
            # Calculate prefix matches using primary medical term
            prefix_score = 0
            if len(primary_term) >= 4:
                # Use first 4-6 characters for intelligent prefix matching
                prefix = primary_term[:6] if len(primary_term) >= 6 else primary_term[:4]
                # Check if description STARTS with same prefix (highest priority)
                if description.startswith(prefix):
                    prefix_score += 5  # Highest weight for same starting prefix
                elif prefix in description:
                    prefix_score += 2  # Lower weight for prefix found anywhere
            
            # Calculate exact matches (case insensitive)
            keyword_score = 0
            if primary_term in description:
                keyword_score += 3  # Exact primary term match
            if len(title_words) > 1:
                # Multi-word titles: bonus for additional word matches
                additional_matches = sum(1 for word in title_words[1:] if word in description)
                keyword_score += additional_matches
            
            # Return tuple for sorting (higher scores first, then alphabetical)
            return (-prefix_score, -keyword_score, code)
        
        sorted_candidates = sorted(candidates, key=calculate_relevance_score)
        
        # Log the reordering for debugging
        if len(sorted_candidates) >= 10:
            title_preview = medical_text.split()[0] if medical_text.split() else "Unknown"
            logger.info(f"Smart ordering for title '{title_preview}' - Top candidates:")
            for i, candidate in enumerate(sorted_candidates[:20]):
                logger.info(f"  {i+1}. {candidate['icd_code']} - {candidate['description'][:50]}...")
        
        return sorted_candidates
    
    def _format_candidates_for_ai(self, candidates: List[Dict]) -> str:
        """Format candidates with rich clinical context for enhanced AI accuracy."""
        formatted_lines = []
        for candidate in candidates:
            # Build structured format with clinical context
            parts = [f"Code: {candidate['icd_code']}"]
            
            # Make descriptions more appealing by replacing negative language
            description = candidate['description']
        
            
            parts.append(f"Description: {description}")
            
            # Add rich clinical context if available
            if candidate.get('rich_text'):
                parts.append(f"Clinical Context: {candidate['rich_text'][:200]}...")
            
            # Add classification context
            if candidate.get('chapter'):
                parts.append(f"Chapter: {candidate['chapter']}")
            if candidate.get('section'):
                parts.append(f"Section: {candidate['section']}")
            
            # Format as structured block
            formatted_lines.append(" | ".join(parts))
            
        return "\n".join(formatted_lines) 