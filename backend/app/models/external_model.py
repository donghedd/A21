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
    is_system = db.Column(db.Boolean, nullable=False, default=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    conversations = db.relationship('Conversation', backref='external_model', lazy='dynamic')
    knowledge_bindings = db.relationship(
        'ExternalModelKnowledgeBinding',
        backref='external_model',
        lazy='dynamic',
        cascade='all, delete-orphan'
    )

    def to_dict(self, include_knowledge=False):
        model_id = self.model_name or self.name
        masked_key = ''
        if self.api_key:
            if len(self.api_key) <= 8:
                masked_key = '*' * len(self.api_key)
            else:
                masked_key = f"{self.api_key[:4]}***{self.api_key[-4:]}"

        data = {
            'id': self.id,
            'user_id': self.user_id,
            'name': self.name,
            'has_api_key': bool(self.api_key),
            'api_key_masked': masked_key,
            'api_base_url': self.api_base_url,
            'model_name': model_id,
            'system_prompt': self.system_prompt,
            'description': self.description,
            'is_system': self.is_system,
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

    @staticmethod
    def get_visible_query(user_id: str):
        return ExternalModel.query.filter(
            db.or_(
                ExternalModel.user_id == user_id,
                ExternalModel.is_system.is_(True),
            )
        )

    @staticmethod
    def get_visible_by_id(model_id: str, user_id: str):
        return ExternalModel.get_visible_query(user_id).filter(ExternalModel.id == model_id).first()

    def can_edit(self, user) -> bool:
        if not user:
            return False
        if getattr(user, 'role', None) == 'admin':
            return True
        if self.is_system:
            return False
        return self.user_id == user.id

    def __repr__(self):
        return f'<ExternalModel {self.name}>'


class ExternalModelKnowledgeBinding(db.Model):
    """Many-to-many relationship between ExternalModel and KnowledgeBase"""
    __tablename__ = 'external_model_knowledge_bindings'

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    external_model_id = db.Column(
        db.String(36),
        db.ForeignKey('external_models.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )
    knowledge_base_id = db.Column(
        db.String(36),
        db.ForeignKey('knowledge_bases.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint('external_model_id', 'knowledge_base_id', name='unique_external_model_knowledge'),
    )

    knowledge_base = db.relationship('KnowledgeBase', lazy='joined')

    def __repr__(self):
        return f'<ExternalModelKnowledgeBinding {self.external_model_id[:8]} - {self.knowledge_base_id[:8]}>'
