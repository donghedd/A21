"""
Authentication Service
"""
from ..models import User
from ..extensions import db


class AuthService:
    """Authentication service for user management"""
    
    @staticmethod
    def register(username, email, password):
        """Register a new user"""
        # Check if username exists
        if User.query.filter_by(username=username).first():
            return {'success': False, 'message': 'Username already exists'}
        
        # Check if email exists
        if User.query.filter_by(email=email).first():
            return {'success': False, 'message': 'Email already exists'}
        
        try:
            user = User(username=username, email=email)
            user.set_password(password)
            
            db.session.add(user)
            db.session.commit()
            
            return {
                'success': True,
                'data': user.to_dict(include_email=True)
            }
        except Exception as e:
            db.session.rollback()
            return {'success': False, 'message': str(e)}
    
    @staticmethod
    def login(username, password):
        """Login user"""
        # Find user by username or email
        user = User.query.filter(
            (User.username == username) | (User.email == username)
        ).first()
        
        if not user:
            return {'success': False, 'message': 'User not found'}
        
        if not user.check_password(password):
            return {'success': False, 'message': 'Invalid password'}
        
        return {
            'success': True,
            'data': user.to_dict(include_email=True)
        }
    
    @staticmethod
    def get_user_by_id(user_id):
        """Get user by ID"""
        user = User.query.get(user_id)
        if not user:
            return {'success': False, 'message': 'User not found'}
        
        return {
            'success': True,
            'data': user.to_dict(include_email=True)
        }
    
    @staticmethod
    def update_user(user_id, data):
        """Update user information"""
        user = User.query.get(user_id)
        if not user:
            return {'success': False, 'message': 'User not found'}
        
        try:
            if 'username' in data and data['username']:
                # Check if new username is taken
                existing = User.query.filter_by(username=data['username']).first()
                if existing and existing.id != user_id:
                    return {'success': False, 'message': 'Username already taken'}
                user.username = data['username']
            
            if 'email' in data and data['email']:
                # Check if new email is taken
                existing = User.query.filter_by(email=data['email']).first()
                if existing and existing.id != user_id:
                    return {'success': False, 'message': 'Email already taken'}
                user.email = data['email']
            
            if 'avatar' in data:
                user.avatar = data['avatar']
            
            if 'password' in data and data['password']:
                if len(data['password']) < 6:
                    return {'success': False, 'message': 'Password must be at least 6 characters'}
                user.set_password(data['password'])
            
            db.session.commit()
            
            return {
                'success': True,
                'data': user.to_dict(include_email=True)
            }
        except Exception as e:
            db.session.rollback()
            return {'success': False, 'message': str(e)}
