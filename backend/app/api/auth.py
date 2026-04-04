"""
Authentication API Routes
"""
from flask import request
from flask_jwt_extended import (
    create_access_token, 
    jwt_required, 
    get_jwt_identity,
    get_jwt
)
from . import auth_bp
from ..utils.response import success_response, error_response
from ..services.auth_service import AuthService


@auth_bp.route('/register', methods=['POST'])
def register():
    """User registration"""
    data = request.get_json()
    
    if not data:
        return error_response(400, 'No data provided')
    
    username = data.get('username', '').strip()
    email = data.get('email', '').strip()
    password = data.get('password', '')
    
    if not username or not email or not password:
        return error_response(400, 'Username, email and password are required')
    
    if len(password) < 6:
        return error_response(400, 'Password must be at least 6 characters')
    
    result = AuthService.register(username, email, password)
    if result['success']:
        return success_response(result['data'], 'Registration successful', 201)
    return error_response(400, result['message'])


@auth_bp.route('/login', methods=['POST'])
def login():
    """User login"""
    data = request.get_json()
    
    if not data:
        return error_response(400, 'No data provided')
    
    username = data.get('username', '').strip()
    password = data.get('password', '')
    
    if not username or not password:
        return error_response(400, 'Username and password are required')
    
    result = AuthService.login(username, password)
    if result['success']:
        user = result['data']
        access_token = create_access_token(identity=user['id'])
        return success_response({
            'token': access_token,
            'user': user
        }, 'Login successful')
    return error_response(401, result['message'])


@auth_bp.route('/logout', methods=['POST'])
@jwt_required()
def logout():
    """User logout"""
    from ..extensions import get_redis
    
    jti = get_jwt()['jti']
    redis_client = get_redis()
    if redis_client:
        # Add token to blocklist with expiration
        redis_client.setex(f"token:blocklist:{jti}", 86400, "1")
    
    return success_response(message='Logout successful')


@auth_bp.route('/me', methods=['GET'])
@jwt_required()
def get_current_user():
    """Get current user info"""
    user_id = get_jwt_identity()
    result = AuthService.get_user_by_id(user_id)
    
    if result['success']:
        return success_response(result['data'])
    return error_response(404, result['message'])


@auth_bp.route('/me', methods=['PUT'])
@jwt_required()
def update_current_user():
    """Update current user info"""
    user_id = get_jwt_identity()
    data = request.get_json()
    
    result = AuthService.update_user(user_id, data)
    if result['success']:
        return success_response(result['data'], 'User updated successfully')
    return error_response(400, result['message'])
