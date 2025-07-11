"""Medical coding engine with deterministic processing and official ICD validation."""

from typing import List, Dict, Optional, Set
import simple_icd_10_cm as icd_lib
from .vector_search import VectorSearchEngine
from .ai_selector import AICodeSelector
from .models import RefinedCodeValidation, ClinicalRefinementResponse
import hashlib
import logging

# Configure professional logging
logger = logging.getLogger(__name__)

class MedicalCodingEngine:
    """Core engine for medical code extraction with official ICD validation."""
    
    def __init__(self):
        self.vector_engine = VectorSearchEngine()
        self.ai_selector = AICodeSelector()
        self._initialize_official_icd_library()
    
    def _initialize_official_icd_library(self) -> None:
        """Initialize official 2025 ICD-10-CM data with comprehensive logging."""
        try:
            logger.info("Initializing official ICD-10-CM library...")
            
            icd_lib.change_version(
                all_codes_file_path="test-data/icd10cm-codes-April-2025.txt",
                classification_data_file_path="test-data/icd10cm_tabular_2025.xml"
            )
            
            # Verify library functionality with test queries
            test_code = "F32.1"
            is_valid = icd_lib.is_valid_item(test_code)
            description = icd_lib.get_description(test_code) if is_valid else "Not found"
            children_count = len(icd_lib.get_children(test_code)) if is_valid else 0
            
            logger.info(f"ICD library validation - Test code {test_code}: valid={is_valid}")
            logger.info(f"Test description: {description}")
            logger.info(f"Test children count: {children_count}")
            
            # Get total codes available
            total_codes = len(icd_lib.get_all_codes())
            logger.info(f"ICD library loaded successfully - Total codes available: {total_codes}")
            
        except Exception as e:
            logger.error(f"Failed to initialize ICD library: {e}")
            raise RuntimeError(f"Critical failure loading official ICD data: {e}")
    
    async def extract_codes_for_spreadsheet(self, title: str, content: Optional[str] = None) -> ClinicalRefinementResponse:
        """
        Extract ICD codes maintaining exact response format for spreadsheet processing.
        
        Args:
            title: Document title
            content: Optional document content
            
        Returns:
            ClinicalRefinementResponse: Existing format with refined_codes and clinical_summary
        """
        logger.info(f"Starting code extraction for: {title[:50]}...")
        
        # Stage 1: Use search text directly (already prepared deterministically)
        candidates = await self.vector_engine.search_codes(content or title)
        
        if not candidates:
            logger.warning("No vector search candidates found")
            return ClinicalRefinementResponse(
                refined_codes=[],
                clinical_summary="No relevant codes found in vector search."
            )
        
        logger.info(f"Vector search returned {len(candidates)} candidate codes")
        
        # Stage 2: AI selection with root family validation
        selected_codes = await self.ai_selector.select_relevant_codes(content or title, candidates)
        
        if not selected_codes:
            logger.warning("No codes selected by AI analysis")
            return ClinicalRefinementResponse(
                refined_codes=[],
                clinical_summary="No codes selected by AI analysis."
            )
        
        logger.info(f"AI selected {len(selected_codes)} codes for hierarchy completion")
        
        # Stage 3: Official hierarchy completion with family focus
        refined_codes = self._complete_hierarchy_with_family_focus(selected_codes, content or title)
        
        summary = self._generate_clinical_summary(selected_codes, refined_codes)
        
        logger.info(f"Code extraction complete: {len(refined_codes)} final codes")
        
        return ClinicalRefinementResponse(
            refined_codes=refined_codes,
            clinical_summary=summary
        )
    
    def _prepare_search_text(self, title: str, content: Optional[str] = None) -> str:
        """Prepare search text with smart enhancement."""
        if content and len(content.strip()) > 50:
            # Use content if substantial
            search_text = f"{title} {content[:500]}"
        else:
            # Use title, duplicate if short
            search_text = f"{title} {title}" if len(title) < 50 else title
        
        return search_text.strip()
    
    def _complete_hierarchy_with_family_focus(self, selected_codes: List[str], search_text: str) -> List[RefinedCodeValidation]:
        """Complete hierarchy using official ICD structure with family focus validation."""
        
        # Get allowed root families from selected codes
        allowed_families = self._extract_allowed_root_families(selected_codes)
        logger.info(f"Hierarchy completion for families: {sorted(allowed_families)}")
        
        all_codes = set()
        icd_errors = []
        
        # Add selected codes and their official children within family constraints
        for code in selected_codes:
            try:
                if not icd_lib.is_valid_item(code):
                    logger.warning(f"Invalid ICD code detected: {code}")
                    icd_errors.append(code)
                    continue
                
                # Add the selected code if it's not a root code
                if not self._is_root_code(code):
                    all_codes.add(code)
                    logger.debug(f"Added selected code: {code}")
                else:
                    logger.warning(f"Filtered out root code from selection: {code}")
                
                # Add ALL official descendants (recursive) within allowed families
                descendants = self._get_all_descendants(code)
                family_filtered_descendants = [
                    desc for desc in descendants 
                    if self._extract_root_family(desc) in allowed_families and not self._is_root_code(desc)
                ]
                
                all_codes.update(family_filtered_descendants)
                logger.debug(f"Added {len(family_filtered_descendants)} descendants for {code}")
                
            except Exception as e:
                logger.error(f"Error processing code {code}: {e}")
                icd_errors.append(code)
        
        if icd_errors:
            logger.warning(f"ICD library errors for codes: {icd_errors}")
        
        # Convert to RefinedCodeValidation objects with validation
        refined_codes = []
        validation_errors = []
        
        for code in sorted(all_codes):
            try:
                # Double-check code validity and hierarchy requirements
                if not icd_lib.is_valid_item(code):
                    validation_errors.append(f"Invalid: {code}")
                    continue
                
                if self._is_root_code(code):
                    validation_errors.append(f"Root code filtered: {code}")
                    continue
                
                refined_code = RefinedCodeValidation(
                    icd_code=code,
                    original_description=icd_lib.get_description(code),
                    enhanced_description=self._create_enhanced_description(code),
                    confidence_score=self._calculate_confidence_score(code, selected_codes)
                )
                refined_codes.append(refined_code)
                
            except Exception as e:
                validation_errors.append(f"Validation error for {code}: {e}")
        
        if validation_errors:
            logger.warning(f"Validation issues: {validation_errors[:5]}")  # Log first 5 to avoid spam
        
        # Final family validation logging
        final_families = self._extract_allowed_root_families([rc.icd_code for rc in refined_codes])
        logger.info(f"Final hierarchy: {len(refined_codes)} codes across {len(final_families)} families: {sorted(final_families)}")
        
        return refined_codes
    
    def _extract_allowed_root_families(self, codes: List[str]) -> Set[str]:
        """Extract unique root families from code list."""
        return set([self._extract_root_family(code) for code in codes])
    
    def _extract_root_family(self, code: str) -> str:
        """Extract root family (first 3 characters) from ICD code."""
        return code[:3] if len(code) >= 3 else code
    
    def _is_root_code(self, code: str) -> bool:
        """Check if code is a root code (3 characters without decimal)."""
        return len(code) == 3 and code.isalnum()
    
    def _get_all_descendants(self, code: str) -> List[str]:
        """Recursively get ALL descendants of a code down to leaf nodes."""
        all_descendants = []
        
        try:
            # Get direct children
            children = icd_lib.get_children(code)
            
            for child in children:
                all_descendants.append(child)
                # Recursively get grandchildren, great-grandchildren, etc.
                descendants = self._get_all_descendants(child)
                all_descendants.extend(descendants)
                
        except Exception as e:
            logger.warning(f"Error getting descendants for {code}: {e}")
        
        return all_descendants
    
    def _create_enhanced_description(self, code: str) -> str:
        """Create enhanced description using official ICD data."""
        try:
            official_description = icd_lib.get_description(code)
            
            # Add inclusion terms if available
            inclusion_terms = icd_lib.get_inclusion_term(code)
            if inclusion_terms and len(inclusion_terms) > 0:
                enhanced = f"{official_description} (includes: {', '.join(inclusion_terms[:2])})"
            else:
                enhanced = official_description
            
            return enhanced
            
        except Exception as e:
            logger.error(f"Error creating enhanced description for {code}: {e}")
            return f"Code {code} - Description unavailable"
    
    def _calculate_confidence_score(self, code: str, selected_codes: List[str]) -> float:
        """Calculate confidence score based on code type and selection."""
        try:
            if code in selected_codes:
                # AI-selected codes get higher confidence
                return 0.95 if icd_lib.is_subcategory(code) else 0.85
            else:
                # Hierarchy-expanded codes get medium confidence
                return 0.75 if icd_lib.is_subcategory(code) else 0.65
                
        except Exception as e:
            logger.error(f"Error calculating confidence for {code}: {e}")
            return 0.60  # Default confidence for problematic codes
    
    def _generate_clinical_summary(self, selected_codes: List[str], refined_codes: List[RefinedCodeValidation]) -> str:
        """Generate clinical summary."""
        selected_families = len(self._extract_allowed_root_families(selected_codes))
        final_families = len(self._extract_allowed_root_families([rc.icd_code for rc in refined_codes]))
        
        return (f"Identified {len(selected_codes)} primary codes through AI analysis across {selected_families} root families. "
                f"Completed with official ICD hierarchy to {len(refined_codes)} total codes spanning {final_families} families. "
                f"All codes validated against 2025 ICD-10-CM standards with root family focus enforcement.")
    
    def generate_deterministic_input_signature(self, title: str, content: Optional[str] = None) -> str:
        """Generate deterministic signature for input tracking (no caching)."""
        input_data = f"{title.strip().lower()}|{content.strip().lower() if content else ''}"
        return hashlib.md5(input_data.encode()).hexdigest()[:12] 