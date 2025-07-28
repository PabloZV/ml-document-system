"""
Django management command to process documents from the dataset.
"""
import os
import logging
from pathlib import Path
from typing import List, Dict, Any

from django.core.management.base import BaseCommand, CommandError
from django.conf import settings

from processor.pipeline import DocumentPipeline


logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Process documents from the dataset directory'

    def add_arguments(self, parser):
        parser.add_argument(
            '--path',
            type=str,
            default='data/docs-sm',
            help='Path to the dataset directory (default: data/docs-sm)'
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=None,
            help='Maximum number of documents to process (default: all)'
        )
        parser.add_argument(
            '--category',
            type=str,
            default=None,
            help='Process only documents from this category (subfolder)'
        )
        parser.add_argument(
            '--skip-existing',
            action='store_true',
            help='Skip documents that are already in the database'
        )

    def handle(self, *args, **options):
        """Main command handler."""
        dataset_path = options['path']
        limit = options['limit']
        category = options['category']
        skip_existing = options['skip_existing']
        
        self.stdout.write(
            self.style.SUCCESS(f'Starting document processing from: {dataset_path}')
        )
        
        if not os.path.exists(dataset_path):
            raise CommandError(f'Dataset path does not exist: {dataset_path}')
        
        try:
            # Initialize the pipeline
            pipeline = DocumentPipeline()
            
            # Get list of documents to process
            documents = self._get_documents(dataset_path, category, limit)
            
            if not documents:
                self.stdout.write(
                    self.style.WARNING('No documents found to process')
                )
                return
            
            self.stdout.write(
                self.style.SUCCESS(f'Found {len(documents)} documents to process')
            )
            
            # Process documents
            processed_count = 0
            error_count = 0
            
            for doc_info in documents:
                try:
                    # Check if document already exists
                    if skip_existing and self._document_exists(pipeline, doc_info['path']):
                        self.stdout.write(f'Skipping existing: {doc_info["name"]}')
                        continue
                    
                    # Process the document
                    result = pipeline.process_single_document(doc_info['path'])
                    
                    if result is not None:
                        processed_count += 1
                        self.stdout.write(
                            self.style.SUCCESS(
                                f'✓ Processed: {doc_info["name"]} '
                                f'(Type: {result.get("category", "unknown")})'
                            )
                        )
                    else:
                        error_count += 1
                        self.stdout.write(
                            self.style.ERROR(
                                f'✗ Failed: {doc_info["name"]} - Processing failed'
                            )
                        )
                
                except Exception as e:
                    error_count += 1
                    logger.exception(f'Error processing {doc_info["path"]}')
                    self.stdout.write(
                        self.style.ERROR(f'✗ Error: {doc_info["name"]} - {str(e)}')
                    )
            
            # Print summary
            self.stdout.write('\n' + '='*50)
            self.stdout.write(
                self.style.SUCCESS(f'Processing complete!')
            )
            self.stdout.write(f'Total documents found: {len(documents)}')
            self.stdout.write(f'Successfully processed: {processed_count}')
            self.stdout.write(f'Errors: {error_count}')
            
            # Show database stats
            try:
                stats = pipeline.get_stats()
                self.stdout.write('\nDatabase Statistics:')
                self.stdout.write(f'Total documents in DB: {stats.get("total_documents", 0)}')
                self.stdout.write(f'Document types: {stats.get("document_types", {})}')
            except Exception as e:
                self.stdout.write(
                    self.style.WARNING(f'Could not retrieve stats: {str(e)}')
                )

        except Exception as e:
            logger.exception('Error in document processing command')
            raise CommandError(f'Command failed: {str(e)}')

    def _get_documents(self, dataset_path: str, category: str = None, limit: int = None) -> List[Dict[str, Any]]:
        """Get list of documents to process."""
        documents = []
        dataset_path = Path(dataset_path)
        
        # Supported image extensions
        image_extensions = {'.jpg', '.jpeg', '.png', '.tiff', '.tif', '.bmp'}
        
        if category:
            # Process only specific category
            category_path = dataset_path / category
            if not category_path.exists():
                self.stdout.write(
                    self.style.WARNING(f'Category path does not exist: {category_path}')
                )
                return documents
            
            for file_path in category_path.iterdir():
                if file_path.is_file() and file_path.suffix.lower() in image_extensions:
                    documents.append({
                        'path': str(file_path),
                        'name': file_path.name,
                        'category': category
                    })
        else:
            # Process all categories
            for category_dir in dataset_path.iterdir():
                if category_dir.is_dir():
                    category_name = category_dir.name
                    
                    for file_path in category_dir.iterdir():
                        if file_path.is_file() and file_path.suffix.lower() in image_extensions:
                            documents.append({
                                'path': str(file_path),
                                'name': file_path.name,
                                'category': category_name
                            })
        
        # Sort by category and name for consistent processing
        documents.sort(key=lambda x: (x['category'], x['name']))
        
        # Apply limit if specified
        if limit and limit > 0:
            documents = documents[:limit]
        
        return documents

    def _document_exists(self, pipeline: DocumentPipeline, file_path: str) -> bool:
        """Check if document already exists in the database."""
        try:
            # Search for document by filename
            filename = os.path.basename(file_path)
            results = pipeline.search(filename, limit=1)
            
            # Check if any result has exactly matching filename
            for result in results:
                if result.get('metadata', {}).get('filename') == filename:
                    return True
            
            return False
            
        except Exception as e:
            logger.warning(f'Error checking if document exists: {str(e)}')
            return False
