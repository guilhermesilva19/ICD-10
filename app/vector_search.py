"""Clean vector search operations with official validation and deterministic ordering."""

from typing import List, Dict
from pinecone import Pinecone
from openai import OpenAI
import simple_icd_10_cm as icd_lib
from .config import PINECONE_API_KEY, PINECONE_INDEX_NAME, OPENAI_API_KEY
import logging

# Configure professional logging
logger = logging.getLogger(__name__)

class VectorSearchEngine:
    """Vector search with official ICD validation and deterministic results."""
    
    MAX_CANDIDATES = 150
    EMBEDDING_MODEL = "text-embedding-3-small"
    MINIMUM_SCORE_THRESHOLD = 0.1  # Filter very low relevance results
    
    def __init__(self):
        self.pc = Pinecone(api_key=PINECONE_API_KEY)
        self.index = self.pc.Index(PINECONE_INDEX_NAME)
        self.openai_client = OpenAI(api_key=OPENAI_API_KEY)
        logger.info(f"Vector search engine initialized with model: {self.EMBEDDING_MODEL}")
    
    async def search_codes(self, search_text: str) -> List[Dict]:
        """Search for candidate codes with official validation and deterministic ordering."""
        
        logger.info(f"Executing vector search for text: {search_text[:100]}...")
        
        # Create embedding
        embedding = self._create_embedding(search_text)
        
        # Vector search with expanded results
        search_result = self.index.query(
            vector=embedding,
            top_k=self.MAX_CANDIDATES,
            include_metadata=True
        )
        
        logger.info(f"Pinecone returned {len(search_result.matches)} raw matches")
        
        # Official validation and formatting with quality filtering
        validated_candidates = []
        invalid_codes = []
        low_score_filtered = 0
        
        for match in search_result.matches:
            code = match.id
            score = match.score
            
            # Filter very low relevance scores
            if score < self.MINIMUM_SCORE_THRESHOLD:
                low_score_filtered += 1
                continue
            
            # Official ICD validation
            if icd_lib.is_valid_item(code):
                try:
                    validated_candidates.append({
                        'icd_code': code,
                        'score': score,
                        'description': icd_lib.get_description(code),
                        'rich_text': match.metadata.get('rich_text', ''),
                        'chapter': match.metadata.get('chapter', ''),
                        'section': match.metadata.get('section', '')
                    })
                except Exception as e:
                    logger.warning(f"Error processing valid code {code}: {e}")
                    invalid_codes.append(code)
            else:
                invalid_codes.append(code)
        
        # Ensure deterministic ordering for consistent results
        validated_candidates = self._ensure_deterministic_ordering(validated_candidates)
        
        # Log validation statistics
        total_matches = len(search_result.matches)
        valid_count = len(validated_candidates)
        invalid_count = len(invalid_codes)
        
        logger.info(f"Vector search validation complete:")
        logger.info(f"  Total Pinecone matches: {total_matches}")
        logger.info(f"  Low score filtered: {low_score_filtered}")
        logger.info(f"  Invalid codes filtered: {invalid_count}")
        logger.info(f"  Valid candidates returned: {valid_count}")
        
        if invalid_codes:
            logger.warning(f"Invalid codes detected: {invalid_codes[:5]}...")  # Log first 5
        
        return validated_candidates
    
    def _ensure_deterministic_ordering(self, candidates: List[Dict]) -> List[Dict]:
        """Ensure consistent ordering for deterministic results across runs."""
        # Sort by score (descending) then by ICD code (ascending) for tie-breaking
        sorted_candidates = sorted(candidates, key=lambda x: (-x['score'], x['icd_code']))
        
        logger.debug(f"Applied deterministic ordering to {len(candidates)} candidates")
        return sorted_candidates
    
    def _create_embedding(self, text: str) -> List[float]:
        """Create embedding for text using OpenAI with error handling."""
        try:
            response = self.openai_client.embeddings.create(
                model=self.EMBEDDING_MODEL,
                input=text.strip()
            )
            embedding = response.data[0].embedding
            logger.debug(f"Created embedding for text length: {len(text)} chars")
            return embedding
            
        except Exception as e:
            logger.error(f"Embedding creation failed: {e}")
            raise RuntimeError(f"Failed to create embedding: {e}") 