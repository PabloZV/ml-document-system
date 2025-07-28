"""
Configuration constants for the document processor
"""

import os

# Document categories based on the dataset structure
DOCUMENT_CATEGORIES = [
    'advertisement',
    'budget',
    'email',
    'file_folder',
    'form',
    'handwritten',
    'invoice',
    'letter',
    'memo',
    'news_article',
    'presentation',
    'questionnaire',
    'resume',
    'scientific_publication',
    'scientific_report',
    'specification'
]

# Entity extraction patterns for different document types
ENTITY_PATTERNS = {
    'email': [
        r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    ],
    'phone': [
        r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b',
        r'\(\d{3}\)\s*\d{3}[-.]?\d{4}\b'
    ],
    'date': [
        r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b',
        r'\b\d{4}[-/]\d{1,2}[-/]\d{1,2}\b',
        r'\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},?\s+\d{4}\b'
    ],
    'amount': [
        r'\$\d{1,3}(?:,\d{3})*(?:\.\d{2})?',
        r'\b\d{1,3}(?:,\d{3})*(?:\.\d{2})?\s*(?:USD|dollars?)\b'
    ],
    'invoice_number': [
        r'(?:Invoice|INV)[\s#-]*(\d+)',
        r'(?:Bill|Receipt)[\s#-]*(\d+)'
    ],
    'ssn': [
        r'\b\d{3}-\d{2}-\d{4}\b'
    ]
}

# File paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_PATH = os.path.join(BASE_DIR, 'data', 'docs-sm')
OUTPUT_PATH = os.path.join(BASE_DIR, 'output')
CHROMA_DB_PATH = os.path.join(BASE_DIR, 'chroma_db')

# Processing settings
DEFAULT_LIMIT = 20
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
