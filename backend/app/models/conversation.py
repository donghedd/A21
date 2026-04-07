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
    title = db.Column(db.String(200), nullable=False, default='New Conversation')
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
            'title': self.title,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
        if include_messages:
            data['messages'] = [msg.to_dict() for msg in self.messages.all()]
        return data
    
    def __repr__(self):
        return f'<Conversation {self.id[:8]}>'
