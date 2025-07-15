"""Clean metadata extraction from embedded HTML metadata with AI fallback."""

from typing import Optional, Tuple
from bs4 import BeautifulSoup
import logging

logger = logging.getLogger(__name__)

def extract_embedded_metadata(file_content: bytes, filename: str) -> Tuple[str, str]:
    """
    Extract gender and unique name from HTML meta tags.
    Returns None values for non-HTML files (will use existing AI system).
    """
    
    # Only extract from HTML files
    if filename.lower().endswith(('.html', '.htm')):
        try:
            gender, unique_name = _extract_from_html_meta(file_content)
            logger.info(f"HTML metadata extracted - Gender: {gender}, Unique: {unique_name}")
            return gender, unique_name
        except Exception as e:
            logger.warning(f"Failed to extract HTML metadata: {e}")
    
    # Return None for non-HTML files (use existing AI system)
    return None, None


def _extract_from_html_meta(file_content: bytes) -> Tuple[Optional[str], Optional[str]]:
    """Extract gender and unique name from HTML meta tags."""
    
    soup = BeautifulSoup(file_content, 'html.parser')
    
    # Extract gender from meta tag
    gender_meta = soup.find('meta', attrs={'name': 'Gender'})
    gender = gender_meta.get('content', '').strip() if gender_meta else None
    
    # Extract unique name from meta tag  
    unique_meta = soup.find('meta', attrs={'name': 'Unique'})
    unique_name = unique_meta.get('content', '').strip() if unique_meta else None
    
    # Clean and validate extracted values
    if gender and unique_name:
        validated_gender = _validate_gender(gender)
        validated_unique = _clean_unique_name(unique_name)
        return validated_gender, validated_unique
    
    return None, None


def _validate_gender(gender: str) -> str:
    """Validate and clean gender value."""
    gender = gender.strip().title()  # Normalize case
    
    # Map common variations to standard values
    gender_map = {
        'Male': 'Male',
        'Female': 'Female', 
        'Both': 'Both',
        'M': 'Male',
        'F': 'Female',
        'All': 'Both',
        'Unisex': 'Both'
    }
    
    return gender_map.get(gender, 'Both')  # Default to 'Both' if unknown


def _clean_unique_name(unique_name: str) -> str:
    """Clean and validate unique name."""
    # Remove any potentially problematic characters
    import re
    
    # Keep only alphanumeric, underscores, and hyphens
    cleaned = re.sub(r'[^a-zA-Z0-9_-]', '_', unique_name)
    
    
    # Remove leading/trailing underscores
    cleaned = cleaned.strip('_')
    
    # Ensure it's not empty
    if not cleaned:
        cleaned = "document"
    
    return cleaned


 