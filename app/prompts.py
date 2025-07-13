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

# Core metadata generation prompt (Step 1)
METADATA_GENERATION_PROMPT = """
You are a senior medical coding specialist with expertise in document classification and metadata extraction.

Title: {title}
Document Content: {content}

TASK: Extract core metadata from this medical document following these precise steps:

STEP 1 - GENDER CLASSIFICATION:
Determine gender applicability using STRICT medical criteria:
- "Male" - ONLY for conditions that EXCLUSIVELY affect males (prostate, testicular, male-specific procedures)
- "Female" - ONLY for conditions that EXCLUSIVELY affect females (pregnancy, menstruation, ovarian, cervical, female-specific breast conditions)
- "Both" - DEFAULT for all other conditions (arthritis, diabetes, heart disease, infections, general procedures, treatments)

NOTE:GENDER APPLICABILITY (STRICT CLASSIFICATION):
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

CRITICAL: When in doubt, ALWAYS select "Both". Most medical conditions affect both genders.

STEP 2 - CORE KEYWORDS:
Extract essential medical keywords focusing ONLY on:
- Primary medical condition or diagnosis
- Key anatomical structures involved
- Essential diagnostic terminology
- Critical clinical modifiers
- Specific patient population if explicitly mentioned (pediatric, geriatric)

EXCLUDE these generic terms that apply to many topics:
- General symptoms (pain, swelling, fatigue, fever)
- Common treatments (medication, surgery, therapy)
- Vague descriptors (chronic, acute, severe, mild)
- Generic body systems (cardiovascular, respiratory)
- Broad categories (disease, disorder, condition)

Format keywords as comma-separated lowercase terms. Keep focused and specific.
"""

# Enhanced terminology generation prompt (Step 2)
ENHANCED_TERMINOLOGY_PROMPT = """
You are a senior medical terminology specialist with expertise in search optimization and clinical vocabulary expansion.

Title: {title}
Core Keywords: {core_keywords}
Document Content: {content}

TASK: Expand the core keywords with comprehensive medical terminology following these steps:



STEP 1 - SYNONYMS:
Generate medical synonyms and alternative clinical names:
- Official medical terminology variants
- Alternative diagnostic terms
- Related condition names with same clinical meaning
- EXCLUDE terms already in core keywords

STEP 2 - ACRONYMS:
Identify relevant clinical abbreviations:
- Standard medical acronyms (ICD, CPT, ROM)
- Procedure abbreviations (I&D, CABG, TURP)
- Condition-specific shorthand
- Include variations with/without punctuation
- DONT INCLUDE any terms already listed in synonyms or core keywords

STEP 3 - MISSPELLINGS:
Anticipate common search errors:
- Phonetic spelling variants
- Common typing mistakes
- Alternative medical term spellings
- EXCLUDE any terms already listed in previous categories

STEP 4 - LAYMAN TERMS:
Include patient-friendly terminology:
- Common names patients use
- Non-medical descriptions
- Everyday language for conditions

STEP 5 - CLINICAL TERMS:
Add professional medical language:
- Formal diagnostic terminology
- Advanced clinical descriptors
- Specialized medical vocabulary

CRITICAL EXCLUSIONS - DO NOT INCLUDE:
- Generic symptoms that apply to many conditions
- Medication names or drug classes
- Vague treatment descriptions
- Common words that lack medical specificity
- Terms that would match hundreds of unrelated topics
- ANY term that appears in core keywords or other categories

Format each category as comma-separated lowercase terms.
Focus on search optimization while maintaining medical accuracy.
"""

