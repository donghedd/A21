"""
API Blueprints
"""
from flask import Blueprint

# Create blueprints
auth_bp = Blueprint('auth', __name__)
chat_bp = Blueprint('chat', __name__)
model_bp = Blueprint('models', __name__)
knowledge_bp = Blueprint('knowledge', __name__)
file_bp = Blueprint('files', __name__)
admin_bp = Blueprint('admin', __name__)
kg_bp = Blueprint('kg', __name__)

# Import routes (will be implemented later)
from . import auth
from . import chat
from . import model
from . import knowledge
from . import file
from . import admin
from . import kg

__all__ = ['auth_bp', 'chat_bp', 'model_bp', 'knowledge_bp', 'file_bp', 'admin_bp', 'kg_bp']
