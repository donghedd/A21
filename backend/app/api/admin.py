"""Admin API Routes
"""
from datetime import datetime, timedelta

from flask import request
from sqlalchemy import or_, func

from . import admin_bp
from ..extensions import db
from ..models import User, Conversation, Message, KnowledgeBase, CustomModel, ExternalModel
from ..utils.decorators import admin_required, get_current_user
from ..utils.response import success_response, error_response


def _parse_history_filters():
    keyword = request.args.get('keyword', '').strip()
    username = request.args.get('username', '').strip()
    start_date = request.args.get('start_date', '').strip()
    end_date = request.args.get('end_date', '').strip()

    start_dt = None
    end_dt = None
    try:
        if start_date:
            start_dt = datetime.strptime(start_date, '%Y-%m-%d')
        if end_date:
            end_dt = datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1)
    except ValueError:
        raise ValueError('Invalid date format, expected YYYY-MM-DD')

    return keyword, username, start_dt, end_dt


@admin_bp.route('/users', methods=['GET'])
@admin_required
def get_users():
    """Get users with statistics"""
    keyword = request.args.get('keyword', '').strip()
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)

    query = User.query
    if keyword:
        like_pattern = f'%{keyword}%'
        query = query.filter(or_(
            User.username.ilike(like_pattern),
            User.email.ilike(like_pattern)
        ))

    pagination = query.order_by(User.created_at.desc()).paginate(
        page=page,
        per_page=per_page,
        error_out=False
    )

    users = pagination.items

    user_ids = [user.id for user in users]
    conversation_counts = {}
    if user_ids:
        counts = db.session.query(
            Conversation.user_id,
            func.count(Conversation.id)
        ).filter(
            Conversation.user_id.in_(user_ids)
        ).group_by(Conversation.user_id).all()
        conversation_counts = {user_id: count for user_id, count in counts}

    data = []
    for user in users:
        item = user.to_dict(include_email=True)
        item['conversation_count'] = conversation_counts.get(user.id, 0)
        data.append(item)

    return success_response(data={
        'items': data,
        'pagination': {
            'total': pagination.total,
            'page': page,
            'per_page': per_page,
            'pages': pagination.pages
        }
    })


@admin_bp.route('/users/<user_id>/role', methods=['PUT'])
@admin_required
def update_user_role(user_id):
    """Set or unset admin role"""
    current_user = get_current_user()
    if current_user and current_user.id == user_id:
        return error_response(400, 'You cannot change your own role')

    user = User.query.get(user_id)
    if not user:
        return error_response(404, 'User not found')

    role = (request.get_json() or {}).get('role')
    if role not in ('user', 'admin'):
        return error_response(400, 'Role must be user or admin')

    try:
        user.role = role
        db.session.commit()
        return success_response(data=user.to_dict(include_email=True), message='Role updated')
    except Exception as e:
        db.session.rollback()
        return error_response(400, str(e))


@admin_bp.route('/users/<user_id>/reset-password', methods=['POST'])
@admin_required
def reset_user_password(user_id):
    """Reset user password"""
    user = User.query.get(user_id)
    if not user:
        return error_response(404, 'User not found')

    data = request.get_json() or {}
    new_password = (data.get('new_password') or '123456').strip()
    if len(new_password) < 6:
        return error_response(400, 'Password must be at least 6 characters')

    try:
        user.set_password(new_password)
        db.session.commit()
        return success_response(message='Password reset successfully')
    except Exception as e:
        db.session.rollback()
        return error_response(400, str(e))


@admin_bp.route('/users/<user_id>', methods=['DELETE'])
@admin_required
def delete_user(user_id):
    """Delete user"""
    current_user = get_current_user()
    if current_user and current_user.id == user_id:
        return error_response(400, 'You cannot delete yourself')

    user = User.query.get(user_id)
    if not user:
        return error_response(404, 'User not found')

    try:
        db.session.delete(user)
        db.session.commit()
        return success_response(message='User deleted')
    except Exception as e:
        db.session.rollback()
        return error_response(400, str(e))


@admin_bp.route('/history/conversations', methods=['GET'])
@admin_required
def search_history_conversations():
    """Search conversations for admin history view"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)

    try:
        keyword, username, start_dt, end_dt = _parse_history_filters()
    except ValueError as e:
        return error_response(400, str(e))

    query = db.session.query(
        Conversation.id.label('conversation_id'),
        Conversation.title.label('conversation_title'),
        User.username.label('username'),
        User.email.label('email'),
        Conversation.updated_at.label('updated_at'),
        func.count(Message.id).label('message_count')
    ).join(
        User, Conversation.user_id == User.id
    ).outerjoin(
        Message, Message.conversation_id == Conversation.id
    )

    if keyword:
        like_pattern = f'%{keyword}%'
        query = query.filter(or_(
            Message.content.ilike(like_pattern),
            Conversation.title.ilike(like_pattern)
        ))

    if username:
        query = query.filter(User.username.ilike(f'%{username}%'))

    if start_dt:
        query = query.filter(Message.created_at >= start_dt)
    if end_dt:
        query = query.filter(Message.created_at < end_dt)

    query = query.group_by(
        Conversation.id,
        Conversation.title,
        User.username,
        User.email,
        Conversation.updated_at
    )

    pagination = query.order_by(
        Conversation.updated_at.desc(),
        Conversation.created_at.desc(),
        Conversation.id.desc()
    ).paginate(
        page=page,
        per_page=per_page,
        error_out=False
    )

    items = []
    for conversation_id, conversation_title, result_username, email, updated_at, message_count in pagination.items:
        items.append({
            'conversation_id': conversation_id,
            'conversation_title': conversation_title,
            'username': result_username,
            'email': email,
            'updated_at': updated_at.isoformat() if updated_at else None,
            'message_count': message_count
        })

    return success_response(data={
        'items': items,
        'pagination': {
            'total': pagination.total,
            'page': page,
            'per_page': per_page,
            'pages': pagination.pages
        }
    })


@admin_bp.route('/history/conversations/<conversation_id>', methods=['GET'])
@admin_required
def get_history_conversation_detail(conversation_id):
    """Get full conversation detail for admin history view"""
    conversation = Conversation.query.get(conversation_id)
    if not conversation:
        return error_response(404, 'Conversation not found')

    user = User.query.get(conversation.user_id)
    messages = Message.query.filter_by(
        conversation_id=conversation_id
    ).order_by(Message.created_at.asc()).all()

    return success_response(data={
        'conversation': {
            'id': conversation.id,
            'title': conversation.title,
            'created_at': conversation.created_at.isoformat() if conversation.created_at else None,
            'updated_at': conversation.updated_at.isoformat() if conversation.updated_at else None,
            'username': user.username if user else '',
            'email': user.email if user else ''
        },
        'messages': [message.to_dict() for message in messages]
    })


@admin_bp.route('/knowledge-bases', methods=['GET'])
@admin_required
def get_admin_knowledge_bases():
    """List knowledge bases created by admin users."""
    keyword = request.args.get('keyword', '').strip()

    query = db.session.query(KnowledgeBase, User).join(
        User, KnowledgeBase.user_id == User.id
    ).filter(
        User.role == 'admin'
    )

    if keyword:
        like_pattern = f'%{keyword}%'
        query = query.filter(or_(
            KnowledgeBase.name.ilike(like_pattern),
            KnowledgeBase.description.ilike(like_pattern),
            User.username.ilike(like_pattern)
        ))

    rows = query.order_by(KnowledgeBase.updated_at.desc()).all()
    items = []
    for kb, owner in rows:
        item = kb.to_dict()
        item['owner_username'] = owner.username if owner else ''
        item['owner_email'] = owner.email if owner else ''
        items.append(item)

    return success_response(data=items)


@admin_bp.route('/knowledge-bases/<kb_id>', methods=['PUT'])
@admin_required
def update_admin_knowledge_base(kb_id):
    """Admin update for knowledge base metadata."""
    kb = KnowledgeBase.query.get(kb_id)
    if not kb:
        return error_response(404, 'Knowledge base not found')

    data = request.get_json() or {}
    if 'name' in data:
        kb.name = (data.get('name') or '').strip() or kb.name
    if 'description' in data:
        kb.description = (data.get('description') or '').strip()
    if 'is_system' in data:
        kb.is_system = bool(data.get('is_system'))

    try:
        db.session.commit()
        return success_response(data=kb.to_dict(), message='Knowledge base updated')
    except Exception as e:
        db.session.rollback()
        return error_response(400, str(e))


@admin_bp.route('/workspace/models', methods=['GET'])
@admin_required
def get_admin_workspace_models():
    """List all admin-created local and external models."""
    keyword = request.args.get('keyword', '').strip()

    custom_query = db.session.query(CustomModel, User).join(
        User, CustomModel.user_id == User.id
    ).filter(User.role == 'admin')
    external_query = db.session.query(ExternalModel, User).join(
        User, ExternalModel.user_id == User.id
    ).filter(User.role == 'admin')

    if keyword:
        like_pattern = f'%{keyword}%'
        custom_query = custom_query.filter(or_(
            CustomModel.name.ilike(like_pattern),
            CustomModel.base_model.ilike(like_pattern),
            CustomModel.description.ilike(like_pattern),
            User.username.ilike(like_pattern)
        ))
        external_query = external_query.filter(or_(
            ExternalModel.name.ilike(like_pattern),
            ExternalModel.model_name.ilike(like_pattern),
            ExternalModel.description.ilike(like_pattern),
            User.username.ilike(like_pattern)
        ))

    items = []
    for model, owner in custom_query.all():
        item = model.to_dict(include_knowledge=True)
        item['type'] = 'local'
        item['owner_username'] = owner.username if owner else ''
        item['owner_email'] = owner.email if owner else ''
        items.append(item)

    for model, owner in external_query.all():
        item = model.to_dict(include_knowledge=True)
        item['type'] = 'external'
        item['owner_username'] = owner.username if owner else ''
        item['owner_email'] = owner.email if owner else ''
        items.append(item)

    items.sort(key=lambda x: x.get('updated_at') or x.get('created_at') or '', reverse=True)
    return success_response(data=items)


@admin_bp.route('/workspace/custom-models/<model_id>', methods=['PUT'])
@admin_required
def update_admin_custom_model(model_id):
    """Admin update for local custom model."""
    model = CustomModel.query.get(model_id)
    if not model:
        return error_response(404, 'Custom model not found')

    data = request.get_json() or {}
    if 'name' in data:
        model.name = (data.get('name') or '').strip() or model.name
    if 'base_model' in data:
        model.base_model = (data.get('base_model') or '').strip() or model.base_model
    if 'system_prompt' in data:
        model.system_prompt = data.get('system_prompt') or ''
    if 'description' in data:
        model.description = data.get('description') or ''
    if 'is_system' in data:
        model.is_system = bool(data.get('is_system'))

    try:
        db.session.commit()
        return success_response(data=model.to_dict(include_knowledge=True), message='Model updated')
    except Exception as e:
        db.session.rollback()
        return error_response(400, str(e))


@admin_bp.route('/workspace/external-models/<model_id>', methods=['PUT'])
@admin_required
def update_admin_external_model(model_id):
    """Admin update for external model."""
    model = ExternalModel.query.get(model_id)
    if not model:
        return error_response(404, 'External model not found')

    data = request.get_json() or {}
    if 'name' in data:
        model.name = (data.get('name') or '').strip() or model.name
    if 'model_name' in data:
        model.model_name = (data.get('model_name') or '').strip() or model.model_name
    if 'api_base_url' in data:
        model.api_base_url = (data.get('api_base_url') or '').strip() or model.api_base_url
    if data.get('api_key'):
        model.api_key = data['api_key']
    if 'system_prompt' in data:
        model.system_prompt = data.get('system_prompt') or ''
    if 'description' in data:
        model.description = data.get('description') or ''
    if 'is_system' in data:
        model.is_system = bool(data.get('is_system'))

    try:
        db.session.commit()
        return success_response(data=model.to_dict(include_knowledge=True), message='External model updated')
    except Exception as e:
        db.session.rollback()
        return error_response(400, str(e))
