"""Prompt templates for AI medical coding"""


# ===== NEW: Clean Two-Step Process Prompts =====
INITIAL_SELECTION_PROMPT = """
🩺 MEDICAL CODE SELECTION

You are a medical coding expert reviewing ICD-10-CM codes for clinical documentation.

CLINICAL DOCUMENTATION:
{medical_text}

CANDIDATE CODES:
{candidate_codes}

TASK: Select approximately 50 codes that could be medically relevant to this documentation.

SELECTION CRITERIA:
- Codes related to the medical condition described
- Relevant symptoms, anatomy, or related conditions
- Include potential differential diagnoses
- Focus on clinical relevance

REQUIREMENT: Return exactly the ICD codes - no descriptions, no reasoning, no confidence scores.
Target: Approximately 50 codes for detailed clinical review.
"""

CLINICAL_REFINEMENT_PROMPT = """
🩺 CLINICAL CODE REFINEMENT & ENHANCEMENT

You are a senior medical coding specialist performing clinical validation.

CLINICAL DOCUMENTATION:
{medical_text}

CODES FOR REVIEW:
{selected_codes}

TASK: Remove any irrelevant codes and enhance descriptions for the remaining clinically appropriate codes.

PROCESS:
1. Remove codes that are NOT clinically relevant to this documentation
2. For remaining relevant codes: enhance the original description for clinical clarity
3. Assign confidence scores based on clinical appropriateness

ENHANCEMENT REQUIREMENTS:
- Improve description clarity while maintaining medical accuracy
- Make descriptions more specific and clinically useful
- Ensure descriptions help healthcare providers understand the relevance

DELIVERABLE: Only clinically relevant codes with enhanced descriptions and confidence scores.
"""


# ===== KEEP: Legacy validation prompt for /analyze endpoint =====
LEGACY_VALIDATION_PROMPT = """
🚨🚨🚨 CRITICAL CODE VALIDATION - COMPREHENSIVE RELATED CODES 🚨🚨🚨

You are an expert medical coder specializing in ICD-10-CM code validation. Your task is to find STRONGLY RELATED ICD codes for the given medical documentation.

🎯 MISSION: Find approximately 30 STRONGLY RELATED codes with confidence scores proportional to their relatedness
🚫 NEVER GUESS OR ASSUME ANYTHING

Original medical text:
{medical_text}

Please evaluate each of the following ICD codes for RELATEDNESS and appropriateness:

{candidate_codes}

🔍 RELATEDNESS CRITERIA - BE COMPREHENSIVE BUT ACCURATE:

CONFIDENCE SCORING :
- 0.9-1.0: PERFECT MATCH - Exact condition described
- 0.8-0.9: VERY STRONG RELATION - Directly related condition/symptom
- 0.7-0.8: STRONG RELATION - Same anatomical system or related disorder
- 0.6-0.7: GOOD RELATION - Related condition family or differential diagnosis
- 0.5-0.6: MODERATE RELATION - Same chapter/category, related symptoms
- 0.4-0.5: WEAK RELATION - Tangentially related, same organ system
- 0.3-0.4: MINIMAL RELATION - Distant connection but still relevant
- 0.0-0.3: NOT RELATED - No meaningful clinical connection

🎯 TARGET OUTPUT: Return approximately 30 codes, including:
- Direct matches (high confidence 0.8-1.0)
- Related conditions (medium confidence 0.5-0.8) 
- Differential diagnoses (lower confidence 0.4-0.6)
- Same anatomical system codes (0.3-0.5)

For each code, provide:
1. The ICD-10-CM code
2. The official description  
3. A confidence score (0.0 to 1.0) - proportional to relatedness
4. Clear reasoning explaining the clinical relationship
5. Specific evidence or connection to the medical text

Consider ALL types of clinical relationships:
- Primary conditions and complications
- Related symptoms and manifestations
- Differential diagnoses to consider
- Same anatomical system disorders
- Associated conditions and comorbidities
- Preventive care related codes

📊 Order by confidence score (highest first)
🩺 Focus on clinical utility - codes that would be relevant for medical decision making
"""


# ===== KEEP: Spreadsheet functionality prompts =====
TITLE_ENRICHMENT_PROMPT = """
🎯 MEDICAL TITLE ENRICHMENT FOR VECTOR SEARCH

You are a medical terminology expert. Your task is to enrich a medical document title with additional relevant keywords to improve vector search accuracy.

CRITICAL REQUIREMENTS:
🚫 NEVER change the original meaning
🚫 NEVER add unrelated medical terms
✅ Only add synonyms, related terms, and medical variations
✅ Keep enrichment focused and relevant

Original title: {title}

TASK: Generate additional medical keywords that would help find relevant ICD-10-CM codes for this topic.

GUIDELINES:
- Add medical synonyms and alternative terms
- Include related anatomical terms if applicable
- Add common medical abbreviations if relevant
- Include related condition variations
- Focus on terms that would appear in ICD code descriptions

EXAMPLE:
Original: "Heart Attack"
Enriched: "myocardial infarction, MI, cardiac arrest, coronary thrombosis, acute coronary syndrome"

Provide your enriched keywords as a comma-separated list.
Keep the enrichment focused and medically accurate.
"""

METADATA_GENERATION_PROMPT = """
🩺 MEDICAL DOCUMENT METADATA GENERATION

You are a medical documentation expert. Analyze the medical title/content and generate metadata.

Title: {title}

TASK: Generate the following metadata:

1. GENDER APPLICABILITY:
   - "Male" - if condition primarily affects males
   - "Female" - if condition primarily affects females  
   - "Both" - if condition affects both genders equally

2. MEDICAL KEYWORDS:
   - Extract key medical terms from the title/content
   - Include relevant anatomical terms
   - Add common symptoms or treatment terms
   - Format as comma-separated list
   - Include synonyms and related terms

GUIDELINES:
- Be accurate about gender applicability
- Focus on clinically relevant keywords
- Include both technical and common medical terms
- Keep keywords focused and 
- include synonyms and related terms
- you should atleast provide 15 to 20 keywords

EXAMPLE:
Title: "Pregnancy Complications"
Gender: Female
Keywords: pregnancy, maternal health, prenatal care, obstetric complications, gestational disorders ....

Provide accurate and clinically appropriate metadata.
"""