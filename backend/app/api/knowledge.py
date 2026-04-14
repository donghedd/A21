"""Knowledge Base API Routes
"""
import uuid
from flask import request
from flask_jwt_extended import jwt_required, get_jwt_identity
from . import knowledge_bp
from ..utils.response import success_response, error_response
from ..models import KnowledgeBase, File, User
from ..extensions import db
from ..services import get_vector_service


@knowledge_bp.route('/', methods=['GET'])
@jwt_required()
def get_knowledge_bases():
    """Get visible knowledge bases: own plus shared/system."""
    user_id = get_jwt_identity()

    kbs = KnowledgeBase.get_visible_query(user_id).order_by(
        KnowledgeBase.is_system.desc(),
        KnowledgeBase.created_at.desc()
    ).all()
    
    return success_response(
        data=[kb.to_dict() for kb in kbs]
    )


@knowledge_bp.route('/', methods=['POST'])
@jwt_required()
def create_knowledge_base():
    """Create a new knowledge base"""
    user_id = get_jwt_identity()
    data = request.get_json()
    
    if not data or not data.get('name'):
        return error_response(400, 'Name is required')

    user = User.query.get(user_id)
    if not user:
        return error_response(401, 'User not found')

    requested_shared = bool(data.get('is_system', False))
    if requested_shared and user.role != 'admin':
        return error_response(403, 'Only admin can create shared knowledge bases')
    
    # Generate unique collection name
    collection_name = f"kb_{uuid.uuid4().hex[:12]}"
    
    kb = KnowledgeBase(
        id=str(uuid.uuid4()),
        user_id=user_id,
        name=data['name'],
        description=data.get('description', ''),
        collection_name=collection_name,
        is_system=requested_shared
    )
    
    try:
        db.session.add(kb)
        db.session.commit()
        return success_response(kb.to_dict(), 'Knowledge base created', 201)
    except Exception as e:
        db.session.rollback()
        return error_response(400, str(e))


@knowledge_bp.route('/<kb_id>', methods=['GET'])
@jwt_required()
def get_knowledge_base(kb_id):
    """Get knowledge base details"""
    user_id = get_jwt_identity()
    
    kb = KnowledgeBase.get_visible_by_id(kb_id, user_id)
    if not kb:
        return error_response(404, 'Knowledge base not found')
    
    return success_response(kb.to_dict(include_files=True))


@knowledge_bp.route('/<kb_id>', methods=['PUT'])
@jwt_required()
def update_knowledge_base(kb_id):
    """Update knowledge base"""
    user_id = get_jwt_identity()
    data = request.get_json()
    
    user = User.query.get(user_id)
    kb = KnowledgeBase.get_visible_by_id(kb_id, user_id)
    if not kb:
        return error_response(404, 'Knowledge base not found')
    if not kb.can_edit(user):
        return error_response(403, 'Permission denied')
    
    if 'name' in data:
        kb.name = data['name']
    if 'description' in data:
        kb.description = data['description']
    if 'is_system' in data:
        if not user or user.role != 'admin':
            return error_response(403, 'Only admin can change shared flag')
        kb.is_system = bool(data.get('is_system'))
    
    try:
        db.session.commit()
        return success_response(kb.to_dict(), 'Knowledge base updated')
    except Exception as e:
        db.session.rollback()
        return error_response(400, str(e))


@knowledge_bp.route('/<kb_id>', methods=['DELETE'])
@jwt_required()
def delete_knowledge_base(kb_id):
    """Delete knowledge base and all its files"""
    user_id = get_jwt_identity()
    
    user = User.query.get(user_id)
    kb = KnowledgeBase.get_visible_by_id(kb_id, user_id)
    if not kb:
        return error_response(404, 'Knowledge base not found')
    if not kb.can_edit(user):
        return error_response(403, 'Permission denied')
    
    try:
        # Delete vector collection
        vector_service = get_vector_service()
        vector_service.delete_collection(kb.collection_name)
        
        # Delete from database (files will cascade delete)
        db.session.delete(kb)
        db.session.commit()
        
        return success_response(message='Knowledge base deleted')
    except Exception as e:
        db.session.rollback()
        return error_response(400, str(e))


@knowledge_bp.route('/<kb_id>/files', methods=['GET'])
@jwt_required()
def get_knowledge_base_files(kb_id):
    """Get files in knowledge base"""
    user_id = get_jwt_identity()
    
    kb = KnowledgeBase.get_visible_by_id(kb_id, user_id)
    if not kb:
        return error_response(404, 'Knowledge base not found')
    
    files = File.query.filter_by(knowledge_base_id=kb_id).order_by(
        File.created_at.desc()
    ).all()
    
    return success_response(
        data=[f.to_dict() for f in files]
    )
