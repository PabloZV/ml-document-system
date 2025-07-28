"""
Core document processing pipeline integrated with Django
Migrated from standalone main.py to Django app structure
"""

import os
import json
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional

import chromadb
import pandas as pd
from sentence_transformers import SentenceTransformer
from transformers import pipeline, AutoTokenizer, AutoModelForTokenClassification
import torch
from tqdm import tqdm

from .utils import extract_text_from_image, clean_text, extract_entities, get_document_files
from .config import ENTITY_PATTERNS, DOCUMENT_CATEGORIES, CHROMA_DB_PATH, OUTPUT_PATH

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DocumentPipeline:
    """Main document processing pipeline"""
    
    def __init__(self):
        """Initialize the pipeline with all required components"""
        # Initialize ChromaDB
        self.client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
        self.collection = self.client.get_or_create_collection("documents")
        
        # Initialize sentence transformer for embeddings
        self.embedder = SentenceTransformer('all-MiniLM-L6-v2')
        
        # Initialize NER pipeline for entity extraction
        try:
            self.ner_pipeline = pipeline(
                "ner", 
                model="dbmdz/bert-large-cased-finetuned-conll03-english",
                aggregation_strategy="simple",
                device=0 if torch.cuda.is_available() else -1
            )
            logger.info("NER pipeline initialized")
        except Exception as e:
            logger.warning(f"Failed to initialize NER pipeline: {e}")
            self.ner_pipeline = None
        
        logger.info("Pipeline initialized")
    
    
    def process_single_document(self, file_path: str) -> Optional[Dict[str, Any]]:
        """Process a single document and return structured data"""
        try:
            # Extract text using OCR
            text = extract_text_from_image(file_path)

            if not text or len(text.strip()) < 10:
                return None

            # Clean and process text
            cleaned_text = clean_text(text)

            # Determine document category from file path or use classification
            category = self._classify_document(file_path, cleaned_text)

            # Extract entities using LLM-based NER
            entities = self._extract_entities_with_llm(cleaned_text, category)

            # Create document data structure
            doc_data = {
                'id': f"{category}_{os.path.basename(file_path)}",
                'filename': os.path.basename(file_path),
                'file_path': file_path,
                'category': category,
                'text': cleaned_text,
                'entities': entities,
                'word_count': len(cleaned_text.split()),
                'timestamp': datetime.now().isoformat()
            }

            # Store the document in ChromaDB
            self._store_documents([doc_data])

            return doc_data

        except Exception as e:
            logger.error(f"Error processing {file_path}: {str(e)}")
            return None
    
    def _classify_document(self, file_path: str, text: str) -> str:
        """
        Classify document type based on file path and content
        For now, uses folder structure. Can be enhanced with ML classification.
        """
        # Extract category from folder structure
        path_parts = file_path.split(os.sep)
        for part in path_parts:
            if part in DOCUMENT_CATEGORIES:
                return part
        
        # Fallback: simple text-based classification
        text_lower = text.lower()
        
        if any(word in text_lower for word in ['invoice', 'bill', 'payment', 'amount', '$']):
            return 'invoice'
        elif any(word in text_lower for word in ['form', 'application', 'request']):
            return 'form'
        elif any(word in text_lower for word in ['resume', 'cv', 'experience', 'education']):
            return 'resume'
        elif any(word in text_lower for word in ['letter', 'dear', 'sincerely']):
            return 'letter'
        elif any(word in text_lower for word in ['memo', 'memorandum', 'subject:']):
            return 'memo'
        else:
            return 'unknown'
    
    def _extract_entities_with_llm(self, text: str, document_type: str) -> Dict[str, List[str]]:
        """
        Extract entities using LLM-based NER pipeline
        Returns structured entities based on document type
        """
        entities = {
            'persons': [],
            'organizations': [],
            'locations': [],
            'dates': [],
            'amounts': [],
            'emails': [],
            'phones': [],
            'addresses': []
        }
        
        if not self.ner_pipeline or not text.strip():
            return entities
        
        try:
            # Use the NER pipeline to extract entities
            ner_results = self.ner_pipeline(text[:512])  # Limit text length for performance
            
            for entity in ner_results:
                entity_type = entity['entity_group'].upper()
                entity_text = entity['word'].strip()
                confidence = entity['score']
                
                # Only include high-confidence entities
                if confidence > 0.8:
                    if entity_type in ['PER', 'PERSON']:
                        entities['persons'].append(entity_text)
                    elif entity_type in ['ORG', 'ORGANIZATION']:
                        entities['organizations'].append(entity_text)
                    elif entity_type in ['LOC', 'LOCATION']:
                        entities['locations'].append(entity_text)
                    elif entity_type in ['MISC']:
                        # Additional processing for miscellaneous entities
                        if any(word in entity_text.lower() for word in ['@', 'email']):
                            entities['emails'].append(entity_text)
                        elif any(char.isdigit() for char in entity_text):
                            entities['dates'].append(entity_text)
            
            # Additional regex-based extraction for specific patterns
            import re
            
            # Extract email addresses
            email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
            emails = re.findall(email_pattern, text)
            entities['emails'].extend(emails)
            
            # Extract phone numbers
            phone_pattern = r'\b(?:\+?1[-.\s]?)?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})\b'
            phones = re.findall(phone_pattern, text)
            entities['phones'].extend(['-'.join(phone) for phone in phones])
            
            # Extract monetary amounts
            money_pattern = r'\$\s*\d+(?:,\d{3})*(?:\.\d{2})?'
            amounts = re.findall(money_pattern, text)
            entities['amounts'].extend(amounts)
            
            # Remove duplicates and clean up
            for key in entities:
                entities[key] = list(set(entities[key]))
                entities[key] = [item for item in entities[key] if len(item.strip()) > 1]
            
            logger.info(f"Extracted {sum(len(v) for v in entities.values())} entities using LLM")
            
        except Exception as e:
            logger.error(f"Error in LLM entity extraction: {e}")
            # Fallback to basic extraction
            from .utils import extract_entities, ENTITY_PATTERNS
            return extract_entities(text, ENTITY_PATTERNS)
        
        return entities
    
    def process_documents(self, data_path: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Process multiple documents from a directory"""
        logger.info(f"Processing up to {limit} documents...")
        
        # Get list of files
        files = get_document_files(data_path)[:limit]
        logger.info(f"Found {len(files)} files")
        
        processed_docs = []
        
        # Process each file
        for file_path in tqdm(files, desc="Processing"):
            doc_data = self.process_single_document(file_path)
            if doc_data:
                processed_docs.append(doc_data)
        
        logger.info(f"Successfully processed {len(processed_docs)} documents")
        
        # Only store if we have documents
        if processed_docs:
            self._store_documents(processed_docs)
            self._save_results(processed_docs)
        else:
            logger.warning("⚠️ No documents were successfully processed")
            return []
        
        return processed_docs
    
    def _store_documents(self, documents: List[Dict[str, Any]]):
        """Store documents in ChromaDB"""
        if not documents:
            logger.warning("⚠️ No documents to store")
            return
            
        logger.info("💾 Storing in vector database...")
        
        ids = []
        texts = []
        metadatas = []
        
        for doc in documents:
            ids.append(doc['id'])
            texts.append(doc['text'])
            metadatas.append({
                'category': doc['category'],
                'filename': doc['filename'],
                'word_count': doc['word_count'],
                'entities': json.dumps(doc['entities'])
            })
        
        # Generate embeddings and store
        embeddings = self.embedder.encode(texts)
        
        self.collection.add(
            ids=ids,
            documents=texts,
            embeddings=embeddings.tolist(),
            metadatas=metadatas
        )
        
        logger.info(f"Stored {len(documents)} documents")
    
    def _save_results(self, documents: List[Dict[str, Any]]):
        """Save results to JSON and CSV files"""
        os.makedirs(OUTPUT_PATH, exist_ok=True)
        
        # Save detailed results as JSON
        json_path = os.path.join(OUTPUT_PATH, 'results.json')
        with open(json_path, 'w') as f:
            json.dump(documents, f, indent=2)
        
        # Create summary CSV
        summary_data = []
        for doc in documents:
            summary_data.append({
                'filename': doc['filename'],
                'category': doc['category'],
                'word_count': doc['word_count'],
                'entity_count': len(doc['entities']),
                'timestamp': doc['timestamp']
            })
        
        df = pd.DataFrame(summary_data)
        csv_path = os.path.join(OUTPUT_PATH, 'summary.csv')
        df.to_csv(csv_path, index=False)
        
        logger.info(f"Results saved to {OUTPUT_PATH}")
    
    def search(self, query: str, n_results: int = 5) -> List[Dict[str, Any]]:
        """Search documents using semantic similarity"""
        try:
            results = self.collection.query(
                query_texts=[query],
                n_results=n_results
            )
            
            search_results = []
            if results['documents'] and results['documents'][0]:
                for i, doc in enumerate(results['documents'][0]):
                    search_results.append({
                        'id': results['ids'][0][i],
                        'text': doc[:200] + "..." if len(doc) > 200 else doc,
                        'similarity': 1 - results['distances'][0][i],  # Convert distance to similarity
                        'metadata': results['metadatas'][0][i]
                    })
            
            return search_results
            
        except Exception as e:
            logger.error(f"Search error: {str(e)}")
            return []
    
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about stored documents"""
        try:
            count = self.collection.count()
            
            # Get sample of documents to analyze categories
            if count > 0:
                sample_results = self.collection.query(
                    query_texts=["sample"],
                    n_results=min(count, 100)
                )
                
                categories = {}
                if sample_results['metadatas'] and sample_results['metadatas'][0]:
                    for metadata in sample_results['metadatas'][0]:
                        category = metadata.get('category', 'unknown')
                        categories[category] = categories.get(category, 0) + 1
                
                return {
                    'total_documents': count,
                    'categories': categories
                }
            else:
                return {'total_documents': 0, 'categories': {}}
                
        except Exception as e:
            logger.error(f"Stats error: {str(e)}")
            return {'total_documents': 0, 'categories': {}, 'error': str(e)}
