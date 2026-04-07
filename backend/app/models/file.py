"""
File Model
"""
import uuid
from datetime import datetime
from ..extensions import db


class File(db.Model):
    """Uploaded file for knowledge base"""
    __tablename__ = 'files'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    knowledge_base_id = db.Column(db.String(36), db.ForeignKey('knowledge_bases.id', ondelete='CASCADE'), 
                                  nullable=False, index=True)
    user_id = db.Column(db.String(36), db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    filename = db.Column(db.String(255), nullable=False)
    filepath = db.Column(db.String(500), nullable=False)
    file_type = db.Column(db.String(50), nullable=False)
    file_size = db.Column(db.BigInteger, nullable=False)
    content_hash = db.Column(db.String(64), nullable=True, index=True)  # SHA256 hash
    chunk_count = db.Column(db.Integer, default=0)
    status = db.Column(
        db.Enum('pending', 'processing', 'completed', 'failed', name='file_status'),
        default='pending',
        nullable=False
    )
    error_message = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            'id': self.id,
            'knowledge_base_id': self.knowledge_base_id,
            'user_id': self.user_id,
            'filename': self.filename,
            'file_type': self.file_type,
            'file_size': self.file_size,
            'chunk_count': self.chunk_count,
            'status': self.status,
            'error_message': self.error_message,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
    
    def __repr__(self):
        return f'<File {self.filename}>'
