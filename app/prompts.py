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
You are a medical search optimization and metadata generation expert.
Your task is to analyze the document title and content to generate relevant keywords for indexing, search, and metadata tagging.
   
Title: {title}
Document Content: {content}

Task: Generate structured metadata by analyzing the title and document content.

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

2. MEDICAL KEYWORDS:
 
   INCLUDE:
   1. Subject Terms:
      - Core medical condition or topic
      - Synonyms or alternate clinical names
   2. Topic-Specific Words:
      - Anatomy involved (e.g., femur, tibia, fibula for leg fracture)
      - Diagnostic terminology (not general symptoms)
      - Modifiers (e.g., open fracture, closed fracture, displaced, left leg, right leg)
   3. Clinical Terms:
      - Proper medical terminology for diagnosis or charting
   4. Layman Terms:
      - Patient-friendly or common names for the condition
   5. Abbreviations and Acronyms:
      - Common clinical short forms (e.g., I&D, SOB, TIA)
      - Include variations with or without punctuation
   6. Shorthand or Slang:
      - Informal terms used in clinical settings or documentation
   7. Common Misspellings or Variants:
      - Words patients may type in error or phonetically
   8. Related Procedures:
      - Only if included in the title or content
   9. Hallmark Symptoms:
      - Only if defining to the condition (e.g., "RLQ pain" for appendicitis)
   10. Patient Population Tags:
       - Only if present in the title or content
       - Examples: adult, pediatric, child, kid, teen, adolescent, baby, infant, newborn, toddler, pregnancy, pregnant, senior adult, geriatric, older adult

   DO NOT INCLUDE:
   - Medication names (e.g., NSAIDs, acetaminophen)
   - Generic symptoms (e.g., fever, fatigue)
   - Treatment types not specific to the diagnosis
   - Vague terms or unrelated words

   Format as single, comma-separated list of keywords in lowercase.
   Remove exact duplicates. Include common spelling variants and search-friendly alternatives.

Provide accurate and clinically appropriate metadata based on complete document analysis.
"""

