"""
Example usage of the simple document pipeline
"""

from main import DocumentPipeline

def demo():
    print("Document Pipeline Demo")
    
    # Initialize
    pipeline = DocumentPipeline()
    
    # Process documents (small batch for demo)
    print("\n1️⃣ Processing documents...")
    results = pipeline.process_documents(limit=10)
    
    # Show some results
    print(f"\nProcessed {len(results)} documents")
    for doc in results[:3]:
        print(f"  • {doc['filename']} ({doc['category']}) - {doc['word_count']} words")
        if doc['entities']:
            print(f"    Entities: {list(doc['entities'].keys())}")
    
    # Search demo
    print("\n2. Search examples:")
    queries = ["invoice", "email address", "payment"]
    
    for query in queries:
        print(f"\nSearch: '{query}'")
        results = pipeline.search(query, n_results=3)
        for result in results:
            print(f"  • {result['filename']} - {result['similarity']:.3f}")
    
    print("\nDemo complete!")

if __name__ == "__main__":
    demo()
