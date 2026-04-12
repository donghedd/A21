"""
Conversation Model
"""
import uuid
from datetime import datetime
from ..extensions import db


class Conversation(db.Model):
    """Conversation/Chat session model"""
    __tablename__ = 'conversations'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = db.Column(db.String(36), db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    custom_model_id = db.Column(db.String(36), db.ForeignKey('custom_models.id', ondelete='SET NULL'), nullable=True)
    external_model_id = db.Column(db.String(36), db.ForeignKey('external_models.id', ondelete='SET NULL'), nullable=True, index=True)
    title = db.Column(db.String(200), nullable=False, default='New Conversation')
    deleted_by_user = db.Column(db.Boolean, nullable=False, default=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    messages = db.relationship('Message', backref='conversation', lazy='dynamic', 
                               cascade='all, delete-orphan', order_by='Message.created_at')
    
    def to_dict(self, include_messages=False):
        """Convert to dictionary"""
        data = {
            'id': self.id,
            'user_id': self.user_id,
            'custom_model_id': self.custom_model_id,
            'external_model_id': self.external_model_id,
            'title': self.title,
            'deleted_by_user': self.deleted_by_user,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
        if include_messages:
            data['messages'] = [msg.to_dict() for msg in self.messages.all()]
        return data
    
    def __repr__(self):
        return f'<Conversation {self.id[:8]}>'
