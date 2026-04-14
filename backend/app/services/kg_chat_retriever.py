"""Knowledge-graph retrieval adapter for chat sources."""

from __future__ import annotations

from typing import Any, Dict, List, Optional
import math
import logging
import re

from flask import current_app

from .embedding_service import get_embedding_service
from .kg_service import get_kg_service

logger = logging.getLogger(__name__)

PREFERRED_PROPERTY_KEYS = (
    "description",
    "summary",
    "content",
    "reason",
    "cause",
    "symptom",
    "action",
    "solution",
    "measure",
    "method",
    "value",
    "status",
)

NOISY_PROPERTY_KEYS = {
    "id",
    "name",
    "label",
    "embedding",
    "vector",
    "source_books",
    "book_names",
    "books",
    "mentions",
}

QUESTION_SUFFIX_PATTERNS = (
    r'的?原因有哪些',
    r'有哪些原因',
    r'怎么处理',
    r'如何处理',
    r'怎么解决',
    r'如何解决',
    r'怎么办',
    r'为什么',
    r'是什么',
    r'有哪些',
    r'怎么排查',
    r'如何排查',
    r'怎么维修',
    r'如何维修',
    r'怎么修',
    r'如何修',
)


class KGChatRetriever:
    """Retrieve graph nodes and normalize them into chat citation sources."""

    def __init__(self, kg_service=None, embedding_service=None):
        self._kg_service = kg_service
        self._embedding_service = embedding_service

    @property
    def kg_service(self):
        if self._kg_service is None:
            self._kg_service = get_kg_service()
        return self._kg_service

    @property
    def embedding_service(self):
        if self._embedding_service is None:
            self._embedding_service = get_embedding_service()
        return self._embedding_service

    def retrieve_sources(
        self,
        query: str,
        limit: Optional[int] = None,
        candidate_limit: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Retrieve KG nodes, convert to source items, and rerank by embedding similarity."""
        if not query or not query.strip():
            return []

        if not current_app.config.get('KG_ENABLED', False):
            return []

        try:
            if not self.kg_service.ping():
                logger.warning("KG service unavailable, skip KG chat retrieval")
                return []
        except Exception as exc:
            logger.warning(f"KG availability check failed: {exc}")
            return []

        resolved_limit = max(1, limit or current_app.config.get('KG_CHAT_TOP_K', 3))
        multiplier = max(1, current_app.config.get('KG_CHAT_CANDIDATE_MULTIPLIER', 3))
        resolved_candidate_limit = max(
            resolved_limit,
            candidate_limit or resolved_limit * multiplier
        )

        raw_nodes: List[Dict[str, Any]] = []
        seen_node_ids = set()
        search_terms = self._expand_query_terms(query)

        for term in search_terms:
            try:
                term_results = self.kg_service.search(term, limit=resolved_candidate_limit)
            except Exception as exc:
                logger.warning(f"KG search failed for term '{term}': {exc}")
                continue

            for node in term_results:
                node_id = node.get('id')
                if not node_id or node_id in seen_node_ids:
                    continue
                raw_nodes.append(node)
                seen_node_ids.add(node_id)
                if len(raw_nodes) >= resolved_candidate_limit:
                    break

            if len(raw_nodes) >= resolved_candidate_limit:
                break

        if not raw_nodes:
            return []

        candidates: List[Dict[str, Any]] = []
        for node in raw_nodes:
            source = self._build_source(node)
            if source:
                candidates.append(source)

        if not candidates:
            return []

        rerank_texts = [self._build_rerank_text(item) for item in candidates]

        try:
            query_embedding = self.embedding_service.generate_embedding(query)
            item_embeddings = self.embedding_service.generate_embeddings(rerank_texts)
        except Exception as exc:
            logger.warning(f"KG rerank embedding failed, fallback to lexical order: {exc}")
            for rank, item in enumerate(candidates):
                item['score'] = max(0.0, 1.0 - rank * 0.05)
            return candidates[:resolved_limit]

        min_score = current_app.config.get('KG_CHAT_MIN_SCORE', 0.2)
        for index, item in enumerate(candidates):
            cosine = self._cosine_similarity(query_embedding, item_embeddings[index])
            name_hit = self._name_match_boost(query, item)
            item['score'] = min(1.0, cosine + name_hit)

        candidates = [
            item for item in candidates
            if item.get('score', 0.0) >= min_score
        ]
        candidates.sort(key=lambda item: item.get('score', 0.0), reverse=True)
        return candidates[:resolved_limit]

    def _build_source(self, node: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        node_id = node.get('id')
        node_name = node.get('name') or '未命名节点'
        node_labels = list(node.get('labels') or [])
        properties = node.get('properties') or {}

        if not node_id:
            return None

        resources = []
        try:
            resources = self.kg_service.get_node_resources(node_id)
        except Exception as exc:
            logger.debug(f"Failed to load KG node resources for {node_id}: {exc}")

        resource_titles = [
            item.get('title') for item in resources
            if item.get('title')
        ]
        max_resources = max(1, current_app.config.get('KG_CHAT_MAX_RESOURCES_PER_NODE', 2))
        resource_titles = resource_titles[:max_resources]

        summary_parts = [
            f"图谱节点：{node_name}",
        ]
        if node_labels:
            summary_parts.append(f"类型：{'、'.join(node_labels)}")

        property_lines = self._summarize_properties(properties)
        if property_lines:
            summary_parts.extend(property_lines)

        if resource_titles:
            summary_parts.append(f"关联资料：{'；'.join(resource_titles)}")

        content = "\n".join(summary_parts).strip()
        if not content:
            return None

        return {
            'source_type': 'kg',
            'content': content,
            'file_name': '知识图谱',
            'file_id': None,
            'section_path': node_labels,
            'section_title': node_name,
            'score': 0.0,
            'node_id': node_id,
            'node_name': node_name,
            'node_labels': node_labels,
            'related_books': resource_titles,
        }

    def _summarize_properties(self, properties: Dict[str, Any]) -> List[str]:
        snippets: List[str] = []
        used_keys = set()

        for key in PREFERRED_PROPERTY_KEYS:
            value = self._format_property_value(properties.get(key))
            if value:
                snippets.append(f"{key}：{value}")
                used_keys.add(key)

        for key, raw_value in properties.items():
            if key in used_keys or key in NOISY_PROPERTY_KEYS:
                continue
            value = self._format_property_value(raw_value)
            if value:
                snippets.append(f"{key}：{value}")
            if len(snippets) >= 5:
                break

        return snippets[:5]

    def _format_property_value(self, value: Any) -> str:
        if value is None:
            return ''

        if isinstance(value, list):
            scalar_items = []
            for item in value:
                if isinstance(item, (str, int, float, bool)):
                    text = str(item).strip()
                    if text:
                        scalar_items.append(text)
                if len(scalar_items) >= 4:
                    break
            return '、'.join(scalar_items)

        if isinstance(value, (str, int, float, bool)):
            text = str(value).strip()
            if not text:
                return ''
            if len(text) > 180:
                return text[:177] + '...'
            return text

        return ''

    def _build_rerank_text(self, item: Dict[str, Any]) -> str:
        parts = [item.get('node_name') or '', ' '.join(item.get('node_labels') or [])]
        parts.extend(item.get('related_books') or [])
        parts.append(item.get('content') or '')
        return '\n'.join(part for part in parts if part)

    def _expand_query_terms(self, query: str) -> List[str]:
        normalized = re.sub(r'[？?！!，,。；;：:“”"\'（）()【】\[\]]+', ' ', query or '').strip()
        if not normalized:
            return []

        candidates = [normalized]

        compact_segments = re.findall(r'[\u4e00-\u9fff]{2,}', normalized)
        for segment in compact_segments:
            simplified = segment
            for pattern in QUESTION_SUFFIX_PATTERNS:
                simplified = re.sub(pattern + r'$', '', simplified)
            simplified = simplified.strip('的和与及')
            if len(simplified) >= 2:
                candidates.append(simplified)

            parts = re.split(r'[的和与及]', simplified)
            for part in parts:
                part = part.strip()
                if len(part) >= 2:
                    candidates.append(part)

        for token in re.findall(r'[A-Za-z0-9_]{3,}', normalized):
            candidates.append(token.lower())

        deduped: List[str] = []
        seen = set()
        for item in candidates:
            if not item or item in seen:
                continue
            seen.add(item)
            deduped.append(item)
        return deduped

    def _name_match_boost(self, query: str, item: Dict[str, Any]) -> float:
        query_text = query.strip().lower()
        node_name = str(item.get('node_name') or '').strip().lower()
        if not query_text or not node_name:
            return 0.0
        if node_name == query_text:
            return 0.12
        if node_name in query_text or query_text in node_name:
            return 0.06
        return 0.0

    def _cosine_similarity(self, lhs: List[float], rhs: List[float]) -> float:
        if not lhs or not rhs or len(lhs) != len(rhs):
            return 0.0

        numerator = sum(a * b for a, b in zip(lhs, rhs))
        lhs_norm = math.sqrt(sum(a * a for a in lhs))
        rhs_norm = math.sqrt(sum(b * b for b in rhs))
        if lhs_norm == 0 or rhs_norm == 0:
            return 0.0
        return float(numerator / (lhs_norm * rhs_norm))


def get_kg_chat_retriever() -> KGChatRetriever:
    return KGChatRetriever()
