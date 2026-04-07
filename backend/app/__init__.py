"""
SFQA - Smart FAQ Application
Flask Application Factory
"""
import os
from flask import Flask
from .config import config
from .extensions import db, migrate, jwt, cors, init_redis, init_celery


def create_app(config_name=None):
    """Application factory pattern"""
    if config_name is None:
        config_name = os.getenv('FLASK_ENV', 'development')
    
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    
    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    cors.init_app(app, resources={
        r"/api/*": {
            "origins": "*",
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization"]
        }
    })
    
    # Initialize Redis
    try:
        init_redis(app)
    except Exception as e:
        app.logger.warning(f"Redis connection failed: {e}")
    
    # Initialize Celery
    init_celery(app)
    
    # Ensure directories exist
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs(app.config['CHROMA_PERSIST_DIRECTORY'], exist_ok=True)
    
    # Register blueprints
    register_blueprints(app)
    
    # Register error handlers
    register_error_handlers(app)
    
    # JWT callbacks
    register_jwt_callbacks(app)
    
    return app


def register_blueprints(app):
    """Register all blueprints"""
    from .api import auth_bp, chat_bp, model_bp, knowledge_bp, file_bp
    
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(chat_bp, url_prefix='/api/chat')
    app.register_blueprint(model_bp, url_prefix='/api/models')
    app.register_blueprint(knowledge_bp, url_prefix='/api/knowledge')
    app.register_blueprint(file_bp, url_prefix='/api/files')


def register_error_handlers(app):
    """Register error handlers"""
    from .utils.response import error_response
    
    @app.errorhandler(400)
    def bad_request(e):
        return error_response(400, str(e.description))
    
    @app.errorhandler(401)
    def unauthorized(e):
        return error_response(401, 'Unauthorized')
    
    @app.errorhandler(403)
    def forbidden(e):
        return error_response(403, 'Forbidden')
    
    @app.errorhandler(404)
    def not_found(e):
        return error_response(404, 'Resource not found')
    
    @app.errorhandler(500)
    def internal_error(e):
        return error_response(500, 'Internal server error')


def register_jwt_callbacks(app):
    """Register JWT callbacks"""
    from .extensions import get_redis
    
    @jwt.token_in_blocklist_loader
    def check_if_token_revoked(jwt_header, jwt_payload):
        """Check if token is in blocklist (logout)"""
        jti = jwt_payload['jti']
        redis_client = get_redis()
        if redis_client:
            token_in_redis = redis_client.get(f"token:blocklist:{jti}")
            return token_in_redis is not None
        return False
    
    @jwt.expired_token_loader
    def expired_token_callback(jwt_header, jwt_payload):
        from .utils.response import error_response
        return error_response(401, 'Token has expired')
    
    @jwt.invalid_token_loader
    def invalid_token_callback(error):
        from .utils.response import error_response
        return error_response(401, 'Invalid token')
    
    @jwt.unauthorized_loader
    def missing_token_callback(error):
        from .utils.response import error_response
        return error_response(401, 'Authorization token is missing')
