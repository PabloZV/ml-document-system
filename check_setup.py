#!/usr/bin/env python3
"""
Setup verification script - checks if all dependencies are installed correctly
"""

def test_imports():
    print("Testing imports...")
    
    try:
        import cv2
        print("OpenCV - OK")
    except ImportError:
        print("OpenCV - MISSING - pip install opencv-python")
    
    try:
        import pytesseract
        print("PyTesseract - OK")
    except ImportError:
        print("PyTesseract - MISSING - pip install pytesseract")
    
    try:
        import chromadb
        print("ChromaDB - OK")
    except ImportError:
        print("ChromaDB - MISSING - pip install chromadb")
    
    try:
        from sentence_transformers import SentenceTransformer
        print("SentenceTransformers - OK")
    except ImportError:
        print("SentenceTransformers - MISSING - pip install sentence-transformers")
    
    try:
        import spacy
        nlp = spacy.load("en_core_web_sm")
        print("spaCy model - OK")
    except (ImportError, OSError):
        print("spaCy model - MISSING - python -m spacy download en_core_web_sm")

def test_tesseract():
    print("\nTesting Tesseract...")
    try:
        import pytesseract
        version = pytesseract.get_tesseract_version()
        print(f"Tesseract {version} - OK")
    except:
        print("Tesseract - ERROR - install tesseract-ocr")

def test_pipeline():
    print("\nTesting pipeline files...")
    import os
    
    files = ['main.py', 'config.py', 'utils.py', 'demo.py']
    for file in files:
        if os.path.exists(file):
            print(f"{file} - OK")
        else:
            print(f"{file} - MISSING")

if __name__ == "__main__":
    print("Setup Verification")
    print("=" * 30)
    
    test_imports()
    test_tesseract()
    test_pipeline()
    
    print("\nIf all tests pass, run: python main.py")
