"""
Flask Extensions Initialization
"""
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_jwt_extended import JWTManager
from flask_cors import CORS
import redis
from celery import Celery

# Initialize extensions
db = SQLAlchemy()
migrate = Migrate()
jwt = JWTManager()
cors = CORS()

# Redis client (initialized later)
redis_client = None

# Celery instance (initialized later)
celery = Celery()


def init_redis(app):
    """Initialize Redis client"""
    global redis_client
    redis_client = redis.Redis(
        host=app.config['REDIS_HOST'],
        port=app.config['REDIS_PORT'],
        db=app.config['REDIS_DB'],
        password=app.config['REDIS_PASSWORD'] or None,
        decode_responses=True
    )
    return redis_client


def init_celery(app):
    """Initialize Celery"""
    celery.conf.update(
        broker_url=app.config['CELERY_BROKER_URL'],
        result_backend=app.config['CELERY_RESULT_BACKEND'],
        task_serializer='json',
        accept_content=['json'],
        result_serializer='json',
        timezone='Asia/Shanghai',
        enable_utc=True,
    )
    
    class ContextTask(celery.Task):
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)
    
    celery.Task = ContextTask
    return celery


def get_redis():
    """Get Redis client with connection check"""
    global redis_client
    if redis_client is None:
        return None
    try:
        # Test connection
        redis_client.ping()
        return redis_client
    except (redis.exceptions.ConnectionError, redis.exceptions.TimeoutError):
        return None
