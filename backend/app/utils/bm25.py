"""
BM25 Retriever for Hybrid Search
Lightweight BM25 implementation using rank_bm25 + jieba for Chinese text.
Reference: Open WebUI's query_doc_with_hybrid_search approach.
"""
import logging
import re
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

try:
    from rank_bm25 import BM25Okapi
except ImportError:
    BM25Okapi = None
    logger.warning("rank_bm25 not installed. BM25 hybrid search will be disabled.")

try:
    import jieba
except ImportError:
    jieba = None
    logger.warning("jieba not installed. Chinese tokenization will fall back to character split.")


def tokenize(text: str) -> List[str]:
    """
    Tokenize text using jieba for Chinese, with whitespace split fallback.
    """
    if not text or not text.strip():
        return []
    if jieba is not None:
        return list(jieba.cut_for_search(text))
    # Fallback: simple whitespace split
    return text.lower().split()


def normalize_lookup_text(text: str) -> str:
    """Normalize text for metadata/title matching."""
    if not text:
        return ''
    value = str(text).lower().strip()
    value = re.sub(r'\s+', '', value)
    value = re.sub(r'[，。；：、“”‘’（）()\[\]【】\-—_·,.!?？!/:]', '', value)
    return value


def get_enriched_text(doc: str, metadata: Dict[str, Any]) -> str:
    """
    Enrich document text with metadata (file_name, section_title, section_path)
    for better BM25 keyword matching. 
    Reference: Open WebUI's get_enriched_texts.
    """
    parts = []
    file_name = metadata.get('file_name', '')
    if file_name:
        # Remove extension for cleaner matching
        name_no_ext = file_name.rsplit('.', 1)[0] if '.' in file_name else file_name
        parts.append(name_no_ext)
    
    section_path = metadata.get('section_path', '')
    if section_path:
        if isinstance(section_path, list):
            parts.append(' '.join(section_path))
        else:
            parts.append(str(section_path))
    
    section_title = metadata.get('section_title', '')
    if section_title:
        parts.append(section_title)
    
    # Prepend metadata text before actual content
    prefix = ' '.join(parts)
    return f"{prefix} {doc}" if prefix.strip() else doc


class BM25Retriever:
    """
    BM25 retriever that works with ChromaDB collections.
    Builds an in-memory BM25 index from collection documents.
    """
    
    def __init__(self):
        self._index_cache = {}  # collection_name -> (corpus_tokens, docs, metadatas, ids)
    
    def _build_index(self, collection_name: str, vector_service) -> bool:
        """
        Build BM25 index from a ChromaDB collection.
        Fetches all documents and tokenizes them.
        """
        if BM25Okapi is None:
            logger.warning("rank_bm25 not available, cannot build BM25 index")
            return False
        
        try:
            collection = vector_service.client.get_collection(name=collection_name)
            # Get all documents from collection
            result = collection.get(include=['documents', 'metadatas'])
            
            if not result['ids']:
                logger.warning(f"Collection {collection_name} is empty")
                return False
            
            docs = result['documents']
            metadatas = result['metadatas'] or [{}] * len(docs)
            ids = result['ids']
            
            # Enrich and tokenize
            corpus_tokens = []
            for doc, meta in zip(docs, metadatas):
                enriched = get_enriched_text(doc, meta)
                tokens = tokenize(enriched)
                corpus_tokens.append(tokens)
            
            self._index_cache[collection_name] = {
                'bm25': BM25Okapi(corpus_tokens),
                'docs': docs,
                'metadatas': metadatas,
                'ids': ids
            }
            
            logger.info(f"Built BM25 index for {collection_name}: {len(docs)} documents")
            return True
            
        except Exception as e:
            logger.error(f"Failed to build BM25 index for {collection_name}: {e}")
            return False
    
    def search(self, query: str, collection_name: str, vector_service,
               n_results: int = 10) -> List[Dict[str, Any]]:
        """
        Search using BM25 scoring.
        
        Returns:
            List of dicts with keys: content, metadata, score, id
        """
        if BM25Okapi is None:
            return []
        
        # Build index if not cached
        if collection_name not in self._index_cache:
            if not self._build_index(collection_name, vector_service):
                return []
        
        cache = self._index_cache[collection_name]
        query_tokens = tokenize(query)
        
        if not query_tokens:
            return []
        
        scores = cache['bm25'].get_scores(query_tokens)
        
        # Get top-N indices sorted by score descending
        indexed_scores = list(enumerate(scores))
        indexed_scores.sort(key=lambda x: x[1], reverse=True)
        top_indices = indexed_scores[:n_results]
        
        results = []
        for idx, score in top_indices:
            if score <= 0:
                continue
            results.append({
                'content': cache['docs'][idx],
                'metadata': cache['metadatas'][idx],
                'score': float(score),
                'id': cache['ids'][idx]
            })
        
        return results

    def search_title_matches(self, query: str, collection_name: str, vector_service,
                             n_results: int = 10, terms: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """
        Search by section title / section path / filename match.
        Useful for title-like technical questions that can be crowded out in large corpora.
        """
        if collection_name not in self._index_cache:
            if not self._build_index(collection_name, vector_service):
                return []

        cache = self._index_cache[collection_name]
        query_norm = normalize_lookup_text(query)
        candidate_terms = [normalize_lookup_text(term) for term in (terms or []) if normalize_lookup_text(term)]
        if query_norm and query_norm not in candidate_terms:
            candidate_terms.insert(0, query_norm)

        if not candidate_terms:
            return []

        ranked = []
        for idx, (doc, metadata, doc_id) in enumerate(zip(cache['docs'], cache['metadatas'], cache['ids'])):
            score = self._score_title_match(metadata or {}, candidate_terms)
            if score <= 0:
                continue
            ranked.append({
                'content': doc,
                'metadata': metadata,
                'score': float(score),
                'id': doc_id,
                'match_type': 'title'
            })

        ranked.sort(key=lambda item: item['score'], reverse=True)
        return ranked[:n_results]

    def _score_title_match(self, metadata: Dict[str, Any], candidate_terms: List[str]) -> float:
        title = normalize_lookup_text(metadata.get('section_title', ''))
        section_path = normalize_lookup_text(metadata.get('section_path', ''))
        file_name = normalize_lookup_text(metadata.get('file_name', ''))

        best = 0.0
        for term in candidate_terms:
            if not term:
                continue
            if title and term == title:
                best = max(best, 8.0)
            elif title and (term in title or title in term):
                best = max(best, 6.5)

            if section_path and term in section_path:
                best = max(best, 5.8)
            if file_name and term in file_name:
                best = max(best, 5.2)

            if title and any(part and part in title for part in term.split()):
                best = max(best, 3.2)

        return best
    
    def invalidate_cache(self, collection_name: str = None):
        """Clear BM25 index cache for a collection (or all)."""
        if collection_name:
            self._index_cache.pop(collection_name, None)
        else:
            self._index_cache.clear()


def reciprocal_rank_fusion(results_list: List[List[Dict[str, Any]]],
                           k: int = 60) -> List[Dict[str, Any]]:
    """
    Reciprocal Rank Fusion (RRF) to merge multiple ranked result lists.
    Reference: Cormack et al., "Reciprocal Rank Fusion outperforms Condorcet and individual Rank Learning Methods"
    
    Args:
        results_list: List of ranked result lists (each result must have 'content' or 'id' key)
        k: RRF constant (default 60)
    
    Returns:
        Merged and re-ranked results sorted by RRF score
    """
    rrf_scores = {}  # id -> {'score': float, 'result': dict}
    
    for results in results_list:
        for rank, result in enumerate(results):
            # Use content hash as unique key
            doc_id = result.get('id', hash(result.get('content', '')))
            rrf_score = 1.0 / (k + rank + 1)
            
            if doc_id in rrf_scores:
                rrf_scores[doc_id]['score'] += rrf_score
            else:
                rrf_scores[doc_id] = {
                    'score': rrf_score,
                    'result': result
                }
    
    # Sort by RRF score descending
    sorted_items = sorted(rrf_scores.values(), key=lambda x: x['score'], reverse=True)
    
    # Return results with RRF score injected
    merged = []
    for item in sorted_items:
        result = item['result'].copy()
        result['rrf_score'] = item['score']
        merged.append(result)
    
    return merged
