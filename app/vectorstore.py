"""Pinecone vector database operations for ICD code retrieval"""

from pinecone import Pinecone
from openai import OpenAI
from .config import PINECONE_API_KEY, PINECONE_INDEX_NAME, OPENAI_API_KEY


class VectorStore:
    """Handles vector operations with Pinecone for ICD code retrieval"""
    
    def __init__(self):
        self.pc = Pinecone(api_key=PINECONE_API_KEY)
        self.index = self.pc.Index(PINECONE_INDEX_NAME)
        self.openai_client = OpenAI(api_key=OPENAI_API_KEY)
    
    def _create_embedding(self, text: str) -> list:
        """Create embedding for text using OpenAI"""
        response = self.openai_client.embeddings.create(
            model="text-embedding-3-small",
            input=text
        )
        return response.data[0].embedding
    
    def search_all_codes(self, medical_text: str, top_k: int = 450) -> list:
        """
        Enhanced search for ICD codes across all chapters - optimized for two-step AI process
        
        Args:
            medical_text: The medical text to search for
            top_k: Number of results to return (optimized for 400-500 range)
            
        Returns:
            list: Comprehensive search results across all chapters
        """
        # Create embedding for the medical text
        query_embedding = self._create_embedding(medical_text)
        
        # Enhanced search with higher top_k for better coverage
        search_result = self.index.query(
            vector=query_embedding,
            top_k=min(top_k, 1000),  # Cap at 1000 for performance
            include_metadata=True
        )
        
        # Format results with enhanced metadata
        formatted_results = []
        for match in search_result.matches:
            formatted_results.append({
                'icd_code': match.id,
                'score': match.score,
                'description': match.metadata.get('description', ''),
                'rich_text': match.metadata.get('rich_text', ''),
                'chapter': match.metadata.get('chapter', ''),
                'section': match.metadata.get('section', '')
            })
        
        print(f"🔍 Vector search found {len(formatted_results)} codes for two-step AI processing")
        return formatted_results
    
    # ===== LEGACY: Keep chapter search for backward compatibility (/analyze endpoint) =====
    
    def search_codes_by_chapter(self, medical_text: str, chapter_names: list, 
                               top_k: int = 50) -> dict:
        """
        LEGACY: Search for ICD codes in specific chapters using vector similarity
        Kept for backward compatibility with /analyze endpoint
        
        Args:
            medical_text: The medical text to search for
            chapter_names: List of EXACT chapter names to filter by
            top_k: Number of results to return per chapter
            
        Returns:
            dict: Chapter-wise search results
        """
        # Create embedding for the medical text
        query_embedding = self._create_embedding(medical_text)
        
        results = {}
        
        for chapter_name in chapter_names:
            # Use the EXACT chapter name for filtering
            filter_dict = {
                "chapter": {"$eq": chapter_name}
            }
            
            # Search in Pinecone with chapter filter
            search_result = self.index.query(
                vector=query_embedding,
                top_k=top_k,
                include_metadata=True,
                filter=filter_dict
            )
            
            # Format results
            formatted_results = []
            for match in search_result.matches:
                formatted_results.append({
                    'icd_code': match.id,
                    'score': match.score,
                    'description': match.metadata.get('description', ''),
                    'rich_text': match.metadata.get('rich_text', ''),
                    'chapter': match.metadata.get('chapter', ''),
                    'section': match.metadata.get('section', '')
                })
            
            results[chapter_name] = formatted_results
        
        return results 