"""
Flask Configuration Classes
"""
import os
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Base configuration"""
    # Flask
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key')
    
    # JWT
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'jwt-secret-key')
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(
        seconds=int(os.getenv('JWT_ACCESS_TOKEN_EXPIRES', 86400))
    )
    JWT_TOKEN_LOCATION = ['headers']
    JWT_HEADER_NAME = 'Authorization'
    JWT_HEADER_TYPE = 'Bearer'
    
    # MySQL Database
    MYSQL_HOST = os.getenv('MYSQL_HOST', 'localhost')
    MYSQL_PORT = int(os.getenv('MYSQL_PORT', 3306))
    MYSQL_USER = os.getenv('MYSQL_USER', 'root')
    MYSQL_PASSWORD = os.getenv('MYSQL_PASSWORD', '')
    MYSQL_DATABASE = os.getenv('MYSQL_DATABASE', 'sfqa_db')
    
    SQLALCHEMY_DATABASE_URI = (
        f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}@"
        f"{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DATABASE}?charset=utf8mb4"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = False
    
    # Redis
    REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
    REDIS_PORT = int(os.getenv('REDIS_PORT', 6379))
    REDIS_DB = int(os.getenv('REDIS_DB', 0))
    REDIS_PASSWORD = os.getenv('REDIS_PASSWORD', None)
    
    # Celery
    CELERY_BROKER_URL = os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379/1')
    CELERY_RESULT_BACKEND = os.getenv('CELERY_RESULT_BACKEND', 'redis://localhost:6379/2')
    
    # LLM Provider
    LLM_PROVIDER = os.getenv('LLM_PROVIDER', 'ollama').lower()

    # Ollama
    OLLAMA_BASE_URL = os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')
    OLLAMA_EMBEDDING_MODEL = os.getenv('OLLAMA_EMBEDDING_MODEL', 'nomic-embed-text')
    OLLAMA_DEFAULT_MODEL = os.getenv('OLLAMA_DEFAULT_MODEL', 'qwen2.5:7b')

    # llama.cpp
    LLAMACPP_BASE_URL = os.getenv('LLAMACPP_BASE_URL', 'http://localhost:8080')
    LLAMACPP_MODEL_PATH = os.getenv('LLAMACPP_MODEL_PATH', 'models/llama-model.gguf')
    LLAMACPP_N_CTX = int(os.getenv('LLAMACPP_N_CTX', '4096'))
    LLAMACPP_N_THREADS = int(os.getenv('LLAMACPP_N_THREADS', '4'))
    LLAMACPP_N_BATCH = int(os.getenv('LLAMACPP_N_BATCH', '512'))
    
    # RAG Configuration
    CHUNK_SIZE = int(os.getenv('CHUNK_SIZE', 800))
    CHUNK_OVERLAP = int(os.getenv('CHUNK_OVERLAP', 120))
    CHUNK_MIN_SIZE = int(os.getenv('CHUNK_MIN_SIZE', 160))
    EMBEDDING_BATCH_SIZE = int(os.getenv('EMBEDDING_BATCH_SIZE', 32))
    
    # RAG Search Configuration
    RELEVANCE_THRESHOLD = float(os.getenv('RELEVANCE_THRESHOLD', 0.3))
    ENABLE_HYBRID_SEARCH = os.getenv('ENABLE_HYBRID_SEARCH', 'true').lower() == 'true'
    HYBRID_BM25_WEIGHT = float(os.getenv('HYBRID_BM25_WEIGHT', 0.3))
    
    # Multi-source RAG Configuration (Reference: Open-WebUI)
    RAG_TOP_K = int(os.getenv('RAG_TOP_K', 12))  # Increase recall for title-style technical questions
    RAG_TOP_K_RERANKER = int(os.getenv('RAG_TOP_K_RERANKER', 5))  # 重排序后保留数量
    RAG_ENABLE_MULTI_SOURCE = os.getenv('RAG_ENABLE_MULTI_SOURCE', 'true').lower() == 'true'
    RAG_MAX_CHUNKS_PER_FILE = int(os.getenv('RAG_MAX_CHUNKS_PER_FILE', 5))  # Allow more evidence from same file
    RAG_MIN_FILES = int(os.getenv('RAG_MIN_FILES', 1))  # Don't force multi-file recall for exact questions
    RAG_ENABLE_KG_FUSION = os.getenv('RAG_ENABLE_KG_FUSION', 'true').lower() == 'true'
    RAG_FUSION_DOCUMENT_LIMIT = int(os.getenv('RAG_FUSION_DOCUMENT_LIMIT', 12))
    RAG_FUSION_DOCUMENT_WEIGHT = float(os.getenv('RAG_FUSION_DOCUMENT_WEIGHT', 1.0))
    RAG_FUSION_KG_WEIGHT = float(os.getenv('RAG_FUSION_KG_WEIGHT', 1.0))
    RAG_FUSION_MAX_KG_RESULTS = int(os.getenv('RAG_FUSION_MAX_KG_RESULTS', 3))
    
    # File Upload
    MAX_CONTENT_LENGTH = int(os.getenv('MAX_CONTENT_LENGTH', 50 * 1024 * 1024))
    UPLOAD_FOLDER = os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        os.getenv('UPLOAD_FOLDER', 'uploads')
    )
    ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx', 'txt', 'md', 'xlsx', 'xls', 'json'}
    ENABLE_PDF_OCR = os.getenv('ENABLE_PDF_OCR', 'true').lower() == 'true'
    PDF_OCR_DPI = int(os.getenv('PDF_OCR_DPI', 200))
    PDF_OCR_MIN_TEXT_CHARS = int(os.getenv('PDF_OCR_MIN_TEXT_CHARS', 20))
    PDF_OCR_LANGUAGE = os.getenv('PDF_OCR_LANGUAGE', 'chi_sim+eng')
    TESSERACT_CMD = os.getenv('TESSERACT_CMD', '').strip() or None
    
    # Chroma Vector DB
    CHROMA_PERSIST_DIRECTORY = os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        os.getenv('CHROMA_PERSIST_DIRECTORY', 'vector_db')
    )

    # Knowledge Graph Configuration
    KG_ENABLED = os.getenv('KG_ENABLED', 'false').lower() == 'true'
    KG_PROVIDER = os.getenv('KG_PROVIDER', 'neo4j')
    KG_TYPED_OUTPUT_DIR = os.getenv('KG_TYPED_OUTPUT_DIR', 'kg_typed_output')
    KG_RAW_OUTPUT_DIR = os.getenv('KG_RAW_OUTPUT_DIR', 'kg_output')
    KG_EVIDENCE_REQUIRED = os.getenv('KG_EVIDENCE_REQUIRED', 'true').lower() == 'true'
    KG_DEFAULT_EXPAND_DEPTH = int(os.getenv('KG_DEFAULT_EXPAND_DEPTH', 2))
    KG_MAX_EXPAND_DEPTH = int(os.getenv('KG_MAX_EXPAND_DEPTH', 3))
    KG_DEFAULT_NODE_LIMIT = int(os.getenv('KG_DEFAULT_NODE_LIMIT', 120))
    KG_DEFAULT_EDGE_LIMIT = int(os.getenv('KG_DEFAULT_EDGE_LIMIT', 200))
    KG_HIDE_BOOK_BY_DEFAULT = os.getenv('KG_HIDE_BOOK_BY_DEFAULT', 'true').lower() == 'true'
    KG_HIDE_COVERS_BY_DEFAULT = os.getenv('KG_HIDE_COVERS_BY_DEFAULT', 'true').lower() == 'true'
    KG_DEFAULT_VISIBLE_NODE_TYPES = os.getenv(
        'KG_DEFAULT_VISIBLE_NODE_TYPES',
        'Device,Fault,Cause,Symptom,Action,Parameter'
    )
    KG_DEFAULT_VISIBLE_REL_TYPES = os.getenv(
        'KG_DEFAULT_VISIBLE_REL_TYPES',
        'HAS_FAULT,CAUSED_BY,HAS_SYMPTOM,RESOLVED_BY,TARGETS,AFFECTS_PARAMETER,SHOWS_AS,HAS_COMPONENT'
    )
    TECH_KG_MAX_KEYWORD_PAGE_SIZE = int(os.getenv('TECH_KG_MAX_KEYWORD_PAGE_SIZE', 100))
    TECH_KG_MAX_GRAPH_DEPTH = int(os.getenv('TECH_KG_MAX_GRAPH_DEPTH', 3))
    TECH_KG_MAX_GRAPH_NODES = int(os.getenv('TECH_KG_MAX_GRAPH_NODES', 200))
    TECH_KG_MAX_RESOURCE_COUNT = int(os.getenv('TECH_KG_MAX_RESOURCE_COUNT', 30))

    # Neo4j Configuration
    NEO4J_URI = os.getenv('NEO4J_URI', 'bolt://localhost:7687')
    NEO4J_USERNAME = os.getenv('NEO4J_USERNAME', 'neo4j')
    NEO4J_PASSWORD = os.getenv('NEO4J_PASSWORD', 'neo4j')
    NEO4J_DATABASE = os.getenv('NEO4J_DATABASE', 'neo4j')
    KG_CHAT_TOP_K = int(os.getenv('KG_CHAT_TOP_K', 3))
    KG_CHAT_CANDIDATE_MULTIPLIER = int(os.getenv('KG_CHAT_CANDIDATE_MULTIPLIER', 3))
    KG_CHAT_MIN_SCORE = float(os.getenv('KG_CHAT_MIN_SCORE', 0.2))
    KG_CHAT_MAX_RESOURCES_PER_NODE = int(os.getenv('KG_CHAT_MAX_RESOURCES_PER_NODE', 2))

    # Search Enhancement for Knowledge Graph
    KG_SEARCH_BACKEND = os.getenv('KG_SEARCH_BACKEND', 'builtin')
    ELASTICSEARCH_URL = os.getenv('ELASTICSEARCH_URL', 'http://localhost:9200')
    ELASTICSEARCH_INDEX = os.getenv('ELASTICSEARCH_INDEX', 'ship_fault_kg')


class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    SQLALCHEMY_ECHO = True


class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    SQLALCHEMY_ECHO = False


class TestingConfig(Config):
    """Testing configuration"""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'


config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}
