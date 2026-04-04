"""
RAG (Retrieval-Augmented Generation) Service
Enhanced with BM25 hybrid search, reranking, and relevance filtering.
Reference: Open WebUI's retrieval pipeline.
"""
import hashlib
import numpy as np
from typing import List, Dict, Any, Optional
from collections import defaultdict
from flask import current_app
import logging

from .embedding_service import get_embedding_service
from .vector_service import get_vector_service
from ..loaders.base import BaseLoader, Document
from ..utils.text_splitter import split_documents
from ..utils.bm25 import BM25Retriever, reciprocal_rank_fusion

logger = logging.getLogger(__name__)


class RAGService:
    """RAG service for document processing and retrieval"""
    
    def __init__(self):
        self._embedding_service = None
        self._vector_service = None
        self._bm25_retriever = None
    
    @property
    def embedding_service(self):
        if self._embedding_service is None:
            self._embedding_service = get_embedding_service()
        return self._embedding_service
    
    @property
    def vector_service(self):
        if self._vector_service is None:
            self._vector_service = get_vector_service()
        return self._vector_service
    
    @property
    def bm25_retriever(self):
        if self._bm25_retriever is None:
            self._bm25_retriever = BM25Retriever()
        return self._bm25_retriever
    
    def process_file(self, file_path: str, file_type: str, 
                     collection_name: str, file_id: str,
                     original_filename: str = None,
                     progress_callback=None) -> Dict[str, Any]:
        """
        Process a file through the complete RAG pipeline:
        1. Load file content
        2. Split into chunks with enhanced metadata
        3. Generate embeddings
        4. Store in vector database
        """
        try:
            # Use original filename if provided, otherwise fall back to basename
            import os
            file_name = original_filename or os.path.basename(file_path)
            
            # Step 1: Load file
            logger.info(f"Loading file: {file_path}")
            loader = BaseLoader.get_loader_for_file(file_path, file_type)
            documents = loader.load(file_path)
            
            if not documents:
                raise ValueError("No content extracted from file")
            
            # Enrich documents with source file metadata
            for doc in documents:
                doc.metadata['source_file'] = file_name
                doc.metadata['file_name'] = file_name
            
            # Calculate content hash for deduplication
            full_content = '\n'.join([doc.page_content for doc in documents])
            content_hash = hashlib.sha256(full_content.encode()).hexdigest()
            
            # Step 2: Split into chunks
            logger.info("Splitting documents into chunks")
            chunk_size = current_app.config.get('CHUNK_SIZE', 1000)
            chunk_overlap = current_app.config.get('CHUNK_OVERLAP', 200)
            chunk_min_size = current_app.config.get('CHUNK_MIN_SIZE', 200)
            use_markdown_splitter = current_app.config.get('ENABLE_MARKDOWN_HEADER_SPLITTER', True)
            
            logger.info(
                f"Chunk config: size={chunk_size}, overlap={chunk_overlap}, "
                f"min_size={chunk_min_size}, markdown_splitter={use_markdown_splitter}"
            )
            
            chunks = split_documents(
                documents,
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                use_markdown_splitter=use_markdown_splitter,
                min_chunk_size=chunk_min_size
            )
            
            if not chunks:
                raise ValueError("No chunks generated from documents")
            
            logger.info(f"Generated {len(chunks)} chunks")
            
            # Step 3: Generate embeddings
            logger.info("Generating embeddings")
            texts = [chunk.page_content for chunk in chunks]
            
            def embedding_progress(progress, current, total):
                if progress_callback:
                    # Embedding is 70% of total progress
                    progress_callback(0.3 + progress * 0.7, f"Generating embeddings: {current}/{total}")
            
            embeddings = self.embedding_service.generate_embeddings(
                texts, 
                progress_callback=embedding_progress
            )
            
            # Step 4: Prepare enhanced metadata (ChromaDB only supports scalar values)
            metadatas = []
            for i, chunk in enumerate(chunks):
                # Convert section_path list to string for ChromaDB compatibility
                section_path = chunk.metadata.get('section_path', [])
                if isinstance(section_path, list):
                    section_path = ' > '.join(section_path) if section_path else ''
                
                section_title = (chunk.metadata.get('Header 3', '') or 
                                 chunk.metadata.get('Header 2', '') or 
                                 chunk.metadata.get('Header 1', ''))
                
                metadata = {
                    'file_id': file_id,
                    'file_name': file_name,
                    'chunk_index': i,
                    'section_path': section_path,
                    'section_title': section_title,
                    'content_hash': content_hash,
                    'collection': collection_name
                }
                
                # Add only scalar values from chunk metadata (ChromaDB requirement)
                for key, value in chunk.metadata.items():
                    if key not in metadata and isinstance(value, (str, int, float, bool)):
                        metadata[key] = value
                
                metadatas.append(metadata)
            
            # Step 5: Store in vector database
            logger.info(f"Storing {len(chunks)} chunks in collection: {collection_name}")
            self.vector_service.add_documents(
                collection_name=collection_name,
                documents=texts,
                embeddings=embeddings,
                metadatas=metadatas
            )
            
            logger.info(f"Successfully processed file: {file_path}")
            
            # Invalidate BM25 cache since new docs were added
            self.bm25_retriever.invalidate_cache(collection_name)
            
            return {
                'success': True,
                'chunk_count': len(chunks),
                'content_hash': content_hash,
                'collection_name': collection_name
            }
            
        except Exception as e:
            logger.error(f"Failed to process file: {e}")
            raise
    
    def query(self, query: str, collection_names: List[str], 
              n_results: int = None, enable_rerank: bool = True,
              enable_hybrid: bool = None, enable_multi_source: bool = None) -> List[Dict[str, Any]]:
        """
        Query multiple collections for relevant documents.
        Enhanced with BM25 hybrid search, cosine reranking, and multi-source diversity.
        
        Reference: Open WebUI's query_collection with multi-source support
        
        Pipeline:
        1. Vector search (top-K candidates from each collection)
        2. BM25 search (top-K candidates) - if hybrid enabled
        3. RRF fusion of two result sets - if hybrid enabled
        4. Multi-source diversity filtering - ensure results from multiple files
        5. Cosine similarity reranking
        6. Relevance threshold filtering
        
        Args:
            query: Search query
            collection_names: List of collection names to search
            n_results: Number of final results to return (default from config RAG_TOP_K)
            enable_rerank: Whether to enable cosine reranking (default True)
            enable_hybrid: Whether to use BM25 hybrid search (default from config)
            enable_multi_source: Whether to ensure diversity across files (default from config)
        """
        try:
            # Read config
            if n_results is None:
                n_results = current_app.config.get('RAG_TOP_K', 10)
            if enable_hybrid is None:
                enable_hybrid = current_app.config.get('ENABLE_HYBRID_SEARCH', True)
            if enable_multi_source is None:
                enable_multi_source = current_app.config.get('RAG_ENABLE_MULTI_SOURCE', True)
            
            relevance_threshold = current_app.config.get('RELEVANCE_THRESHOLD', 0.3)
            bm25_weight = current_app.config.get('HYBRID_BM25_WEIGHT', 0.3)
            max_per_file = current_app.config.get('RAG_MAX_CHUNKS_PER_FILE', 3)
            min_files = current_app.config.get('RAG_MIN_FILES', 2)
            
            # Generate embedding for query
            query_embedding = self.embedding_service.generate_embedding(query)
            
            # Increase candidate count for better recall and diversity
            # Use larger multiplier to ensure enough candidates for multi-source filtering
            candidate_count = n_results * 5  # Increased from 3 to 5
            
            logger.info(f"Query: '{query[:50]}...' | Collections: {len(collection_names)} | "
                       f"n_results: {n_results} | candidate_count: {candidate_count} | "
                       f"multi_source: {enable_multi_source}")
            
            # ---- Step 1: Vector search ----
            vector_results = []
            for collection_name in collection_names:
                if not self.vector_service.collection_exists(collection_name):
                    continue
                
                results = self.vector_service.query(
                    collection_name=collection_name,
                    query_embedding=query_embedding,
                    n_results=candidate_count
                )
                
                for i, doc in enumerate(results['documents']):
                    vector_results.append({
                        'content': doc,
                        'metadata': results['metadatas'][i] if results['metadatas'] else {},
                        'distance': results['distances'][i] if results['distances'] else 0,
                        'id': results['ids'][i] if results['ids'] else str(i),
                        'collection': collection_name
                    })
            
            # Sort vector results by distance (lower is better)
            vector_results.sort(key=lambda x: x['distance'])
            logger.info(f"Vector search returned {len(vector_results)} results")
            
            # ---- Step 2: BM25 search (if hybrid enabled) ----
            if enable_hybrid:
                bm25_results = []
                for collection_name in collection_names:
                    if not self.vector_service.collection_exists(collection_name):
                        continue
                    bm25_hits = self.bm25_retriever.search(
                        query=query,
                        collection_name=collection_name,
                        vector_service=self.vector_service,
                        n_results=candidate_count
                    )
                    for hit in bm25_hits:
                        hit['collection'] = collection_name
                    bm25_results.extend(bm25_hits)
                
                # ---- Step 3: RRF Fusion ----
                if bm25_results:
                    all_results = reciprocal_rank_fusion(
                        [vector_results, bm25_results], k=60
                    )
                    logger.info(f"Hybrid search: {len(vector_results)} vector + {len(bm25_results)} BM25 -> {len(all_results)} fused")
                else:
                    all_results = vector_results
            else:
                all_results = vector_results
            
            # ---- Step 4: Multi-source diversity filtering ----
            if enable_multi_source and all_results:
                before_diversity = len(all_results)
                all_results = self._ensure_source_diversity(
                    all_results, 
                    max_per_file=max_per_file,
                    min_files=min_files,
                    target_total=n_results * 2  # Get more candidates for reranking
                )
                logger.info(f"Multi-source filtering: {before_diversity} -> {len(all_results)} results")
            
            # ---- Step 5: Cosine similarity reranking ----
            if enable_rerank and all_results:
                all_results = self._rerank_by_cosine(query_embedding, all_results)
                logger.info(f"Reranked {len(all_results)} results by cosine similarity")
            
            # ---- Step 6: Relevance threshold filtering ----
            if relevance_threshold > 0:
                before_count = len(all_results)
                all_results = [
                    r for r in all_results 
                    if r.get('score', 0) >= relevance_threshold
                ]
                filtered_count = before_count - len(all_results)
                if filtered_count > 0:
                    logger.info(f"Filtered {filtered_count} results below threshold {relevance_threshold}")
            
            # Return top n results
            final_results = all_results[:n_results]
            logger.info(f"Final results: {len(final_results)} (from {len(all_results)} candidates)")
            
            # Log source distribution
            if final_results:
                file_distribution = defaultdict(int)
                for r in final_results:
                    file_name = r.get('metadata', {}).get('file_name', 'unknown')
                    file_distribution[file_name] += 1
                logger.info(f"Source distribution: {dict(file_distribution)}")
            
            return final_results
            
        except Exception as e:
            logger.error(f"Query failed: {e}")
            return []
    
    def _ensure_source_diversity(self, results: List[Dict[str, Any]], 
                                 max_per_file: int = 3,
                                 min_files: int = 2,
                                 target_total: int = 10) -> List[Dict[str, Any]]:
        """
        Ensure retrieval results come from multiple files for better diversity.
        
        Reference: Open WebUI's approach to multi-source retrieval
        - Limits chunks per file to avoid single file monopoly
        - Prioritizes results from different files
        - Ensures minimum number of source files
        
        Args:
            results: List of search results sorted by relevance
            max_per_file: Maximum number of chunks to keep from a single file
            min_files: Minimum number of different files to include
            target_total: Target total number of results after filtering
            
        Returns:
            Diversified list of results
        """
        if not results:
            return results
        
        # Group results by file
        file_chunks = defaultdict(list)
        for result in results:
            file_id = result.get('metadata', {}).get('file_id', 'unknown')
            file_name = result.get('metadata', {}).get('file_name', 'unknown')
            key = f"{file_id}:{file_name}"  # Use both id and name for uniqueness
            file_chunks[key].append(result)
        
        logger.info(f"Results come from {len(file_chunks)} different files")
        
        # Round-robin selection to ensure diversity
        # Take top results from each file in rotation
        diversified = []
        file_pointers = {k: 0 for k in file_chunks.keys()}
        
        while len(diversified) < target_total:
            added_in_round = 0
            
            for file_key in file_chunks.keys():
                pointer = file_pointers[file_key]
                chunks = file_chunks[file_key]
                
                # Check if we've reached max_per_file for this file
                file_count = sum(1 for r in diversified if 
                               f"{r.get('metadata', {}).get('file_id', 'unknown')}:"
                               f"{r.get('metadata', {}).get('file_name', 'unknown')}" == file_key)
                
                if pointer < len(chunks) and file_count < max_per_file:
                    diversified.append(chunks[pointer])
                    file_pointers[file_key] += 1
                    added_in_round += 1
                    
                    if len(diversified) >= target_total:
                        break
            
            # If no more results can be added, break
            if added_in_round == 0:
                break
        
        # Check if we have enough different files
        files_in_result = set()
        for r in diversified:
            file_id = r.get('metadata', {}).get('file_id', 'unknown')
            file_name = r.get('metadata', {}).get('file_name', 'unknown')
            files_in_result.add(f"{file_id}:{file_name}")
        
        if len(files_in_result) < min_files:
            logger.warning(f"Only {len(files_in_result)} files in results, "
                          f"less than minimum {min_files}")
        
        logger.info(f"Diversity filtering: {len(results)} -> {len(diversified)} results "
                   f"from {len(files_in_result)} files")
        
        return diversified
    
    def _rerank_by_cosine(self, query_embedding: List[float],
                          results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Rerank results using cosine similarity between query embedding 
        and document embeddings.
        Reference: Open WebUI's RerankCompressor approach.
        """
        try:
            # Collect texts to embed
            texts = [r['content'] for r in results]
            
            # Generate embeddings for all candidate documents in batch
            doc_embeddings = self.embedding_service.generate_embeddings(texts)
            
            query_vec = np.array(query_embedding)
            query_norm = np.linalg.norm(query_vec)
            
            if query_norm == 0:
                return results
            
            for i, result in enumerate(results):
                doc_vec = np.array(doc_embeddings[i])
                doc_norm = np.linalg.norm(doc_vec)
                if doc_norm == 0:
                    result['score'] = 0.0
                else:
                    cosine_sim = float(np.dot(query_vec, doc_vec) / (query_norm * doc_norm))
                    result['score'] = cosine_sim
            
            # Sort by cosine similarity descending (higher is better)
            results.sort(key=lambda x: x.get('score', 0), reverse=True)
            return results
            
        except Exception as e:
            logger.warning(f"Cosine reranking failed, falling back to original order: {e}")
            # Fallback: convert distance to score if available
            for r in results:
                if 'score' not in r and 'distance' in r:
                    r['score'] = max(0, 1 - r['distance'])
            return results
    
    def delete_file_from_collection(self, collection_name: str, file_id: str):
        """Delete all chunks for a file from collection"""
        try:
            self.vector_service.delete_by_metadata(
                collection_name=collection_name,
                where={'file_id': file_id}
            )
            # Invalidate BM25 cache since collection content changed
            self.bm25_retriever.invalidate_cache(collection_name)
            logger.info(f"Deleted file {file_id} from collection {collection_name}")
        except Exception as e:
            logger.error(f"Failed to delete file from collection: {e}")
            raise


def get_rag_service() -> RAGService:
    """Get RAG service instance"""
    return RAGService()
