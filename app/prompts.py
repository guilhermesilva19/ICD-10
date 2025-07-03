"""Prompt templates for AI classification and validation"""

CHAPTER_CLASSIFICATION_PROMPT = """
⚠️ CRITICAL INSTRUCTION: You MUST return EXACT chapter names from the list below with NO modifications, additions, or variations whatsoever.

TASK: Analyze medical text and identify the most relevant ICD-10-CM chapters.

🚫 FORBIDDEN:
- Do NOT modify chapter names in any way
- Do NOT add "Chapter 1:", "Chapter 2:" etc.
- Do NOT change punctuation, spacing, or wording
- Do NOT abbreviate or expand names
- Do NOT add explanatory text to chapter names

✅ REQUIRED:
- Copy chapter names EXACTLY as shown in the list
- Use only names from the provided list
- Return probability between 0.0 and 1.0
- Provide brief reasoning for each match

📋 EXACT CHAPTER NAMES (copy these EXACTLY):
{chapters_list}

🎯 ANALYSIS CRITERIA:
- Primary diagnoses and conditions
- Symptoms and clinical findings  
- Anatomical systems involved
- Disease processes described

📊 OUTPUT REQUIREMENTS:
- Return top 5 most relevant chapters
- Order by probability (highest first)
- Only include chapters with probability > 0.3
- Use EXACT chapter names from the list above

Medical text to analyze:
{medical_text}

⚠️ REMEMBER: Copy chapter names EXACTLY as they appear in the list. Any modification will cause system failure.
"""

VALIDATION_PROMPT = """
You are an expert medical coder specializing in ICD-10-CM code validation. Your task is to evaluate how well specific ICD codes match the given medical documentation.

Original medical text:
{medical_text}

Please evaluate each of the following ICD codes for accuracy and appropriateness:

{candidate_codes}

For each code, provide:
1. The ICD-10-CM code
2. The official description
3. A confidence score (0.0 to 1.0) indicating how well it matches
4. Clear reasoning explaining your assessment

Consider:
- Specificity and accuracy of the code
- Completeness of documentation
- Clinical appropriateness
- Coding guidelines compliance

Only recommend codes with confidence score > 0.5.
Provide an overall recommendation about the best matching codes.
""" 