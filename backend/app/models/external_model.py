"""
External Model
"""
import uuid
from datetime import datetime
from ..extensions import db


class ExternalModel(db.Model):
    """User-configured external API model"""
    __tablename__ = 'external_models'

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = db.Column(db.String(36), db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    name = db.Column(db.String(100), nullable=False)
    api_key = db.Column(db.String(255), nullable=False)
    api_base_url = db.Column(db.String(255), nullable=True, default='https://api.openai.com/v1')
    model_name = db.Column(db.String(100), nullable=True)
    system_prompt = db.Column(db.Text, nullable=True)
    description = db.Column(db.String(500), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    conversations = db.relationship('Conversation', backref='external_model', lazy='dynamic')

    def to_dict(self):
        model_id = self.model_name or self.name
        masked_key = ''
        if self.api_key:
            if len(self.api_key) <= 8:
                masked_key = '*' * len(self.api_key)
            else:
                masked_key = f"{self.api_key[:4]}***{self.api_key[-4:]}"

        return {
            'id': self.id,
            'user_id': self.user_id,
            'name': self.name,
            'api_key': self.api_key,
            'api_key_masked': masked_key,
            'api_base_url': self.api_base_url,
            'model_name': model_id,
            'system_prompt': self.system_prompt,
            'description': self.description,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self):
        return f'<ExternalModel {self.name}>'
