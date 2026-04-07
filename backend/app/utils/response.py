"""
Unified Response Helper
"""
from flask import jsonify


def success_response(data=None, message='Success', code=200):
    """Return success response"""
    response = {
        'success': True,
        'code': code,
        'message': message,
    }
    if data is not None:
        response['data'] = data
    return jsonify(response), code


def error_response(code=400, message='Error', errors=None):
    """Return error response"""
    response = {
        'success': False,
        'code': code,
        'message': message,
    }
    if errors:
        response['errors'] = errors
    return jsonify(response), code


def paginate_response(items, total, page, per_page, message='Success'):
    """Return paginated response"""
    return success_response(
        data={
            'items': items,
            'pagination': {
                'total': total,
                'page': page,
                'per_page': per_page,
                'pages': (total + per_page - 1) // per_page
            }
        },
        message=message
    )
