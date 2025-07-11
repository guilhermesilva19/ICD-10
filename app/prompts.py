"""Medical coding prompt templates - all prompts consolidated."""

# Core code selection prompt
CODE_SELECTION_PROMPT = """
You are an ICD-10-CM medical coding expert.

Medical Documentation (clinical topic): {medical_text}

Available Candidate Codes:
{candidate_codes}

Your task is to map the given clinical topic to all applicable ICD-10-CM codes for use in EHR retrieval of patient education documents. Follow the steps below precisely:
---
 STEP 1: Match the base code(s)
- Identify the most clinically relevant base ICD-10-CM code(s) (3-character category).
- Select only the base code(s) directly tied to the main diagnostic concept.
- If more than one base code applies, include them only if clinically necessary.
---
STEP 2: Select applicable subcodes
- Expand all subcategories (4-character and above) under each base code.
- Default: include all subcodes unless the topic is narrowly defined.
- If the topic specifies a subtype, include only that subcategory and its descendants.
  Examples:
  - Topic = “abdominal pain” → Include all subcodes under R10.
  - Topic = “diabetes with PAD” → Include only subcode E11.5 and its full codes.
---
 STEP 3: Include all full ICD-10-CM codes
- For each subcategory, list all 5–7 character codes under it in the hierarchy.
- Include all modifiers such as:
  - Encounter type (initial, subsequent, sequela)
  - Laterality
  - Severity or anatomical detail
- Do NOT truncate or filter. Include all full codes listed in the CDC Tabular List for each subcategory.
---
EXCLUSION RULES:
- Do not include root codes like E11 or R10 without extensions.
- Do not stop at the 4-character level — always return the most specific 5–7 character codes.
---
"""

# Metadata generation prompt
METADATA_GENERATION_PROMPT = """
MEDICAL DOCUMENT METADATA GENERATION

Title: {title}
Document Content: {content}

Task: Generate structured metadata by analyzing the title and full document content.

Required Metadata:

1. GENDER APPLICABILITY (STRICT CLASSIFICATION):
   - "Male" - ONLY if condition EXCLUSIVELY affects males and NEVER affects females
   - "Female" - ONLY if condition EXCLUSIVELY affects females and NEVER affects males  
   - "Both" - DEFAULT for all other conditions (affects both genders or gender-neutral)
   
   STRICT RULES:
   - Return "Male" ONLY for: prostate conditions, testicular conditions, male-specific procedures
   - Return "Female" ONLY for: pregnancy, menstruation, ovarian conditions, cervical conditions, breast conditions specific to females
   - Return "Both" for: arthritis, diabetes, heart disease, infections, most medical conditions, surgical procedures, general treatments
   - When in doubt, ALWAYS return "Both"
   - Do NOT assume gender bias - most medical conditions affect both genders
   - Analyze the FULL document content to determine if condition is truly gender-exclusive

2. MEDICAL KEYWORDS (Structured Format):
   Extract keywords in this specific structure:
   
   A. RELEVANT MEDICAL TERMS:
   - Extract relevant medical keywords from the document content
   - Focus on primary conditions, treatments, procedures mentioned
   - Include anatomical terms and body systems referenced
   - Prioritize document-specific medical terminology
   
   B. ACRONYMS (Maximum 10):
   - Include medical acronyms found or implied in content
   - Examples: MI, COPD, GAD, ICD, MRI, etc.
   - Only include if relevant to document content
   
   C. SYNONYMS/LAYMAN TERMS (Maximum 10):
   - Include common patient language terms
   - Add synonyms for medical conditions mentioned
   - Include alternative terminology for procedures/treatments
   - Focus on terms patients would use

Guidelines:
- Analyze the FULL document content, not just the title
- Extract only terms directly relevant to the document
- !!!Avoid generic medical terms like "health", "patient", "medical"
- Format as single comma-separated list combining all categories
- Prioritize quality over quantity - be selective
- Focus on terms specific to the document's medical topic

Provide accurate and clinically appropriate metadata based on complete document analysis.
"""

