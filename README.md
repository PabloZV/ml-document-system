# Document Processing System - ML Project

A Django-based document classification and entity extraction system using OCR, vector databases, and LLM models.

## Quick Setup

**Docker**
```bash
docker-compose up --build -d
```

- **Web Interface**: http://localhost:8000

## Dataset Setup

**Required**: Download the document dataset to test the system:

1. **Download**: https://drive.google.com/file/d/1-XkurZxd72b1nN8W-VeCO3vraai6cTIF/view
2. **Extract** the contents to `data/docs-sm/` directory
3. **Verify** structure: `data/docs-sm/advertisement/`, `data/docs-sm/invoice/`, etc.

The dataset contains categorized document images (JPG) for testing OCR, classification, and entity extraction.

**Test the 3 ML Project Requirements:**

### - For **Document Processing Pipeline** and **Django Management Command** use the process_documents command:

**Command Arguments Reference:**

| Argument | Description | Example | Default |
|----------|-------------|---------|---------|
| `--path` | Root directory containing document categories | `--path=data/docs-sm` | Required |
| `--category` | Process only specific document category | `--category=advertisement` | All categories |
| `--limit` | Maximum number of documents to process | `--limit=5` | No limit |
| `--verbosity` | Logging detail level (0=minimal, 2=detailed) | `--verbosity=2` | 1 |

**Example combinations:**
```bash
# Process 3 invoices with detailed logging
docker exec -it document-processor python manage.py process_documents --path=data/docs-sm --category=invoice --limit=3 --verbosity=2

# Process 20 documents from all categories
docker exec -it document-processor python manage.py process_documents --path=data/docs-sm --limit=20

# Process ALL advertisement documents (no limit)
docker exec -it document-processor python manage.py process_documents --path=data/docs-sm --category=advertisement
```

### - For the **Django API View** Upload and process document via API, either using the UI at http://localhost:8000 or by querying the following endpoint:

```bash
curl -X POST http://localhost:8000/api/process/ -F "file=@data/docs-sm/advertisement/0000126151.jpg"
```

---

**Manual Setup (Alternative)**
<details>
<summary>Click to expand manual installation</summary>

**Requirements:**
- Python 3.9+
- Tesseract OCR

```bash
# Install Tesseract:
sudo apt-get install tesseract-ocr

# Setup Python environment:
conda create -n doc-pipeline python=3.9 -y
conda activate doc-pipeline
pip install -r requirements.txt

# Run Django migrations and start server:
python manage.py migrate
python manage.py runserver
```
</details>

## Project Structure

```
├── document_processor/     # Django project settings
│   ├── settings.py        # Django configuration
│   ├── urls.py           # Main URL routing + web interface
│   └── wsgi.py           # WSGI application
├── processor/             # Main Django app
│   ├── management/       # Django management commands
│   │   └── commands/     
│   │       └── process_documents.py  # Batch processing command
│   ├── migrations/       # Database migrations
│   ├── models.py         # Data models
│   ├── pipeline.py       # ML processing pipeline (300+ lines)
│   ├── views.py          # REST API endpoints (400+ lines)
│   ├── urls.py           # API URL routing
│   └── config.py         # Configuration
├── manage.py             # Django management script
├── docker-compose.yml    # Docker orchestration
├── Dockerfile           # Docker container setup
├── requirements.txt     # Python dependencies
├── chroma_db/           # ChromaDB vector database
└── data/docs-sm/        # Document dataset
```

## What it does

1. **OCR Processing**: Extracts text from documents using Tesseract
2. **Document Classification**: ML-based document type identification using vector similarity
3. **LLM Entity Extraction**: Uses BERT/transformers for advanced entity extraction
4. **Vector Database**: Stores documents in ChromaDB for semantic search
5. **REST API**: Django REST Framework endpoints for processing and search
6. **Web Interface**: Professional HTML/CSS/JS interface for testing

## ML Project Requirements Implementation

### **1. Document Processing Pipeline**
**Implementation**: `processor/pipeline.py` - Complete ML pipeline with OCR, classification, and entity extraction

**Features Implemented:**
- **OCR Text Extraction**: Tesseract OCR service
- **Text Processing & Cleaning**: Regex normalization and preprocessing
- **Document Type Identification**: Vector similarity using sentence-transformers
- **LLM Entity Extraction**: BERT/transformers for advanced NER
- **ChromaDB Storage**: Vector embeddings with metadata

**Example Pipeline Flow:**
```python
# processor/pipeline.py
def process_single_document(self, file_path: str) -> Dict[str, Any]:
    # 1. OCR Text Extraction
    text = self._extract_text_with_ocr(file_path)
    
    # 2. Text Processing & Cleaning
    cleaned_text = self._clean_text(text)
    
    # 3. Document Type Identification
    doc_type, confidence = self._classify_document(cleaned_text)
    
    # 4. LLM Entity Extraction
    entities = self._extract_entities_with_llm(cleaned_text, doc_type)
    
    # 5. ChromaDB Storage
    self._store_in_chromadb(file_path, text, doc_type, entities)
    
    return {
        "document_type": doc_type,
        "confidence": confidence,
        "entities": entities,
        "text": text
    }
```

### **2. Django Management Command**
**Implementation**: `processor/management/commands/process_documents.py` - Batch processing with error handling

**Features Implemented:**
- **Dataset Input**: `--path` parameter for dataset directory
- **Pipeline Processing**: Processes each document through complete ML pipeline
- **Document Type Identification**: Automatic classification per document
- **ChromaDB Upserts**: Stores documents with vector embeddings
- **Error Handling & Logging**: Graceful error recovery with detailed logs

**Example Command Usage:**
```bash
# Basic batch processing
python manage.py process_documents --path=data/docs-sm --limit=50

# Category-specific processing with logging
python manage.py process_documents \
  --path=data/docs-sm \
  --category=advertisement \
  --limit=10 \
  --verbosity=2

# Example output with error handling:
# [2025-07-27 10:30:00] INFO: Starting document processing...
# [2025-07-27 10:30:01] INFO: Found 13 categories in dataset
# [2025-07-27 10:30:02] SUCCESS: 0000126151.jpg → advertisement (0.92)
# [2025-07-27 10:30:03] ERROR: Failed to process corrupted_file.jpg - Skipping
# [2025-07-27 10:30:04] SUCCESS: 0000126164.jpg → advertisement (0.88)
# [2025-07-27 10:30:10] SUMMARY: 9/10 processed successfully, 1 error
```

### **3. Django API View**
**Implementation**: `processor/views.py` - REST API with file upload and LLM processing

**Features Implemented:**
- **File Upload Acceptance**: MultiPartParser for document uploads
- **OCR Text Extraction**: Tesseract integration in API endpoint
- **Vector Database Queries**: ChromaDB similarity search for document type
- **LLM Entity Extraction**: BERT/transformers model integration
- **Structured JSON Response**: Complete metadata with confidence scores

**Example API Implementation:**
```python
# processor/views.py - DocumentUploadView
class DocumentUploadView(APIView):
    def post(self, request):
        # 1. Accept file upload
        uploaded_file = request.FILES['file']
        
        # 2. Extract text using OCR
        text = self.pipeline.extract_text_with_ocr(uploaded_file)
        
        # 3. Query vector database for document type
        doc_type, confidence = self.pipeline.classify_document(text)
        
        # 4. Call LLM for entity extraction
        entities = self.pipeline.extract_entities_with_llm(text, doc_type)
        
        # 5. Return structured JSON response
        return Response({
            "success": True,
            "document_type": doc_type,
            "confidence": confidence,
            "entities": entities,
            "extracted_text": text[:200] + "...",
            "word_count": len(text.split()),
            "processing_time": processing_time
        })
```

## Usage Examples

### **REST API Endpoints**

**Upload & Process Document:**
```bash
curl -X POST http://localhost:8000/api/process/ \
  -F "file=@data/docs-sm/advertisement/0000126151.jpg"

# Example response:
{
  "success": true,
  "document_type": "advertisement",
  "confidence": 0.92,
  "entities": {
    "persons": ["John Smith", "Dr. Sarah Johnson"],
    "organizations": ["TechCorp", "Solutions Inc"],
    "locations": ["New York", "California", "San Francisco"],
    "dates": ["2025-01-15", "March 2025"],
    "amounts": ["$1,500.00", "$50,000"],
    "emails": ["contact@techcorp.com", "info@solutions.com"],
    "phones": ["555-123-4567", "800-555-0123"],
    "addresses": ["123 Main St, New York, NY 10001"]
  },
  "extracted_text": "TechCorp Premium Software Suite...",
  "word_count": 156,
  "processing_time": 2.3,
  "filename": "0000126151.jpg"
}
```

**Search Documents:**
```bash
curl "http://localhost:8000/api/search/?q=advertisement&limit=3"

# Example response:
{
  "query": "advertisement",
  "results": [
    {
      "document_id": "0000126151.jpg",
      "document_type": "advertisement",
      "confidence": 0.92,
      "entities": {"organizations": ["TechCorp"]},
      "similarity_score": 0.95
    }
  ],
  "count": 1
}
```

**Get System Stats:**
```bash
curl "http://localhost:8000/api/stats/"

# Example response:
{
  "total_documents": 247,
  "categories": {
    "advertisement": 75,
    "invoice": 42,
    "letter": 38,
    "form": 29,
    "email": 25,
    "resume": 18,
    "other": 20
  },
  "database_size": "15.2 MB",
  "last_updated": "2025-07-27T10:30:00Z"
}
```

### **Web Interface**
Visit http://localhost:8000 for the interactive web interface with:
- Document upload and processing
- Real-time ML results display  
- Semantic search functionality
- System statistics dashboard

**Example workflow:**
1. **Upload**: Click the upload area and select `data/docs-sm/advertisement/0000126151.jpg`
2. **Process**: Click "Process Document" 
3. **View Results**: See real-time processing status and JSON response
4. **Search**: Try searching for "software" or "technology" to find similar documents
5. **Statistics**: View dashboard showing 247 total documents across 7 categories

## ML Features

### **Supported Entity Types**
The system extracts **8 types of entities** from documents using a combination of BERT NER models and regex patterns:

| Entity Type | Description | Example | Detection Method |
|-------------|-------------|---------|------------------|
| **persons** | People names | "John Smith", "Dr. Jane Doe" | BERT NER (PER/PERSON) |
| **organizations** | Company/org names | "TechCorp", "Solutions Inc" | BERT NER (ORG/ORGANIZATION) |
| **locations** | Places, addresses | "New York", "California" | BERT NER (LOC/LOCATION) |
| **dates** | Date information | "2025-01-15", "January 2025" | BERT NER + regex patterns |
| **amounts** | Monetary values | "$1,500.00", "$50K" | Regex pattern: `\$\s*\d+(?:,\d{3})*(?:\.\d{2})?` |
| **emails** | Email addresses | "contact@company.com" | Regex pattern: `[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z\|a-z]{2,}` |
| **phones** | Phone numbers | "555-123-4567", "(555) 123-4567" | Regex pattern: `\+?1[-.\s]?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})` |
| **addresses** | Physical addresses | Street addresses, postal codes | BERT NER + pattern matching |

### **Document Classification**
- Vector similarity matching using sentence-transformers
- Confidence scoring for classification results
- Support for 13+ document types (advertisement, invoice, letter, etc.)

### **Entity Extraction**
- **LLM-based extraction** using BERT/transformers
- Advanced NER (Named Entity Recognition)
- Confidence scoring for extracted entities
- Context-aware entity identification

### **Vector Database**
- ChromaDB for semantic document storage
- Embedding-based similarity search
- Efficient document retrieval and ranking

## Technology Stack

- **Framework**: Django 4.2+ with Django REST Framework
- **OCR**: Tesseract OCR for text extraction
- **ML Models**: 
  - sentence-transformers for document embeddings
  - transformers/BERT for entity extraction
  - torch for ML processing
- **Vector DB**: ChromaDB for semantic search
- **Frontend**: HTML/CSS/JavaScript web interface
- **Deployment**: Docker with docker-compose

## Architecture Overview

**Pipeline Architecture:**
```
DocumentPipeline:
├── OCR Extraction (Tesseract)
├── Text Cleaning & Preprocessing
├── Document Classification (Vector Similarity)
├── LLM Entity Extraction (BERT/transformers)
├── Vector Embedding (sentence-transformers)
└── ChromaDB Storage
```

**Docker Setup:**
```yaml
services:
  document-processor:
    container_name: document-processor
    image: document-processor:latest
    build: .
    ports:
      - "8000:8000"
    volumes:
      - ./data:/app/data
      - ./chroma_db:/app/chroma_db
    command: python manage.py runserver 0.0.0.0:8000
```

**Quick Commands:**
```bash
# Start the system
docker-compose up --build

# Process documents  
python manage.py process_documents --path=data/docs-sm --category=advertisement --limit=5

# Test APIs
curl -X GET http://localhost:8000/api/stats/
curl -X GET "http://localhost:8000/api/search/?q=advertisement&limit=2"
curl -X POST http://localhost:8000/api/process/ -F "file=@document.jpg"
```