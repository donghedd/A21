"""
Custom Decorators
"""
from functools import wraps
from flask import jsonify
from flask_jwt_extended import get_jwt_identity, verify_jwt_in_request
from ..models import User


def admin_required(fn):
    """Decorator to require admin role"""
    @wraps(fn)
    def wrapper(*args, **kwargs):
        verify_jwt_in_request()
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        if not user or user.role != 'admin':
            return jsonify({
                'success': False,
                'code': 403,
                'message': 'Admin access required'
            }), 403
        return fn(*args, **kwargs)
    return wrapper


def get_current_user():
    """Get current user from JWT token"""
    user_id = get_jwt_identity()
    if user_id:
        return User.query.get(user_id)
    return None
