"""
Message Model
"""
import uuid
import json
from datetime import datetime
from ..extensions import db


class Message(db.Model):
    """Chat message model"""
    __tablename__ = 'messages'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    conversation_id = db.Column(db.String(36), db.ForeignKey('conversations.id', ondelete='CASCADE'), 
                                nullable=False, index=True)
    role = db.Column(db.Enum('user', 'assistant', 'system', name='message_role'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    thinking_content = db.Column(db.Text, nullable=True)
    sources = db.Column(db.JSON, nullable=True)  # JSON array of source references
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            'id': self.id,
            'conversation_id': self.conversation_id,
            'role': self.role,
            'content': self.content,
            'thinking_content': self.thinking_content,
            'sources': self.sources or [],
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
    
    def __repr__(self):
        return f'<Message {self.id[:8]} ({self.role})>'
