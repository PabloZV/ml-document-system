"""
Utility functions for document processing
Migrated from standalone utils.py
"""

import os
import re
import cv2
import pytesseract
from PIL import Image
import numpy as np
from typing import List, Dict, Any


def extract_text_from_image(image_path: str) -> str:
    """
    Extract text from an image using OCR
    """
    try:
        # Read image using OpenCV
        image = cv2.imread(image_path)
        if image is None:
            return ""
        
        # Convert to grayscale
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # Apply noise reduction and sharpening
        denoised = cv2.fastNlMeansDenoising(gray)
        
        # Use Tesseract for OCR
        text = pytesseract.image_to_string(denoised, config='--psm 6')
        
        return text.strip()
        
    except Exception as e:
        print(f"Error extracting text from {image_path}: {str(e)}")
        return ""


def clean_text(text: str) -> str:
    """
    Clean and normalize extracted text
    """
    if not text:
        return ""
    
    # Remove excessive whitespace
    text = re.sub(r'\s+', ' ', text)
    
    # Remove special characters but keep punctuation
    text = re.sub(r'[^\w\s.,!?;:()\-$@]', '', text)
    
    # Remove very short lines (likely OCR artifacts)
    lines = text.split('\n')
    lines = [line.strip() for line in lines if len(line.strip()) > 2]
    
    return ' '.join(lines).strip()


def extract_entities(text: str, patterns: Dict[str, List[str]]) -> Dict[str, List[str]]:
    """
    Extract entities from text using regex patterns
    """
    entities = {}
    
    for entity_type, pattern_list in patterns.items():
        matches = []
        for pattern in pattern_list:
            found = re.findall(pattern, text, re.IGNORECASE)
            matches.extend(found)
        
        if matches:
            # Remove duplicates while preserving order
            entities[entity_type] = list(dict.fromkeys(matches))
    
    return entities


def get_document_files(data_path: str, extensions: List[str] = None) -> List[str]:
    """
    Get list of document files from a directory
    """
    if extensions is None:
        # Only JPG/JPEG supported and tested with this dataset
        extensions = ['.jpg', '.jpeg']
    
    files = []
    
    for root, dirs, filenames in os.walk(data_path):
        for filename in filenames:
            if any(filename.lower().endswith(ext) for ext in extensions):
                files.append(os.path.join(root, filename))
    
    return sorted(files)


def validate_file(file_path: str, max_size: int = 10 * 1024 * 1024) -> bool:
    """
    Validate if file exists and is within size limits
    """
    if not os.path.exists(file_path):
        return False
    
    if os.path.getsize(file_path) > max_size:
        return False
    
    return True
