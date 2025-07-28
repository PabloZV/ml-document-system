"""
Simple configuration for document processing pipeline
"""

import os
from pathlib import Path

# Paths
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data" / "docs-sm"
OUTPUT_DIR = BASE_DIR / "output"

# Document types (from folder structure)
DOCUMENT_TYPES = [
    'advertisement', 'budget', 'email', 'file_folder', 'form',
    'handwritten', 'invoice', 'letter', 'memo', 'news_article',
    'presentation', 'questionnaire', 'resume', 'scientific_publication',
    'scientific_report', 'specification'
]

# Simple patterns for entity extraction
ENTITY_PATTERNS = {
    'email': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
    'phone': r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b',
    'date': r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}',
    'amount': r'\$\s*\d+\.?\d*',
}

# ChromaDB settings
CHROMA_DB_PATH = BASE_DIR / "chroma_db"
COLLECTION_NAME = "documents"
