"""
Embedding Service - Ollama Integration
"""
import requests
from typing import List
from flask import current_app
import logging

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Service for generating embeddings using Ollama"""
    
    def __init__(self, base_url: str = None, model: str = None, batch_size: int = 32):
        self.base_url = base_url or current_app.config.get('OLLAMA_BASE_URL', 'http://localhost:11434')
        self.model = model or current_app.config.get('OLLAMA_EMBEDDING_MODEL', 'nomic-embed-text')
        self.batch_size = batch_size or current_app.config.get('EMBEDDING_BATCH_SIZE', 32)
    
    def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for a single text.
        Tries /api/embed (new Ollama API) first, falls back to /api/embeddings (legacy).
        """
        try:
            # Try new Ollama API endpoint first: /api/embed
            response = requests.post(
                f"{self.base_url}/api/embed",
                json={
                    "model": self.model,
                    "input": text
                },
                timeout=60
            )
            
            if response.status_code == 404:
                # Fall back to legacy /api/embeddings endpoint
                logger.info("Falling back to legacy /api/embeddings endpoint")
                response = requests.post(
                    f"{self.base_url}/api/embeddings",
                    json={
                        "model": self.model,
                        "prompt": text
                    },
                    timeout=60
                )
                response.raise_for_status()
                result = response.json()
                return result.get('embedding', [])
            
            response.raise_for_status()
            result = response.json()
            # /api/embed returns {"embeddings": [[...]]} for single input
            embeddings = result.get('embeddings', [])
            if embeddings and isinstance(embeddings[0], list):
                return embeddings[0]
            return embeddings
        except Exception as e:
            logger.error(f"Embedding generation failed: {e}")
            raise
    
    def _batch_embed(self, texts: List[str]) -> List[List[float]]:
        """Call Ollama /api/embed with batch input (supports list of strings)."""
        try:
            response = requests.post(
                f"{self.base_url}/api/embed",
                json={"model": self.model, "input": texts},
                timeout=120
            )
            if response.status_code == 404:
                # Fallback: legacy endpoint does not support batch, embed one by one
                logger.info("Batch embed not available, falling back to single embed")
                return [self.generate_embedding(t) for t in texts]
            response.raise_for_status()
            result = response.json()
            embeddings = result.get('embeddings', [])
            return embeddings
        except Exception as e:
            logger.error(f"Batch embedding failed: {e}")
            raise

    def generate_embeddings(self, texts: List[str], progress_callback=None) -> List[List[float]]:
        """Generate embeddings for multiple texts in batches (using Ollama batch API)"""
        embeddings = []
        total = len(texts)
        
        for i in range(0, total, self.batch_size):
            batch_raw = texts[i:i + self.batch_size]
            # Clean texts
            batch = []
            for text in batch_raw:
                clean = text.replace('\n', ' ').strip()
                batch.append(clean if clean else " ")
            
            batch_embeddings = self._batch_embed(batch)
            embeddings.extend(batch_embeddings)
            
            done = min(i + self.batch_size, total)
            if progress_callback:
                progress_callback(done / total, done, total)
            
            logger.info(f"Generated embeddings: {done}/{total}")
        
        return embeddings
    
    @staticmethod
    def get_instance(base_url: str = None, model: str = None, batch_size: int = None):
        """Get a new EmbeddingService instance with optional overrides"""
        return EmbeddingService(base_url, model, batch_size)


def get_embedding_service() -> EmbeddingService:
    """Get embedding service instance"""
    return EmbeddingService(
        base_url=current_app.config.get('OLLAMA_BASE_URL'),
        model=current_app.config.get('OLLAMA_EMBEDDING_MODEL'),
        batch_size=current_app.config.get('EMBEDDING_BATCH_SIZE', 32)
    )
