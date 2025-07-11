"""Configuration with environment validation."""

import os
from dotenv import load_dotenv

load_dotenv()

# API Keys with validation
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY") 
PINECONE_INDEX_NAME = os.getenv("PINECONE_INDEX_NAME")

# Validate required environment variables
required_vars = [OPENAI_API_KEY, PINECONE_API_KEY, PINECONE_INDEX_NAME]
if not all(required_vars):
    missing = [var for var in ["OPENAI_API_KEY", "PINECONE_API_KEY", "PINECONE_INDEX_NAME"] 
               if not os.getenv(var)]
    raise RuntimeError(f"Missing required environment variables: {missing}")

# ICD Configuration (hardcoded in medical_engine.py)
# Processing Configuration (hardcoded in respective classes) 