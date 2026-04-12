"""
SFQA - Smart FAQ Application
Flask Application Factory
"""
import os
from flask import Flask
from sqlalchemy import inspect, text
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

    # Ensure optional schema changes exist for incremental upgrades
    ensure_schema_updates(app)
    
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


def ensure_schema_updates(app):
    """Apply lightweight non-destructive schema upgrades for new optional features."""
    try:
        with app.app_context():
            from . import models  # noqa: F401

            db.create_all()

            inspector = inspect(db.engine)
            if 'users' in inspector.get_table_names():
                user_columns = {column['name'] for column in inspector.get_columns('users')}
                if 'last_login_at' not in user_columns:
                    with db.engine.begin() as conn:
                        conn.execute(text(
                            'ALTER TABLE users '
                            'ADD COLUMN last_login_at DATETIME NULL'
                        ))
                        conn.execute(text(
                            'ALTER TABLE users '
                            'ADD INDEX idx_last_login_at (last_login_at)'
                        ))

            if 'conversations' not in inspector.get_table_names():
                return

            conversation_columns = {column['name'] for column in inspector.get_columns('conversations')}
            if 'deleted_by_user' not in conversation_columns:
                with db.engine.begin() as conn:
                    conn.execute(text(
                        'ALTER TABLE conversations '
                        'ADD COLUMN deleted_by_user BOOLEAN NOT NULL DEFAULT FALSE'
                    ))
                    conn.execute(text(
                        'ALTER TABLE conversations '
                        'ADD INDEX idx_deleted_by_user (deleted_by_user)'
                    ))

            if 'external_model_id' in conversation_columns:
                return

            with db.engine.begin() as conn:
                conn.execute(text(
                    'ALTER TABLE conversations '
                    'ADD COLUMN external_model_id VARCHAR(36) NULL'
                ))
                conn.execute(text(
                    'ALTER TABLE conversations '
                    'ADD INDEX idx_external_model_id (external_model_id)'
                ))
                conn.execute(text(
                    'ALTER TABLE conversations '
                    'ADD CONSTRAINT fk_conversations_external_model '
                    'FOREIGN KEY (external_model_id) REFERENCES external_models(id) '
                    'ON DELETE SET NULL'
                ))
    except Exception as e:
        app.logger.warning(f"Schema update skipped: {e}")


def register_blueprints(app):
    """Register all blueprints"""
    from .api import auth_bp, chat_bp, model_bp, knowledge_bp, file_bp, admin_bp, kg_bp
    
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(chat_bp, url_prefix='/api/chat')
    app.register_blueprint(model_bp, url_prefix='/api/models')
    app.register_blueprint(knowledge_bp, url_prefix='/api/knowledge')
    app.register_blueprint(file_bp, url_prefix='/api/files')
    app.register_blueprint(admin_bp, url_prefix='/api/admin')
    app.register_blueprint(kg_bp, url_prefix='/api/kg')


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
