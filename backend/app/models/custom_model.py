"""
Custom Model
"""
import uuid
from datetime import datetime
from ..extensions import db


class CustomModel(db.Model):
    """User-defined custom model with knowledge base bindings"""
    __tablename__ = 'custom_models'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = db.Column(db.String(36), db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    name = db.Column(db.String(100), nullable=False)
    base_model = db.Column(db.String(100), nullable=False)  # Ollama model name
    system_prompt = db.Column(db.Text, nullable=True)
    description = db.Column(db.String(500), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    conversations = db.relationship('Conversation', backref='custom_model', lazy='dynamic')
    knowledge_bindings = db.relationship('ModelKnowledgeBinding', backref='custom_model', 
                                         lazy='dynamic', cascade='all, delete-orphan')
    
    def to_dict(self, include_knowledge=False):
        """Convert to dictionary"""
        data = {
            'id': self.id,
            'user_id': self.user_id,
            'name': self.name,
            'base_model': self.base_model,
            'system_prompt': self.system_prompt,
            'description': self.description,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
        if include_knowledge:
            data['knowledge_bases'] = [
                binding.knowledge_base.to_dict() 
                for binding in self.knowledge_bindings.all()
                if binding.knowledge_base
            ]
        return data
    
    def __repr__(self):
        return f'<CustomModel {self.name}>'
