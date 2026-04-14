"""Model Management API Routes
"""
import uuid
from flask import request
from flask_jwt_extended import jwt_required, get_jwt_identity
from . import model_bp
from ..utils.response import success_response, error_response
from ..models import CustomModel, KnowledgeBase, ModelKnowledgeBinding, User, ExternalModel, ExternalModelKnowledgeBinding
from ..extensions import db
from ..services import get_llm_service, get_llm_provider, get_external_model_service


@model_bp.route('/ollama', methods=['GET'])
@jwt_required()
def get_ollama_models():
    """Get available LLM models (Ollama or llama.cpp)"""
    llm = get_llm_service()
    models = llm.get_models()

    return success_response(
        data=[{
            'name': m.get('name', ''),
            'size': m.get('size', 0),
            'modified_at': m.get('modified_at', ''),
            'provider': get_llm_provider()
        } for m in models]
    )


@model_bp.route('/custom', methods=['GET'])
@jwt_required()
def get_custom_models():
    """Get visible custom models: own plus shared/system."""
    user_id = get_jwt_identity()
    
    models = CustomModel.get_visible_query(user_id).order_by(
        CustomModel.is_system.desc(),
        CustomModel.created_at.desc()
    ).all()
    
    return success_response(
        data=[m.to_dict(include_knowledge=True) for m in models]
    )


@model_bp.route('/custom', methods=['POST'])
@jwt_required()
def create_custom_model():
    """Create a custom model"""
    user_id = get_jwt_identity()
    data = request.get_json()
    
    if not data or not data.get('name') or not data.get('base_model'):
        return error_response(400, 'Name and base_model are required')

    user = User.query.get(user_id)
    if not user:
        return error_response(401, 'User not found')

    requested_shared = bool(data.get('is_system', False))
    if requested_shared and user.role != 'admin':
        return error_response(403, 'Only admin can create shared models')
    
    model = CustomModel(
        id=str(uuid.uuid4()),
        user_id=user_id,
        name=data['name'],
        base_model=data['base_model'],
        system_prompt=data.get('system_prompt', ''),
        description=data.get('description', ''),
        is_system=requested_shared
    )
    
    try:
        db.session.add(model)
        db.session.commit()
        return success_response(model.to_dict(), 'Model created', 201)
    except Exception as e:
        db.session.rollback()
        return error_response(400, str(e))


@model_bp.route('/custom/<model_id>', methods=['GET'])
@jwt_required()
def get_custom_model(model_id):
    """Get custom model details"""
    user_id = get_jwt_identity()
    
    model = CustomModel.get_visible_by_id(model_id, user_id)
    if not model:
        return error_response(404, 'Model not found')
    
    return success_response(model.to_dict(include_knowledge=True))


@model_bp.route('/custom/<model_id>', methods=['PUT'])
@jwt_required()
def update_custom_model(model_id):
    """Update custom model"""
    user_id = get_jwt_identity()
    data = request.get_json()
    
    user = User.query.get(user_id)
    model = CustomModel.get_visible_by_id(model_id, user_id)
    if not model:
        return error_response(404, 'Model not found')
    if not model.can_edit(user):
        return error_response(403, 'Permission denied')
    
    if 'name' in data:
        model.name = data['name']
    if 'base_model' in data:
        model.base_model = data['base_model']
    if 'system_prompt' in data:
        model.system_prompt = data['system_prompt']
    if 'description' in data:
        model.description = data['description']
    if 'is_system' in data:
        if not user or user.role != 'admin':
            return error_response(403, 'Only admin can change shared flag')
        model.is_system = bool(data.get('is_system'))
    
    try:
        db.session.commit()
        return success_response(model.to_dict(include_knowledge=True), 'Model updated')
    except Exception as e:
        db.session.rollback()
        return error_response(400, str(e))


@model_bp.route('/custom/<model_id>', methods=['DELETE'])
@jwt_required()
def delete_custom_model(model_id):
    """Delete custom model"""
    user_id = get_jwt_identity()
    
    user = User.query.get(user_id)
    model = CustomModel.get_visible_by_id(model_id, user_id)
    if not model:
        return error_response(404, 'Model not found')
    if not model.can_edit(user):
        return error_response(403, 'Permission denied')
    
    try:
        db.session.delete(model)
        db.session.commit()
        return success_response(message='Model deleted')
    except Exception as e:
        db.session.rollback()
        return error_response(400, str(e))


@model_bp.route('/custom/<model_id>/knowledge', methods=['POST'])
@jwt_required()
def bind_knowledge_base(model_id):
    """Bind knowledge base to model"""
    user_id = get_jwt_identity()
    data = request.get_json()
    
    if not data or not data.get('knowledge_base_id'):
        return error_response(400, 'knowledge_base_id is required')
    
    user = User.query.get(user_id)
    model = CustomModel.get_visible_by_id(model_id, user_id)
    if not model:
        return error_response(404, 'Model not found')
    if not model.can_edit(user):
        return error_response(403, 'Permission denied')
    
    kb = KnowledgeBase.get_visible_by_id(data['knowledge_base_id'], user_id)
    if not kb:
        return error_response(404, 'Knowledge base not found')
    
    # Check if binding exists
    existing = ModelKnowledgeBinding.query.filter_by(
        custom_model_id=model_id,
        knowledge_base_id=kb.id
    ).first()
    
    if existing:
        return error_response(400, 'Knowledge base already bound to this model')
    
    binding = ModelKnowledgeBinding(
        id=str(uuid.uuid4()),
        custom_model_id=model_id,
        knowledge_base_id=kb.id
    )
    
    try:
        db.session.add(binding)
        db.session.commit()
        return success_response(
            model.to_dict(include_knowledge=True),
            'Knowledge base bound'
        )
    except Exception as e:
        db.session.rollback()
        return error_response(400, str(e))


@model_bp.route('/custom/<model_id>/knowledge/<kb_id>', methods=['DELETE'])
@jwt_required()
def unbind_knowledge_base(model_id, kb_id):
    """Unbind knowledge base from model"""
    user_id = get_jwt_identity()
    
    user = User.query.get(user_id)
    model = CustomModel.get_visible_by_id(model_id, user_id)
    if not model:
        return error_response(404, 'Model not found')
    if not model.can_edit(user):
        return error_response(403, 'Permission denied')
    
    binding = ModelKnowledgeBinding.query.filter_by(
        custom_model_id=model_id,
        knowledge_base_id=kb_id
    ).first()
    
    if not binding:
        return error_response(404, 'Binding not found')
    
    try:
        db.session.delete(binding)
        db.session.commit()
        return success_response(
            model.to_dict(include_knowledge=True),
            'Knowledge base unbound'
        )
    except Exception as e:
        db.session.rollback()
        return error_response(400, str(e))


@model_bp.route('/external', methods=['GET'])
@jwt_required()
def get_external_models():
    """Get visible external API models."""
    user_id = get_jwt_identity()

    models = ExternalModel.get_visible_query(user_id).order_by(
        ExternalModel.is_system.desc(),
        ExternalModel.created_at.desc()
    ).all()

    return success_response(
        data=[m.to_dict(include_knowledge=True) for m in models]
    )


@model_bp.route('/external', methods=['POST'])
@jwt_required()
def create_external_model():
    """Create an external API model."""
    user_id = get_jwt_identity()
    data = request.get_json() or {}

    if not data.get('name') or not data.get('model_name') or not data.get('api_key'):
        return error_response(400, 'name, model_name and api_key are required')

    user = User.query.get(user_id)
    requested_shared = bool(data.get('is_system', False))
    if requested_shared and (not user or user.role != 'admin'):
        return error_response(403, 'Only admin can create shared external models')

    model = ExternalModel(
        id=str(uuid.uuid4()),
        user_id=user_id,
        name=data['name'],
        api_key=data['api_key'],
        api_base_url=(data.get('api_base_url') or 'https://api.openai.com/v1').strip(),
        model_name=data['model_name'],
        system_prompt=data.get('system_prompt', ''),
        description=data.get('description', ''),
        is_system=requested_shared
    )

    try:
        db.session.add(model)
        db.session.commit()
        return success_response(model.to_dict(include_knowledge=True), 'External model created', 201)
    except Exception as e:
        db.session.rollback()
        return error_response(400, str(e))


@model_bp.route('/external/<model_id>', methods=['PUT'])
@jwt_required()
def update_external_model(model_id):
    """Update an external API model."""
    user_id = get_jwt_identity()
    data = request.get_json() or {}

    user = User.query.get(user_id)
    model = ExternalModel.get_visible_by_id(model_id, user_id)
    if not model:
        return error_response(404, 'External model not found')
    if not model.can_edit(user):
        return error_response(403, 'Permission denied')

    if 'name' in data:
        model.name = data['name']
    if 'model_name' in data:
        model.model_name = data['model_name']
    if 'api_base_url' in data:
        model.api_base_url = (data.get('api_base_url') or 'https://api.openai.com/v1').strip()
    if data.get('api_key'):
        model.api_key = data['api_key']
    if 'system_prompt' in data:
        model.system_prompt = data.get('system_prompt', '')
    if 'description' in data:
        model.description = data.get('description', '')
    if 'is_system' in data:
        if not user or user.role != 'admin':
            return error_response(403, 'Only admin can change shared flag')
        model.is_system = bool(data.get('is_system'))

    try:
        db.session.commit()
        return success_response(model.to_dict(include_knowledge=True), 'External model updated')
    except Exception as e:
        db.session.rollback()
        return error_response(400, str(e))


@model_bp.route('/external/<model_id>', methods=['DELETE'])
@jwt_required()
def delete_external_model(model_id):
    """Delete an external API model."""
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    model = ExternalModel.get_visible_by_id(model_id, user_id)
    if not model:
        return error_response(404, 'External model not found')
    if not model.can_edit(user):
        return error_response(403, 'Permission denied')

    try:
        db.session.delete(model)
        db.session.commit()
        return success_response(message='External model deleted')
    except Exception as e:
        db.session.rollback()
        return error_response(400, str(e))


@model_bp.route('/external/<model_id>/test', methods=['POST'])
@jwt_required()
def test_external_model(model_id):
    """Test connectivity for an external API model."""
    user_id = get_jwt_identity()
    model = ExternalModel.get_visible_by_id(model_id, user_id)
    if not model:
        return error_response(404, 'External model not found')

    try:
        service = get_external_model_service(
            api_key=model.api_key,
            base_url=model.api_base_url
        )
        result = service.test_connection(model.model_name or model.name)
        return success_response(data=result, message='External model connection OK')
    except Exception as e:
        return error_response(400, f'Connection test failed: {str(e)}')


@model_bp.route('/external/<model_id>/knowledge', methods=['POST'])
@jwt_required()
def bind_external_knowledge_base(model_id):
    """Bind knowledge base to external model."""
    user_id = get_jwt_identity()
    data = request.get_json() or {}

    if not data.get('knowledge_base_id'):
        return error_response(400, 'knowledge_base_id is required')

    user = User.query.get(user_id)
    model = ExternalModel.get_visible_by_id(model_id, user_id)
    if not model:
        return error_response(404, 'External model not found')
    if not model.can_edit(user):
        return error_response(403, 'Permission denied')

    kb = KnowledgeBase.get_visible_by_id(data['knowledge_base_id'], user_id)
    if not kb:
        return error_response(404, 'Knowledge base not found')

    existing = ExternalModelKnowledgeBinding.query.filter_by(
        external_model_id=model_id,
        knowledge_base_id=kb.id
    ).first()
    if existing:
        return error_response(400, 'Knowledge base already bound to this model')

    binding = ExternalModelKnowledgeBinding(
        id=str(uuid.uuid4()),
        external_model_id=model_id,
        knowledge_base_id=kb.id
    )

    try:
        db.session.add(binding)
        db.session.commit()
        return success_response(model.to_dict(include_knowledge=True), 'Knowledge base bound')
    except Exception as e:
        db.session.rollback()
        return error_response(400, str(e))


@model_bp.route('/external/<model_id>/knowledge/<kb_id>', methods=['DELETE'])
@jwt_required()
def unbind_external_knowledge_base(model_id, kb_id):
    """Unbind knowledge base from external model."""
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    model = ExternalModel.get_visible_by_id(model_id, user_id)
    if not model:
        return error_response(404, 'External model not found')
    if not model.can_edit(user):
        return error_response(403, 'Permission denied')

    binding = ExternalModelKnowledgeBinding.query.filter_by(
        external_model_id=model_id,
        knowledge_base_id=kb_id
    ).first()
    if not binding:
        return error_response(404, 'Binding not found')

    try:
        db.session.delete(binding)
        db.session.commit()
        return success_response(model.to_dict(include_knowledge=True), 'Knowledge base unbound')
    except Exception as e:
        db.session.rollback()
        return error_response(400, str(e))


@model_bp.route('/health', methods=['GET'])
@jwt_required()
def get_llm_health():
    """Get LLM service health status"""
    llm = get_llm_service()
    provider = get_llm_provider()

    is_available = llm.is_available()

    return success_response(
        data={
            'provider': provider,
            'available': is_available,
            'default_model': llm.get_default_model() if is_available else None
        }
    )
