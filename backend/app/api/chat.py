"""Chat API Routes - Conversation and Messaging
"""
from flask import request, Response, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
import json
from . import chat_bp
from ..utils.response import success_response, error_response
from ..services import get_chat_service


# ==================== Conversation Endpoints ====================

@chat_bp.route('/conversations', methods=['GET'])
@jwt_required()
def get_conversations():
    """Get user's conversation list with pagination"""
    user_id = get_jwt_identity()
    
    search = request.args.get('search', '')
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    chat_service = get_chat_service()
    result = chat_service.get_conversations(
        user_id=user_id,
        search=search,
        page=page,
        per_page=per_page
    )
    
    return success_response(data=result)


@chat_bp.route('/conversations', methods=['POST'])
@jwt_required()
def create_conversation():
    """Create a new conversation"""
    user_id = get_jwt_identity()
    data = request.get_json() or {}
    
    title = data.get('title')
    custom_model_id = data.get('custom_model_id')
    external_model_id = data.get('external_model_id')
    
    chat_service = get_chat_service()
    conversation = chat_service.create_conversation(
        user_id=user_id,
        title=title,
        custom_model_id=custom_model_id,
        external_model_id=external_model_id
    )
    
    return success_response(
        data=conversation.to_dict(),
        message='Conversation created successfully',
        code=201
    )


@chat_bp.route('/conversations/<conversation_id>', methods=['GET'])
@jwt_required()
def get_conversation(conversation_id):
    """Get conversation details with messages"""
    user_id = get_jwt_identity()
    
    chat_service = get_chat_service()
    conversation = chat_service.get_conversation(conversation_id, user_id)
    
    if not conversation:
        return error_response(404, 'Conversation not found')
    
    return success_response(data=conversation.to_dict(include_messages=True))


@chat_bp.route('/conversations/<conversation_id>', methods=['PUT'])
@jwt_required()
def update_conversation(conversation_id):
    """Update conversation details"""
    user_id = get_jwt_identity()
    data = request.get_json() or {}
    
    chat_service = get_chat_service()
    conversation = chat_service.update_conversation(
        conversation_id=conversation_id,
        user_id=user_id,
        title=data.get('title'),
        custom_model_id=data.get('custom_model_id'),
        external_model_id=data.get('external_model_id')
    )
    
    if not conversation:
        return error_response(404, 'Conversation not found')
    
    return success_response(
        data=conversation.to_dict(),
        message='Conversation updated successfully'
    )


@chat_bp.route('/conversations/<conversation_id>', methods=['DELETE'])
@jwt_required()
def delete_conversation(conversation_id):
    """Delete a conversation"""
    user_id = get_jwt_identity()
    
    chat_service = get_chat_service()
    success = chat_service.delete_conversation(conversation_id, user_id)
    
    if not success:
        return error_response(404, 'Conversation not found')
    
    return success_response(message='Conversation deleted successfully')


@chat_bp.route('/conversations/<conversation_id>/copy', methods=['POST'])
@jwt_required()
def copy_conversation(conversation_id):
    """Copy a conversation with all messages"""
    user_id = get_jwt_identity()
    
    chat_service = get_chat_service()
    new_conversation = chat_service.copy_conversation(conversation_id, user_id)
    
    if not new_conversation:
        return error_response(404, 'Original conversation not found')
    
    return success_response(
        data=new_conversation.to_dict(),
        message='Conversation copied successfully',
        code=201
    )


# ==================== Messaging Endpoints ====================

@chat_bp.route('/conversations/<conversation_id>/messages', methods=['POST'])
@jwt_required()
def send_message(conversation_id):
    """
    Send a message and get streaming response.
    Returns Server-Sent Events (SSE) stream.
    
    SSE Event Types:
    - status: Processing status update
    - sources: RAG retrieved sources
    - thinking_start: Start of thinking process
    - thinking: AI thinking process content
    - thinking_end: End of thinking with duration
    - content: Response content token
    - done: Completion signal with metadata
    - error: Error message
    """
    user_id = get_jwt_identity()
    data = request.get_json()

    if not data or not data.get('content'):
        return error_response(400, 'Message content is required')

    user_message = data['content']
    model = data.get('model')  # Optional model override
    custom_model_id = data.get('custom_model_id')  # Optional custom model
    external_model_id = data.get('external_model_id')

    # 调试日志
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"=== API收到消息 ===")
    logger.info(f"用户消息: {user_message[:50]}...")
    logger.info(f"model参数: {model}")
    logger.info(f"custom_model_id参数: {custom_model_id}")
    logger.info(f"external_model_id参数: {external_model_id}")

    chat_service = get_chat_service()
    app = current_app._get_current_object()
    
    def generate():
        with app.app_context():
            for event in chat_service.chat_stream(
                conversation_id=conversation_id,
                user_id=user_id,
                user_message=user_message,
                model=model,
                custom_model_id=custom_model_id,
                external_model_id=external_model_id
            ):
                yield event
    
    return Response(
        generate(),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'X-Accel-Buffering': 'no'
        }
    )


@chat_bp.route('/conversations/<conversation_id>/messages/<message_id>', methods=['DELETE'])
@jwt_required()
def delete_messages_from(conversation_id, message_id):
    """Delete a message and all subsequent messages (for edit/resend)"""
    user_id = get_jwt_identity()
    
    chat_service = get_chat_service()
    result = chat_service.delete_messages_from(conversation_id, user_id, message_id)
    
    if result is None:
        return error_response(404, 'Message or conversation not found')
    
    return success_response(
        data=result,
        message='Messages deleted successfully'
    )


@chat_bp.route('/conversations/<conversation_id>/regenerate', methods=['POST'])
@jwt_required()
def regenerate_response(conversation_id):
    """
    Regenerate the last assistant response.
    Returns Server-Sent Events (SSE) stream.
    """
    user_id = get_jwt_identity()
    data = request.get_json() or {}
    model = data.get('model')
    custom_model_id = data.get('custom_model_id')  # Optional custom model
    external_model_id = data.get('external_model_id')
    
    chat_service = get_chat_service()
    app = current_app._get_current_object()
    
    def generate():
        with app.app_context():
            for event in chat_service.regenerate_response(
                conversation_id=conversation_id,
                user_id=user_id,
                model=model,
                custom_model_id=custom_model_id,
                external_model_id=external_model_id
            ):
                yield event
    
    return Response(
        generate(),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'X-Accel-Buffering': 'no'
        }
    )


# ==================== Search Endpoint ====================

@chat_bp.route('/conversations/search', methods=['GET'])
@jwt_required()
def search_conversations():
    """Full-text search in conversations"""
    user_id = get_jwt_identity()
    
    query = request.args.get('q', '')
    if not query:
        return error_response(400, 'Search query is required')
    
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    chat_service = get_chat_service()
    result = chat_service.search_conversations(
        user_id=user_id,
        query=query,
        page=page,
        per_page=per_page
    )
    
    return success_response(data=result)


# ==================== Export Endpoint ====================

@chat_bp.route('/conversations/<conversation_id>/export', methods=['GET'])
@jwt_required()
def export_conversation(conversation_id):
    """
    Export conversation in specified format.
    Supported formats: json, txt, markdown
    """
    user_id = get_jwt_identity()
    
    format_type = request.args.get('format', 'json')
    if format_type not in ('json', 'txt', 'markdown'):
        return error_response(400, 'Invalid format. Supported: json, txt, markdown')
    
    chat_service = get_chat_service()
    result = chat_service.export_conversation(
        conversation_id=conversation_id,
        user_id=user_id,
        format=format_type
    )
    
    if not result:
        return error_response(404, 'Conversation not found')
    
    if format_type == 'json':
        return success_response(data=result)
    else:
        return Response(
            result['content'],
            mimetype='text/plain',
            headers={
                'Content-Disposition': f'attachment; filename="{result["filename"]}"'
            }
        )
