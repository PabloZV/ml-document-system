"""
Simple Document Processing Pipeline - Main Script
"""

import json
import pandas as pd
from datetime import datetime
from pathlib import Path
from tqdm import tqdm
import chromadb
from sentence_transformers import SentenceTransformer

from config import *
from utils import *


class DocumentPipeline:
    """Simple document processing pipeline"""
    
    def __init__(self):
        # Initialize ChromaDB
        self.client = chromadb.PersistentClient(path=str(CHROMA_DB_PATH))
        self.collection = self._get_or_create_collection()
        
        # Initialize embedding model
        self.embedder = SentenceTransformer('all-MiniLM-L6-v2')
        
        print("Pipeline initialized")
    
    def _get_or_create_collection(self):
        """Get or create ChromaDB collection"""
        try:
            return self.client.get_collection(COLLECTION_NAME)
        except:
            return self.client.create_collection(COLLECTION_NAME)
    
    def process_single_document(self, file_info):
        """Process a single document"""
        try:
            # Extract text using OCR
            text = extract_text_from_image(file_info['path'])
            if not text:
                return None
            
            # Clean text
            cleaned_text = clean_text(text)
            
            # Extract entities
            entities = extract_entities(text)
            
            # Create document data
            doc_data = {
                'id': f"{file_info['category']}_{file_info['filename']}",
                'filename': file_info['filename'],
                'category': file_info['category'],
                'text': cleaned_text,
                'entities': entities,
                'word_count': len(cleaned_text.split()),
                'timestamp': datetime.now().isoformat()
            }
            
            return doc_data
            
        except Exception as e:
            print(f"Error processing {file_info['filename']}: {e}")
            return None
    
    def process_documents(self, limit=50):
        """Process multiple documents"""
        print(f"Processing up to {limit} documents...")
        
        # Get document files
        files = get_document_files(DATA_DIR, limit)
        print(f"Found {len(files)} files")
        
        # Process documents
        processed_docs = []
        for file_info in tqdm(files, desc="Processing"):
            doc_data = self.process_single_document(file_info)
            if doc_data:
                processed_docs.append(doc_data)
        
        print(f"Successfully processed {len(processed_docs)} documents")
        
        # Only store if we have documents
        if processed_docs:
            # Store in vector database
            self._store_documents(processed_docs)
            
            # Save results
            self._save_results(processed_docs)
        else:
            print("⚠️ No documents were successfully processed")
            print("   Make sure Tesseract OCR is installed and in your PATH")
            return []
        
        return processed_docs
    
    def _store_documents(self, documents):
        """Store documents in ChromaDB"""
        if not documents:
            print("⚠️ No documents to store")
            return
            
        print("💾 Storing in vector database...")
        
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
        
        print(f"Stored {len(documents)} documents")
    
    def _save_results(self, documents):
        """Save results to files"""
        OUTPUT_DIR.mkdir(exist_ok=True)
        
        # Save as JSON
        with open(OUTPUT_DIR / "results.json", 'w') as f:
            json.dump(documents, f, indent=2)
        
        # Save as CSV
        df_data = []
        for doc in documents:
            df_data.append({
                'filename': doc['filename'],
                'category': doc['category'],
                'word_count': doc['word_count'],
                'entities_count': len(doc['entities']),
                'has_email': 'email' in doc['entities'],
                'has_phone': 'phone' in doc['entities'],
                'has_date': 'date' in doc['entities'],
                'has_amount': 'amount' in doc['entities']
            })
        
        df = pd.DataFrame(df_data)
        df.to_csv(OUTPUT_DIR / "summary.csv", index=False)
        
        print(f"Results saved to {OUTPUT_DIR}")
    
    def search(self, query, n_results=5):
        """Search documents"""
        query_embedding = self.embedder.encode([query])
        
        results = self.collection.query(
            query_embeddings=query_embedding.tolist(),
            n_results=n_results
        )
        
        search_results = []
        for i in range(len(results['ids'][0])):
            search_results.append({
                'id': results['ids'][0][i],
                'text': results['documents'][0][i][:200] + "...",
                'category': results['metadatas'][0][i]['category'],
                'filename': results['metadatas'][0][i]['filename'],
                'similarity': 1 - results['distances'][0][i]
            })
        
        return search_results
    
    def get_stats(self):
        """Get simple statistics"""
        count = self.collection.count()
        return {'total_documents': count}


def main():
    """Main execution"""
    print("Simple Document Processing Pipeline")
    print("=" * 40)
    
    # Initialize pipeline
    pipeline = DocumentPipeline()
    
    # Process documents
    results = pipeline.process_documents(limit=20)  # Start small
    
    # Show statistics
    print("\nResults:")
    categories = {}
    for doc in results:
        cat = doc['category']
        categories[cat] = categories.get(cat, 0) + 1
    
    for category, count in categories.items():
        print(f"  {category}: {count} documents")
    
    # Demo search
    print("\nSearch Demo:")
    search_results = pipeline.search("invoice payment")
    for i, result in enumerate(search_results[:3]):
        print(f"  {i+1}. {result['filename']} ({result['category']}) - {result['similarity']:.3f}")
    
    print("\nPipeline completed!")
    print(f"Check {OUTPUT_DIR} for detailed results")


if __name__ == "__main__":
    main()
