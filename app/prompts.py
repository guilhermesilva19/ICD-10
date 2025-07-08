"""Prompt templates for AI medical coding"""


# ===== Clean Two-Step Process Prompts =====
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





# ===== Spreadsheet functionality prompts =====
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

You are a medical documentation expert. Analyze the medical title and document content to generate comprehensive metadata.

Title: {title}
Document Content: {content}

TASK: Generate the following metadata by analyzing BOTH the title and full document content:

1. GENDER APPLICABILITY:
   - "Male" - if condition primarily affects males
   - "Female" - if condition primarily affects females  
   - "Both" - if condition affects both genders equally

2. MEDICAL KEYWORDS:
   - Extract key medical terms from the content
   - Include relevant anatomical terms
   - Add symptoms, treatments, procedures
   - Include diagnostic terms and medical conditions
   - Include other relevant  medical keywords and synonyms
   - Add relevant medical specialties and care areas
   - Format as comma-separated list
   - Include synonyms and related terms
   - Focus on terms that would help in medical coding and search

GUIDELINES:
- Analyze the FULL document content, not just the title
- Be accurate about gender applicability based on content analysis
- Focus on clinically relevant keywords from the entire document
- Include both technical and common medical terms found in content and other relavant keywords too that might not be mentioned int he document
- Extract procedure names, medication categories, and treatment approaches
- Include anatomical terms and body systems mentioned
- You should provide at least 15-35 comprehensive keywords
- Prioritize terms that appear in or relate to the document content

Provide accurate and clinically appropriate metadata based on the complete document analysis.
"""