"""
Django views for document processing API endpoints
"""

import os
import logging
from typing import Dict, Any

from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser

from .pipeline import DocumentPipeline
from .config import DATA_PATH

logger = logging.getLogger(__name__)


@method_decorator(csrf_exempt, name='dispatch')
class DocumentUploadView(APIView):
    """
    API endpoint for uploading and processing single documents
    """
    parser_classes = (MultiPartParser, FormParser)
    
    def __init__(self):
        super().__init__()
        self.pipeline = DocumentPipeline()
    
    def post(self, request):
        """
        Process a uploaded document file
        
        Expected request:
        - file: uploaded document image
        
        Returns:
        - JSON response with document type, entities, and metadata
        """
        try:
            # Check if file was uploaded
            if 'file' not in request.FILES:
                return Response({
                    'error': 'No file uploaded',
                    'message': 'Please upload a document file'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            uploaded_file = request.FILES['file']
            
            # Validate file
            if not self._validate_file(uploaded_file):
                return Response({
                    'error': 'Invalid file',
                    'message': 'File must be a JPG/JPEG image and less than 10MB'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Save file temporarily
            temp_path = self._save_temp_file(uploaded_file)
            
            try:
                import time
                start_time = time.time()
                
                # Process the document using our enhanced pipeline
                doc_data = self.pipeline.process_single_document(temp_path)
                
                if not doc_data:
                    return Response({
                        'error': 'Processing failed',
                        'message': 'Could not extract meaningful text from the document'
                    }, status=status.HTTP_422_UNPROCESSABLE_ENTITY)
                
                processing_time = round(time.time() - start_time, 2)
                
                # Calculate confidence based on text quality and entity extraction
                confidence = self._calculate_confidence(doc_data)
                
                # Prepare structured JSON response as required by ML project
                response_data = {
                    'success': True,
                    'document_type': doc_data['category'],
                    'confidence': confidence,
                    'extracted_entities': {
                        'persons': doc_data['entities'].get('persons', []),
                        'organizations': doc_data['entities'].get('organizations', []),
                        'locations': doc_data['entities'].get('locations', []),
                        'dates': doc_data['entities'].get('dates', []),
                        'amounts': doc_data['entities'].get('amounts', []),
                        'emails': doc_data['entities'].get('emails', []),
                        'phones': doc_data['entities'].get('phones', []),
                        'addresses': doc_data['entities'].get('addresses', [])
                    },
                    'metadata': {
                        'filename': doc_data['filename'],
                        'word_count': doc_data['word_count'],
                        'processing_time_seconds': processing_time,
                        'timestamp': doc_data['timestamp'],
                        'ocr_method': 'tesseract',
                        'classification_method': 'rule_based',
                        'entity_extraction_method': 'bert_ner_llm'
                    },
                    'text_preview': doc_data['text'][:200] + "..." if len(doc_data['text']) > 200 else doc_data['text']
                }
                
                return Response(response_data, status=status.HTTP_200_OK)
                
            finally:
                # Clean up temp file
                if os.path.exists(temp_path):
                    os.remove(temp_path)
                    
        except Exception as e:
            logger.error(f"Error processing upload: {str(e)}")
            return Response({
                'error': 'Internal server error',
                'message': 'An error occurred while processing the document'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def _calculate_confidence(self, doc_data: dict) -> float:
        """Calculate confidence score based on document processing quality"""
        confidence = 0.5  # Base confidence
        
        # Add confidence based on text length
        text_length = len(doc_data.get('text', ''))
        if text_length > 100:
            confidence += 0.2
        if text_length > 500:
            confidence += 0.1
        
        # Add confidence based on entity extraction
        entities = doc_data.get('entities', {})
        total_entities = sum(len(entities.get(key, [])) for key in entities)
        if total_entities > 0:
            confidence += 0.1
        if total_entities > 3:
            confidence += 0.1
        
        # Add confidence based on document type classification
        if doc_data.get('category', 'unknown') != 'unknown':
            confidence += 0.1
        
        return min(confidence, 0.95)  # Cap at 95%
    
    def _validate_file(self, uploaded_file) -> bool:
        """Validate uploaded file"""
        # Check file size (10MB limit)
        if uploaded_file.size > 10 * 1024 * 1024:
            return False
        
        # Check file extension - only JPG/JPEG supported and tested
        allowed_extensions = ['.jpg', '.jpeg']
        file_ext = os.path.splitext(uploaded_file.name)[1].lower()
        if file_ext not in allowed_extensions:
            return False
        
        return True
    
    def _save_temp_file(self, uploaded_file) -> str:
        """Save uploaded file temporarily"""
        import tempfile
        
        # Create temp file with original extension
        file_ext = os.path.splitext(uploaded_file.name)[1]
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=file_ext)
        
        for chunk in uploaded_file.chunks():
            temp_file.write(chunk)
        
        temp_file.close()
        return temp_file.name


@method_decorator(csrf_exempt, name='dispatch')
class DocumentSearchView(APIView):
    """
    API endpoint for searching documents using semantic similarity
    """
    
    def __init__(self):
        super().__init__()
        self.pipeline = DocumentPipeline()
    
    def get(self, request):
        """
        Search documents in the vector database
        
        Query parameters:
        - q: search query string
        - limit: number of results (default: 5)
        
        Returns:
        - JSON response with search results
        """
        try:
            query = request.GET.get('q', '')
            limit = int(request.GET.get('limit', 5))
            
            if not query:
                return Response({
                    'error': 'Missing query',
                    'message': 'Please provide a search query using the "q" parameter'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Perform search
            results = self.pipeline.search(query, n_results=limit)
            
            return Response({
                'query': query,
                'results': results,
                'count': len(results)
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Error in search: {str(e)}")
            return Response({
                'error': 'Search failed',
                'message': 'An error occurred while searching documents'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@method_decorator(csrf_exempt, name='dispatch')
class StatsView(APIView):
    """
    API endpoint for getting database statistics
    """
    
    def get(self, request):
        """
        Get statistics about stored documents
        
        Returns:
        - JSON response with document statistics
        """
        try:
            # Initialize pipeline only when needed to avoid startup errors
            pipeline = DocumentPipeline()
            stats = pipeline.get_stats()
            return Response(stats, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Error getting stats: {str(e)}")
            return Response({
                'total_documents': 0,
                'categories': {},
                'status': 'Database temporarily offline'
            }, status=status.HTTP_200_OK)  # Return 200 to avoid breaking frontend


def home_view(request):
    """Simple HTML interface for the document processing system"""
    from django.shortcuts import render
    return render(request, 'index.html')
