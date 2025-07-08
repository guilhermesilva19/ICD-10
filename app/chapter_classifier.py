"""Chapter classification using OpenAI structured outputs"""

from openai import OpenAI
from .config import OPENAI_API_KEY, ICD_CHAPTERS
from .models import ChapterClassification
from .prompts import CHAPTER_CLASSIFICATION_PROMPT


class ChapterClassifier:
    """Classifies medical text into ICD-10-CM chapters using AI"""
    
    def __init__(self):
        self.client = OpenAI(api_key=OPENAI_API_KEY)
        self.model = "gpt-4o-2024-08-06"
    
    def classify_chapters(self, medical_text: str) -> ChapterClassification:
        """
        Classify medical text into most likely ICD-10-CM chapters
        
        Args:
            medical_text: The medical documentation to classify
            
        Returns:
            ChapterClassification: Structured response with chapter predictions
        """
        # Format chapters list for prompt
        chapters_formatted = "\n".join([f"- {chapter}" for chapter in ICD_CHAPTERS])
        
        # Create the prompt with medical text
        prompt = CHAPTER_CLASSIFICATION_PROMPT.format(
            chapters_list=chapters_formatted,
            medical_text=medical_text
        )
        
        # Call OpenAI with SUPER STRICT parameters for maximum accuracy
        completion = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "🚨 CRITICAL MEDICAL CODING TASK 🚨 You are an expert medical coder. Accuracy is LIFE-CRITICAL. Never guess or make assumptions. Only use the EXACT chapter names provided."},
                {"role": "user", "content": prompt}
            ],
            # SUPER STRICT PARAMETERS FOR MAXIMUM ACCURACY
            temperature=0.1,           # Zero creativity - pure logic only
            top_p=0.1,                # Extremely focused token selection
            frequency_penalty=0.0,    # No penalty for repetition of exact names
            presence_penalty=0.0,     # No penalty for using required format
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "chapter_classification",
                    "strict": True,
                    "schema": ChapterClassification.model_json_schema()
                }
            }
        )
        
        import json
        from pydantic import ValidationError
        
        try:
            result_json = json.loads(completion.choices[0].message.content)
            return ChapterClassification(**result_json)
        except (json.JSONDecodeError, ValidationError) as e:
            raise ValueError(f"Failed to parse OpenAI response: {e}")
    
    def get_high_probability_chapters(self, classification: ChapterClassification, 
                                    threshold: float = 0.5, max_chapters: int = 2) -> list:
        """
        Get focused chapter selection: 1 main chapter + 1 optional (if >50%)
        
        Args:
            classification: The chapter classification result
            threshold: Minimum probability threshold (default 0.5)
            max_chapters: Maximum number of chapters to return (default 2)
            
        Returns:
            list: 1 main chapter + 1 optional chapter (if confidence >50%), focused approach
        """
        # Sort predictions by probability (highest first)
        sorted_predictions = sorted(
            classification.predictions, 
            key=lambda x: x.probability, 
            reverse=True
        )
        
        selected_chapters = []
        
        # Always take the highest probability chapter (main focus)
        if sorted_predictions:
            main_chapter = sorted_predictions[0]
            selected_chapters.append(main_chapter.chapter_name)
            
            # Add second chapter ONLY if it has >50% confidence (optional)
            if len(sorted_predictions) > 1:
                second_chapter = sorted_predictions[1]
                if second_chapter.probability > 0.5:
                    selected_chapters.append(second_chapter.chapter_name)
        
        return selected_chapters 