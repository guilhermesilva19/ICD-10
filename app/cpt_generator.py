"""
CPT Code Generation Module

This module provides functionality to extract and generate CPT codes from medical documents
using OpenAI's GPT models.
"""

import logging
from typing import List, Dict, Any, Optional
from openai import OpenAI
from .config import OPENAI_API_KEY

# Configure logging
logger = logging.getLogger(__name__)

class CPTGenerator:
    """
    A class to handle CPT code generation from medical documents.
    Uses OpenAI's GPT models to analyze text and extract relevant procedure codes.
    """
    
    def __init__(self, model: str = "gpt-4-turbo"):
        """
        Initialize the CPT generator with the specified OpenAI model.
        
        Args:
            model: The OpenAI model to use for generation (default: gpt-4-turbo)
        """
        self.client = OpenAI(api_key=OPENAI_API_KEY)
        self.model = model
        logger.info(f"Initialized CPT Generator with model: {model}")
    
    def generate_cpt_codes(
        self, 
        document_text: str,
        max_codes: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Generate CPT codes from medical document text.
        
        Args:
            document_text: The text content of the medical document
            max_codes: Maximum number of CPT codes to return (default: 5)
            
        Returns:
            List of dictionaries containing CPT codes and their details
        """
        try:
            # Prepare the prompt for the AI model
            prompt = self._prepare_prompt(document_text, max_codes)
            
            # Call the OpenAI API (synchronous call)
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a medical coding assistant that extracts CPT codes from medical documents."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2,
                max_tokens=1000
            )
            
            # Parse the response
            result = response.choices[0].message.content
            cpt_codes = self._parse_response(result)
            
            # Validate and format the codes
            validated_codes = self._validate_cpt_codes(cpt_codes)
            
            return validated_codes[:max_codes]
            
        except Exception as e:
            logger.error(f"Error generating CPT codes: {str(e)}", exc_info=True)
            return []
    
    def _prepare_prompt(self, document_text: str, max_codes: int) -> str:
        """Prepare the prompt for the AI model."""
        return f"""
        Analyze the following medical document and extract up to {max_codes} relevant CPT codes.
        For each code, provide:
        1. The CPT code
        2. A brief description
        3. The confidence level (Low, Medium, High)
        4. The relevant text from the document that supports this code
        
        Format your response as a list of JSON objects with the following structure:
        [
            {{
                "code": "CPT_CODE",
                "description": "Procedure description",
                "confidence": "High/Medium/Low",
                "supporting_text": "Relevant text from the document"
            }}
        ]
        
        Document Text:
        {document_text[:10000]}  # Limit to first 10k chars to avoid token limits
        """
    
    def _parse_response(self, response_text: str) -> List[Dict[str, Any]]:
        """Parse the AI model's response into a list of CPT codes."""
        import json
        import re
        
        try:
            # Try to parse the response as JSON
            return json.loads(response_text)
        except json.JSONDecodeError:
            # If JSON parsing fails, try to extract JSON-like structures using regex
            json_matches = re.findall(r'\[\s*\{.*\}\s*\]', response_text, re.DOTALL)
            if json_matches:
                try:
                    return json.loads(json_matches[0])
                except json.JSONDecodeError:
                    logger.warning("Failed to parse JSON from response")
            
            # If all else fails, return an empty list
            return []
    
    def _validate_cpt_codes(self, codes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Validate the format of CPT codes and add any missing fields.
        
        Args:
            codes: List of code dictionaries to validate
            
        Returns:
            List of validated code dictionaries
        """
        validated = []
        
        for code in codes:
            if not isinstance(code, dict):
                continue
                
            # Ensure required fields exist
            code.setdefault('code', '')
            code.setdefault('description', '')
            code.setdefault('confidence', 'Medium')
            code.setdefault('supporting_text', '')
            
            # Clean the code (remove non-alphanumeric characters)
            if 'code' in code and code['code']:
                code['code'] = ''.join(c for c in str(code['code']) if c.isalnum())
            
            # Validate confidence level
            if 'confidence' in code and code['confidence'] not in ['High', 'Medium', 'Low']:
                code['confidence'] = 'Medium'
            
            validated.append(code)
        
        return validated
    
    def get_code_details(self, code: str) -> Optional[Dict[str, Any]]:
        """
        Get additional details for a specific CPT code.
        
        Args:
            code: The CPT code to look up
            
        Returns:
            Dictionary with code details or None if not found
        """
        try:
            # This is a placeholder - in a real implementation, you would query a CPT code database
            # or use an API like the AMA's CPT API
            return {
                'code': code,
                'description': 'Procedure description not available',
                'category': 'Category not available',
                'work_rvu': 0.0,
                'facility_fee': 0.0,
                'professional_fee': 0.0
            }
        except Exception as e:
            logger.error(f"Error getting code details for {code}: {str(e)}")
            return None
