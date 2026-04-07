"""
Knowledge Base Model
"""
import uuid
from datetime import datetime
from ..extensions import db


class KnowledgeBase(db.Model):
    """Knowledge base for RAG"""
    __tablename__ = 'knowledge_bases'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = db.Column(db.String(36), db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(500), nullable=True)
    collection_name = db.Column(db.String(100), unique=True, nullable=False)  # Chroma collection name
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    files = db.relationship('File', backref='knowledge_base', lazy='dynamic', cascade='all, delete-orphan')
    model_bindings = db.relationship('ModelKnowledgeBinding', backref='knowledge_base', 
                                     lazy='dynamic', cascade='all, delete-orphan')
    
    def to_dict(self, include_files=False):
        """Convert to dictionary"""
        data = {
            'id': self.id,
            'user_id': self.user_id,
            'name': self.name,
            'description': self.description,
            'collection_name': self.collection_name,
            'file_count': self.files.count(),
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
        if include_files:
            data['files'] = [f.to_dict() for f in self.files.all()]
        return data
    
    def __repr__(self):
        return f'<KnowledgeBase {self.name}>'


class ModelKnowledgeBinding(db.Model):
    """Many-to-many relationship between CustomModel and KnowledgeBase"""
    __tablename__ = 'model_knowledge_bindings'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    custom_model_id = db.Column(db.String(36), db.ForeignKey('custom_models.id', ondelete='CASCADE'), 
                                nullable=False, index=True)
    knowledge_base_id = db.Column(db.String(36), db.ForeignKey('knowledge_bases.id', ondelete='CASCADE'), 
                                  nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Unique constraint
    __table_args__ = (
        db.UniqueConstraint('custom_model_id', 'knowledge_base_id', name='unique_model_knowledge'),
    )
    
    def __repr__(self):
        return f'<ModelKnowledgeBinding {self.custom_model_id[:8]} - {self.knowledge_base_id[:8]}>'
