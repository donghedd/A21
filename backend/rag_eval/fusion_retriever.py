"""Fusion retriever for document + knowledge-graph evaluation."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence

from .evaluator import _safe_float, _truncate_preview


class FusionRetriever:
    """Retrieve and merge document chunks with KG nodes using the runtime fusion logic."""

    def __init__(self, runtime_fusion_retriever=None):
        self._runtime_fusion_retriever = runtime_fusion_retriever

    @property
    def runtime_fusion_retriever(self):
        if self._runtime_fusion_retriever is None:
            from app.services.fusion_retriever import get_fusion_retriever

            self._runtime_fusion_retriever = get_fusion_retriever()
        return self._runtime_fusion_retriever

    def retrieve(
        self,
        query: str,
        collection_names: Sequence[str],
        top_k: int,
        *,
        enable_rerank: bool = True,
        enable_hybrid: Optional[bool] = None,
        enable_multi_source: Optional[bool] = None,
        enable_kg: bool = True,
        document_limit: Optional[int] = None,
        kg_limit: Optional[int] = None,
        preview_chars: int = 180,
    ) -> List[Dict[str, Any]]:
        raw_results = self.runtime_fusion_retriever.retrieve_sources(
            query=query,
            collection_names=list(collection_names),
            top_k=top_k,
            enable_rerank=enable_rerank,
            enable_hybrid=enable_hybrid,
            enable_multi_source=enable_multi_source,
            enable_kg=enable_kg,
            document_limit=document_limit,
            kg_limit=kg_limit,
        )

        ranked: List[Dict[str, Any]] = []
        for index, item in enumerate(raw_results[:top_k], start=1):
            normalized = dict(item)
            normalized["node_name"] = normalized.get("node_name") or normalized.get("section_title")
            normalized["distance"] = round(_safe_float(normalized.get("distance"), 0.0), 6)
            normalized["score"] = round(_safe_float(normalized.get("score"), 0.0), 6)
            normalized["preview"] = _truncate_preview(
                normalized.get("content", ""),
                limit=preview_chars,
            )
            normalized["rank"] = index
            ranked.append(normalized)

        return ranked
