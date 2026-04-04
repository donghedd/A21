"""
Vector Database Service - ChromaDB Integration
"""
import uuid
from typing import List, Dict, Any, Optional
from flask import current_app
import chromadb
from chromadb.config import Settings
import logging

logger = logging.getLogger(__name__)

# Global client instance
_chroma_client = None


def get_chroma_client():
    """Get or create ChromaDB client"""
    global _chroma_client
    
    if _chroma_client is None:
        persist_dir = current_app.config.get('CHROMA_PERSIST_DIRECTORY', 'vector_db')
        _chroma_client = chromadb.PersistentClient(
            path=persist_dir,
            settings=Settings(anonymized_telemetry=False)
        )
    
    return _chroma_client


class VectorService:
    """Service for managing vector database operations"""
    
    def __init__(self):
        self.client = get_chroma_client()
    
    def create_collection(self, collection_name: str, metadata: dict = None) -> Any:
        """Create a new collection"""
        try:
            kwargs = {"name": collection_name}
            if metadata:
                kwargs["metadata"] = metadata
            collection = self.client.create_collection(**kwargs)
            logger.info(f"Created collection: {collection_name}")
            return collection
        except Exception as e:
            logger.error(f"Failed to create collection: {e}")
            raise
    
    def get_or_create_collection(self, collection_name: str, metadata: dict = None) -> Any:
        """Get existing collection or create new one"""
        try:
            kwargs = {"name": collection_name}
            if metadata:
                kwargs["metadata"] = metadata
            collection = self.client.get_or_create_collection(**kwargs)
            return collection
        except Exception as e:
            logger.error(f"Failed to get/create collection: {e}")
            raise
    
    def delete_collection(self, collection_name: str):
        """Delete a collection"""
        try:
            self.client.delete_collection(name=collection_name)
            logger.info(f"Deleted collection: {collection_name}")
        except Exception as e:
            logger.warning(f"Failed to delete collection {collection_name}: {e}")
    
    def add_documents(self, collection_name: str, documents: List[str], 
                      embeddings: List[List[float]], metadatas: List[dict] = None,
                      ids: List[str] = None):
        """Add documents to collection"""
        collection = self.get_or_create_collection(collection_name)
        
        if ids is None:
            ids = [str(uuid.uuid4()) for _ in range(len(documents))]
        
        if metadatas is None:
            metadatas = [{"_placeholder": "true"} for _ in range(len(documents))]
        
        try:
            collection.add(
                documents=documents,
                embeddings=embeddings,
                metadatas=metadatas,
                ids=ids
            )
            logger.info(f"Added {len(documents)} documents to {collection_name}")
        except Exception as e:
            logger.error(f"Failed to add documents: {e}")
            raise
    
    def query(self, collection_name: str, query_embedding: List[float], 
              n_results: int = 10, where: dict = None) -> Dict[str, Any]:
        """Query collection for similar documents"""
        try:
            collection = self.client.get_collection(name=collection_name)
            
            results = collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results,
                where=where,
                include=['documents', 'metadatas', 'distances']
            )
            
            return {
                'ids': results['ids'][0] if results['ids'] else [],
                'documents': results['documents'][0] if results['documents'] else [],
                'metadatas': results['metadatas'][0] if results['metadatas'] else [],
                'distances': results['distances'][0] if results['distances'] else []
            }
        except Exception as e:
            logger.error(f"Query failed: {e}")
            return {'ids': [], 'documents': [], 'metadatas': [], 'distances': []}
    
    def get_collection_count(self, collection_name: str) -> int:
        """Get number of documents in collection"""
        try:
            collection = self.client.get_collection(name=collection_name)
            return collection.count()
        except Exception:
            return 0
    
    def collection_exists(self, collection_name: str) -> bool:
        """Check if collection exists"""
        try:
            collections = self.client.list_collections()
            return any(c.name == collection_name for c in collections)
        except Exception:
            return False
    
    def delete_by_metadata(self, collection_name: str, where: dict):
        """Delete documents by metadata filter"""
        try:
            collection = self.client.get_collection(name=collection_name)
            # Get matching IDs first
            results = collection.get(where=where)
            if results['ids']:
                collection.delete(ids=results['ids'])
                logger.info(f"Deleted {len(results['ids'])} documents from {collection_name}")
        except Exception as e:
            logger.error(f"Failed to delete by metadata: {e}")


def get_vector_service() -> VectorService:
    """Get vector service instance"""
    return VectorService()
