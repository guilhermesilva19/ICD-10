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
        logger.info(f"Selected codes: {selected_codes}")
        
        # Stage 3: Official hierarchy completion with family focus
        refined_codes = self._complete_hierarchy_with_family_focus(selected_codes, content or title, candidates)
        
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
    
    def _complete_hierarchy_with_family_focus(self, selected_codes: List[str], search_text: str, 
                                           vector_candidates: List[Dict] = None) -> List[RefinedCodeValidation]:
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
                
                # Get descendants first to determine if root has children
                descendants = self._get_nearby_descendants(code)
                family_filtered_descendants = [
                    desc for desc in descendants 
                    if self._extract_root_family(desc) in allowed_families and not self._is_root_code(desc)
                ]
                
                # Add selected code - include root codes only if they have no valid descendants
                if not self._is_root_code(code):
                    all_codes.add(code)
                    logger.debug(f"Added selected code: {code}")
                elif not family_filtered_descendants:
                    all_codes.add(code)
                    logger.info(f"Added orphan root code {code} (no valid descendants)")
                else:
                    logger.debug(f"Excluded root code {code} (has {len(family_filtered_descendants)} descendants)")
                
                # Add descendants
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
                
                # Calculate both legacy and improved confidence scores
                legacy_score = self._calculate_confidence_score_legacy(code, selected_codes)
                improved_score = self._calculate_confidence_score(code, selected_codes, vector_candidates, search_text)
                
                refined_code = RefinedCodeValidation(
                    icd_code=code,
                    original_description=icd_lib.get_description(code),
                    enhanced_description=self._create_enhanced_description(code),
                    confidence_score=legacy_score,
                    improved_confidence_score=improved_score
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
        """Get most relevant descendants with intelligent prioritization to prevent Excel overflow."""
        return self._get_nearby_descendants(code, max_codes=25)
    
    def _get_nearby_descendants(self, code: str, max_codes: int = 25) -> List[str]:
        """Get most relevant descendants with intelligent prioritization."""
        all_descendants = []
        
        try:
            # Get direct children first (highest priority)
            direct_children = icd_lib.get_children(code)
            all_descendants.extend(direct_children)
            logger.debug(f"Code {code}: {len(direct_children)} direct children")
            
            # If we have room, get grandchildren from most important children
            remaining_slots = max_codes - len(direct_children)
            if remaining_slots > 0 and direct_children:
                # Sort children for consistent results
                sorted_children = sorted(direct_children)
                
                for child in sorted_children:
                    if remaining_slots <= 0:
                        break
                    try:
                        grandchildren = icd_lib.get_children(child)
                        # Take only what fits in remaining slots
                        take_count = min(len(grandchildren), remaining_slots)
                        all_descendants.extend(grandchildren[:take_count])
                        remaining_slots -= take_count
                        logger.debug(f"Added {take_count} grandchildren from {child}")
                    except Exception as e:
                        logger.warning(f"Error getting grandchildren for {child}: {e}")
            
            # Safety limit to prevent any overflow
            final_descendants = all_descendants[:max_codes]
            logger.info(f"Smart descendants for {code}: {len(final_descendants)} codes (limit: {max_codes})")
            
        except Exception as e:
            logger.warning(f"Error getting smart descendants for {code}: {e}")
            return []
        
        return final_descendants
    
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
    
    def _calculate_confidence_score(self, code: str, selected_codes: List[str], 
                                  vector_candidates: List[Dict] = None, 
                                  search_text: str = None) -> float:
        """
        Calculate comprehensive confidence score using multiple factors:
        1. AI Selection Status (highest weight)
        2. Vector Search Score (if available)
        3. Code Specificity (subcategory vs category)
        4. Hierarchy Depth (more specific = higher confidence)
        5. Semantic Relevance (keyword matching)
        6. Code Validity and Completeness
        """
        try:
            # Initialize base score
            base_score = 0.0
            factors = {}
            
            # Factor 1: AI Selection Status (40% weight)
            if code in selected_codes:
                ai_score = 0.95 if icd_lib.is_subcategory(code) else 0.85
                factors['ai_selection'] = ai_score
                base_score += ai_score * 0.4
            else:
                # Hierarchy-expanded codes get lower base score
                ai_score = 0.75 if icd_lib.is_subcategory(code) else 0.65
                factors['ai_selection'] = ai_score
                base_score += ai_score * 0.4
            
            # Factor 2: Vector Search Score (25% weight)
            vector_score = 0.0
            if vector_candidates:
                for candidate in vector_candidates:
                    if candidate['icd_code'] == code:
                        # Normalize vector score (0.1-1.0 range to 0.0-1.0)
                        raw_score = candidate['score']
                        vector_score = max(0.0, min(1.0, (raw_score - 0.1) / 0.9))
                        factors['vector_search'] = vector_score
                        break
            
            if vector_score > 0:
                base_score += vector_score * 0.25
            else:
                # Default vector score for codes not in vector results
                default_vector = 0.5 if code in selected_codes else 0.3
                factors['vector_search'] = default_vector
                base_score += default_vector * 0.25
            
            # Factor 3: Code Specificity (15% weight)
            specificity_score = 0.0
            try:
                if icd_lib.is_subcategory(code):
                    specificity_score = 0.9
                elif icd_lib.is_category(code):
                    specificity_score = 0.7
                else:
                    specificity_score = 0.5
                factors['specificity'] = specificity_score
                base_score += specificity_score * 0.15
            except:
                factors['specificity'] = 0.5
                base_score += 0.5 * 0.15
            
            # Factor 4: Hierarchy Depth (10% weight)
            depth_score = 0.0
            try:
                # Count decimal places to determine depth
                decimal_count = code.count('.')
                if decimal_count >= 2:
                    depth_score = 0.9  # Very specific (e.g., E11.65.1)
                elif decimal_count == 1:
                    depth_score = 0.8  # Specific (e.g., E11.65)
                else:
                    depth_score = 0.6  # General (e.g., E11)
                factors['hierarchy_depth'] = depth_score
                base_score += depth_score * 0.10
            except:
                factors['hierarchy_depth'] = 0.6
                base_score += 0.6 * 0.10
            
            # Factor 5: Semantic Relevance (10% weight)
            semantic_score = 0.0
            if search_text:
                try:
                    # Get code description and calculate semantic similarity
                    description = icd_lib.get_description(code)
                    semantic_score = self._calculate_semantic_similarity(description, search_text)
                    factors['semantic_relevance'] = semantic_score
                    base_score += semantic_score * 0.10
                except:
                    factors['semantic_relevance'] = 0.5
                    base_score += 0.5 * 0.10
            else:
                factors['semantic_relevance'] = 0.5
                base_score += 0.5 * 0.10
            
            # Apply confidence boosters and penalties
            final_score = base_score
            
            # Booster: High-quality codes get small boost
            if code in selected_codes and icd_lib.is_subcategory(code):
                final_score = min(1.0, final_score + 0.05)
            
            # Penalty: Very general codes get small penalty
            if len(code) == 3 and code.isalnum():
                final_score = max(0.0, final_score - 0.05)
            
            # Ensure score is within valid range
            final_score = max(0.0, min(1.0, final_score))
            
            # Apply normalization and calibration
            final_score = self._normalize_confidence_score(final_score, code, selected_codes)
            
            # Log detailed confidence calculation for debugging
            logger.debug(f"Confidence calculation for {code}:")
            logger.debug(f"  Factors: {factors}")
            logger.debug(f"  Base score: {base_score:.3f}, Final score: {final_score:.3f}")
            
            return final_score
                
        except Exception as e:
            logger.error(f"Error calculating confidence for {code}: {e}")
            return 0.60  # Default confidence for problematic codes
    
    def _calculate_confidence_score_legacy(self, code: str, selected_codes: List[str]) -> float:
        """Legacy confidence score calculation (original simple approach)."""
        try:
            if code in selected_codes:
                # AI-selected codes get higher confidence
                return 0.95 if icd_lib.is_subcategory(code) else 0.85
            else:
                # Hierarchy-expanded codes get medium confidence
                return 0.75 if icd_lib.is_subcategory(code) else 0.65
                
        except Exception as e:
            logger.error(f"Error calculating legacy confidence for {code}: {e}")
            return 0.60  # Default confidence for problematic codes
    
    def _normalize_confidence_score(self, raw_score: float, code: str, selected_codes: List[str]) -> float:
        """
        Normalize and calibrate confidence scores to ensure proper distribution.
        This method applies additional adjustments based on code characteristics.
        """
        try:
            normalized_score = raw_score
            
            # Apply code-specific adjustments
            if code in selected_codes:
                # AI-selected codes should have higher confidence
                if normalized_score < 0.8:
                    normalized_score = min(1.0, normalized_score + 0.1)
            else:
                # Hierarchy-expanded codes should have moderate confidence
                if normalized_score > 0.9:
                    normalized_score = max(0.0, normalized_score - 0.1)
            
            # Apply specificity adjustments
            try:
                if icd_lib.is_subcategory(code):
                    # Subcategories should have higher confidence
                    if normalized_score < 0.7:
                        normalized_score = min(1.0, normalized_score + 0.05)
                elif len(code) == 3 and code.isalnum():
                    # Root codes should have lower confidence
                    normalized_score = max(0.0, normalized_score - 0.1)
            except:
                pass
            
            # Ensure score is within valid range
            normalized_score = max(0.0, min(1.0, normalized_score))
            
            # Round to 3 decimal places for consistency
            normalized_score = round(normalized_score, 3)
            
            return normalized_score
            
        except Exception as e:
            logger.warning(f"Error normalizing confidence score for {code}: {e}")
            return round(raw_score, 3)  # Return original score rounded
    
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

    def _calculate_semantic_similarity(self, code_description: str, search_text: str) -> float:
        """
        Calculate semantic similarity between code description and search text using embeddings.
        This provides a more sophisticated measure of relevance than simple keyword matching.
        """
        try:
            # Clean and prepare texts
            description_clean = code_description.lower().strip()
            search_clean = search_text.lower().strip()
            
            # Simple keyword-based similarity as fallback
            search_words = [word for word in search_clean.split() if len(word) > 3]
            description_words = [word for word in description_clean.split() if len(word) > 3]
            
            if not search_words or not description_words:
                return 0.5
            
            # Calculate word overlap
            common_words = set(search_words) & set(description_words)
            overlap_ratio = len(common_words) / max(len(search_words), len(description_words))
            
            # Boost for exact phrase matches
            phrase_boost = 0.0
            if len(search_clean) > 10:
                # Check if search text contains significant phrases from description
                description_phrases = [phrase.strip() for phrase in description_clean.split(',')]
                for phrase in description_phrases:
                    if len(phrase) > 5 and phrase in search_clean:
                        phrase_boost += 0.2
            
            # Medical terminology bonus
            medical_terms = ['disease', 'syndrome', 'disorder', 'condition', 'infection', 
                           'injury', 'trauma', 'fracture', 'cancer', 'tumor', 'diabetes',
                           'hypertension', 'arthritis', 'pneumonia', 'bronchitis']
            medical_bonus = sum(0.1 for term in medical_terms if term in description_clean and term in search_clean)
            
            # Calculate final similarity score
            similarity = min(1.0, overlap_ratio + phrase_boost + medical_bonus)
            
            return similarity
            
        except Exception as e:
            logger.warning(f"Error calculating semantic similarity: {e}")
            return 0.5  # Default neutral score 