"""Runtime fusion retriever for document and knowledge-graph sources."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence
import logging

from flask import current_app

from .kg_chat_retriever import get_kg_chat_retriever
from .rag_service import get_rag_service

logger = logging.getLogger(__name__)


class FusionRetriever:
    """Merge document retrieval with KG retrieval using unified score ordering."""

    def __init__(self, rag_service=None, kg_chat_retriever=None):
        self._rag_service = rag_service
        self._kg_chat_retriever = kg_chat_retriever

    @property
    def rag_service(self):
        if self._rag_service is None:
            self._rag_service = get_rag_service()
        return self._rag_service

    @property
    def kg_chat_retriever(self):
        if self._kg_chat_retriever is None:
            self._kg_chat_retriever = get_kg_chat_retriever()
        return self._kg_chat_retriever

    def retrieve_sources(
        self,
        query: str,
        collection_names: Sequence[str],
        top_k: Optional[int] = None,
        enable_rerank: bool = True,
        enable_hybrid: Optional[bool] = None,
        enable_multi_source: Optional[bool] = None,
        enable_kg: Optional[bool] = None,
        document_limit: Optional[int] = None,
        kg_limit: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        resolved_top_k = max(1, top_k or current_app.config.get('RAG_TOP_K', 10))
        resolved_document_limit = max(
            resolved_top_k,
            document_limit or current_app.config.get('RAG_FUSION_DOCUMENT_LIMIT', resolved_top_k)
        )
        resolved_kg_limit = max(
            1,
            kg_limit or current_app.config.get('KG_CHAT_TOP_K', 3)
        )
        use_kg = (
            current_app.config.get('RAG_ENABLE_KG_FUSION', True)
            if enable_kg is None
            else enable_kg
        )

        document_weight = float(current_app.config.get('RAG_FUSION_DOCUMENT_WEIGHT', 1.0))
        kg_weight = float(current_app.config.get('RAG_FUSION_KG_WEIGHT', 1.0))

        merged_results: List[Dict[str, Any]] = []

        if collection_names:
            document_results = self.rag_service.query(
                query=query,
                collection_names=list(collection_names),
                n_results=resolved_document_limit,
                enable_rerank=enable_rerank,
                enable_hybrid=enable_hybrid,
                enable_multi_source=enable_multi_source,
            )
            for result in document_results:
                metadata = result.get('metadata', {})
                score = self._resolve_score(result) * document_weight
                merged_results.append(
                    {
                        'source_type': 'document',
                        'content': result.get('content', ''),
                        'file_name': metadata.get('file_name', 'Unknown'),
                        'file_id': metadata.get('file_id'),
                        'section_path': metadata.get('section_path', []),
                        'section_title': metadata.get('section_title', ''),
                        'score': score,
                        'node_id': None,
                        'node_name': None,
                        'node_labels': [],
                    }
                )

        if use_kg:
            kg_results = self.kg_chat_retriever.retrieve_sources(
                query=query,
                limit=resolved_kg_limit,
            )
            for result in kg_results:
                normalized = dict(result)
                normalized['score'] = float(result.get('score', 0.0)) * kg_weight
                merged_results.append(normalized)

        merged_results.sort(key=lambda item: item.get('score', 0.0), reverse=True)

        max_kg_results = current_app.config.get('RAG_FUSION_MAX_KG_RESULTS')
        if max_kg_results:
            merged_results = self._limit_kg_results(
                merged_results,
                top_k=resolved_top_k,
                max_kg_results=max(1, int(max_kg_results))
            )

        return merged_results[:resolved_top_k]

    def _resolve_score(self, result: Dict[str, Any]) -> float:
        score = result.get('score')
        if score is not None:
            return max(0.0, float(score))

        distance = result.get('distance')
        if distance is None:
            return 0.0
        return max(0.0, 1.0 - float(distance))

    def _limit_kg_results(
        self,
        results: List[Dict[str, Any]],
        top_k: int,
        max_kg_results: int,
    ) -> List[Dict[str, Any]]:
        limited: List[Dict[str, Any]] = []
        kg_count = 0

        for item in results:
            if item.get('source_type') == 'kg':
                if kg_count >= max_kg_results:
                    continue
                kg_count += 1
            limited.append(item)
            if len(limited) >= top_k:
                break

        return limited


def get_fusion_retriever() -> FusionRetriever:
    return FusionRetriever()
