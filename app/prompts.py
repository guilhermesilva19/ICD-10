"""Medical coding prompt templates - all prompts consolidated."""

# Core code selection prompt
CODE_SELECTION_PROMPT = """
MEDICAL CODE SELECTION - ROOT FAMILY FOCUS REQUIRED

Medical Documentation: {medical_text}

Available Candidate Codes:
{candidate_codes}

CRITICAL SELECTION REQUIREMENTS:
1. SELECT CODES FROM MAXIMUM 2 ROOT FAMILIES ONLY
2. Primary root family must contain 80%+ of selected codes
3. Secondary root family only if medically essential (maximum 20% of codes)
4. Focus on ONE primary medical condition/diagnosis family
5. Maximum 25 codes total to ensure precision over breadth

ROOT FAMILY ANALYSIS PROTOCOL:
- Identify the PRIMARY root family (first 3 characters) most relevant to documentation
- Select 10-12 codes from primary family showing condition variations/severity
- Add secondary family ONLY if clinically essential (maximum 3 codes)
- Avoid scattered selection across multiple unrelated families

HIERARCHY REQUIREMENTS:
- Select specific subcategory codes (with decimal points: X##.### format)
- DO NOT select broad root codes (3-character codes without decimals)
- Prioritize detailed diagnostic codes over general categories
- Focus on codes with strong textual evidence in documentation

MEDICAL CODING STANDARDS:
- Each selected code must have clear clinical relevance
- Prefer specific diagnostic codes over symptom codes
- Ensure codes represent primary condition and direct complications
- Maintain diagnostic coherence within selected families

OUTPUT FORMAT:
Return selected ICD-10-CM codes as JSON list focusing on 1-2 root families maximum.
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

