"""
File Processing Service
"""
import os
import uuid
import hashlib
import shutil
from typing import Optional
from flask import current_app
import logging

from ..extensions import db
from ..models import File, KnowledgeBase, User
from .rag_service import get_rag_service

logger = logging.getLogger(__name__)


class FileService:
    """Service for file upload and processing"""

    @staticmethod
    def normalize_original_filename(filename: str) -> str:
        """Preserve user-facing filenames, including Chinese characters."""
        if not filename:
            return ''

        normalized = filename.replace('\\', '/').split('/')[-1]
        normalized = normalized.strip().strip('. ')
        normalized = ''.join(ch for ch in normalized if ch not in '\x00\r\n\t')
        return normalized[:255]
    
    @staticmethod
    def allowed_file(filename: str) -> bool:
        """Check if file extension is allowed"""
        if '.' not in filename:
            return False
        ext = filename.rsplit('.', 1)[1].lower()
        return ext in current_app.config.get('ALLOWED_EXTENSIONS', set())
    
    @staticmethod
    def save_uploaded_file(file, knowledge_base_id: str, user_id: str) -> Optional[File]:
        """Save uploaded file to disk and create database record"""
        if not file or not file.filename:
            raise ValueError("No file provided")
        
        if not FileService.allowed_file(file.filename):
            raise ValueError(f"File type not allowed. Allowed: {', '.join(current_app.config['ALLOWED_EXTENSIONS'])}")
        
        # Get knowledge base
        kb = KnowledgeBase.query.get(knowledge_base_id)
        if not kb:
            raise ValueError("Knowledge base not found")
        user = User.query.get(user_id)
        if not kb.can_edit(user):
            raise ValueError("Permission denied")
        
        # Preserve the original display name, including Chinese characters.
        original_filename = FileService.normalize_original_filename(file.filename)
        if not original_filename or '.' not in original_filename:
            raise ValueError("Invalid filename")
        file_ext = original_filename.rsplit('.', 1)[1].lower() if '.' in original_filename else ''
        unique_filename = f"{uuid.uuid4()}.{file_ext}"
        
        # Create upload directory
        upload_dir = os.path.join(
            current_app.config['UPLOAD_FOLDER'],
            knowledge_base_id
        )
        os.makedirs(upload_dir, exist_ok=True)
        
        # Save file
        filepath = os.path.join(upload_dir, unique_filename)
        file.save(filepath)
        
        # Get file size
        file_size = os.path.getsize(filepath)
        
        # Create database record
        file_record = File(
            id=str(uuid.uuid4()),
            knowledge_base_id=knowledge_base_id,
            user_id=user_id,
            filename=original_filename,
            filepath=filepath,
            file_type=file_ext,
            file_size=file_size,
            status='pending'
        )
        
        db.session.add(file_record)
        db.session.commit()
        
        logger.info(f"Saved file: {original_filename} -> {filepath}")
        
        return file_record

    @staticmethod
    def import_local_file(source_path: str, knowledge_base_id: str, user_id: str) -> Optional[File]:
        """Copy a local file into uploads and create a file record for indexing."""
        if not source_path or not os.path.exists(source_path):
            raise ValueError("Source file not found")

        filename = os.path.basename(source_path)
        filename = FileService.normalize_original_filename(filename)
        if not FileService.allowed_file(filename):
            raise ValueError(
                f"File type not allowed. Allowed: {', '.join(sorted(current_app.config['ALLOWED_EXTENSIONS']))}"
            )

        kb = KnowledgeBase.query.get(knowledge_base_id)
        if not kb:
            raise ValueError("Knowledge base not found")

        user = User.query.get(user_id)
        if not kb.can_edit(user):
            raise ValueError("Permission denied")

        existing = File.query.filter_by(
            knowledge_base_id=knowledge_base_id,
            filename=filename
        ).first()
        if existing:
            return existing

        file_ext = filename.rsplit('.', 1)[1].lower()
        unique_filename = f"{uuid.uuid4()}.{file_ext}"

        upload_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], knowledge_base_id)
        os.makedirs(upload_dir, exist_ok=True)

        filepath = os.path.join(upload_dir, unique_filename)
        shutil.copy2(source_path, filepath)
        file_size = os.path.getsize(filepath)

        file_record = File(
            id=str(uuid.uuid4()),
            knowledge_base_id=knowledge_base_id,
            user_id=user_id,
            filename=filename,
            filepath=filepath,
            file_type=file_ext,
            file_size=file_size,
            status='pending'
        )

        db.session.add(file_record)
        db.session.commit()
        logger.info(f"Imported local file: {filename} -> {filepath}")
        return file_record
    
    @staticmethod
    def process_file(file_id: str, progress_callback=None) -> dict:
        """Process a file through the RAG pipeline"""
        file_record = File.query.get(file_id)
        if not file_record:
            raise ValueError("File not found")
        
        try:
            # Update status to processing
            file_record.status = 'processing'
            db.session.commit()
            
            # Get knowledge base collection name
            kb = KnowledgeBase.query.get(file_record.knowledge_base_id)
            if not kb:
                raise ValueError("Knowledge base not found")
            
            # Process through RAG pipeline
            rag_service = get_rag_service()
            result = rag_service.process_file(
                file_path=file_record.filepath,
                file_type=file_record.file_type,
                collection_name=kb.collection_name,
                file_id=file_record.id,
                original_filename=file_record.filename,
                progress_callback=progress_callback
            )
            
            # Update file record
            file_record.status = 'completed'
            file_record.chunk_count = result['chunk_count']
            file_record.content_hash = result['content_hash']
            file_record.error_message = None
            db.session.commit()
            
            logger.info(f"File processed successfully: {file_record.filename}")
            
            return {
                'success': True,
                'file_id': file_id,
                'chunk_count': result['chunk_count']
            }
            
        except Exception as e:
            logger.error(f"File processing failed: {e}")
            try:
                db.session.rollback()
                # Re-fetch to ensure clean state
                file_record = File.query.get(file_id)
                if file_record:
                    file_record.status = 'failed'
                    file_record.error_message = str(e)[:500]
                    db.session.commit()
            except Exception as commit_err:
                logger.error(f"Failed to update file status: {commit_err}")
            raise
    
    @staticmethod
    def delete_file(file_id: str, user_id: str) -> bool:
        """Delete a file and its vectors"""
        file_record = File.query.get(file_id)
        if not file_record:
            raise ValueError("File not found")
        
        if file_record.user_id != user_id:
            user = User.query.get(user_id)
            if not user or user.role != 'admin':
                raise ValueError("Permission denied")
        
        try:
            # Get knowledge base
            kb = KnowledgeBase.query.get(file_record.knowledge_base_id)
            
            # Delete from vector database
            if kb and file_record.status == 'completed':
                rag_service = get_rag_service()
                rag_service.delete_file_from_collection(
                    collection_name=kb.collection_name,
                    file_id=file_id
                )
            
            # Delete physical file
            if os.path.exists(file_record.filepath):
                os.remove(file_record.filepath)
            
            # Delete database record
            db.session.delete(file_record)
            db.session.commit()
            
            logger.info(f"File deleted: {file_record.filename}")
            return True
            
        except Exception as e:
            logger.error(f"File deletion failed: {e}")
            raise
    
    @staticmethod
    def get_file_status(file_id: str) -> dict:
        """Get file processing status"""
        file_record = File.query.get(file_id)
        if not file_record:
            return {'error': 'File not found'}
        
        return {
            'id': file_record.id,
            'filename': file_record.filename,
            'status': file_record.status,
            'chunk_count': file_record.chunk_count,
            'error_message': file_record.error_message
        }


def get_file_service() -> FileService:
    """Get file service instance"""
    return FileService()
