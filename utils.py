"""
Simple utility functions for document processing
"""

import re
import cv2
import numpy as np
import pytesseract
from PIL import Image
from pathlib import Path
from config import ENTITY_PATTERNS


def extract_text_from_image(image_path):
    """Extract text from image using OCR"""
    try:
        # Read and preprocess image
        image = cv2.imread(str(image_path))
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # Simple preprocessing
        gray = cv2.medianBlur(gray, 3)
        
        # Extract text
        text = pytesseract.image_to_string(gray)
        return text.strip()
    except Exception as e:
        print(f"Error processing {image_path}: {e}")
        return ""


def clean_text(text):
    """Basic text cleaning"""
    if not text:
        return ""
    
    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def extract_entities(text):
    """Extract entities using simple regex patterns"""
    entities = {}
    
    for entity_type, pattern in ENTITY_PATTERNS.items():
        matches = re.findall(pattern, text, re.IGNORECASE)
        if matches:
            entities[entity_type] = list(set(matches))  # Remove duplicates
    
    return entities


def get_document_files(data_dir, limit=None):
    """Get list of document files with their categories"""
    files = []
    
    for category_dir in Path(data_dir).iterdir():
        if not category_dir.is_dir():
            continue
            
        category = category_dir.name
        image_files = list(category_dir.glob("*.jpg")) + list(category_dir.glob("*.png"))
        
        for file_path in image_files:
            files.append({
                'path': file_path,
                'category': category,
                'filename': file_path.name
            })
            
            if limit and len(files) >= limit:
                return files
    
    return files
