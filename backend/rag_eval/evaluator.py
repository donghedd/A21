"""Standalone retrieval evaluator built on top of the existing RAG service."""

from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional, Sequence

from .dataset import EvalDataset, EvalQuery, normalize_k_values


METRIC_LEVELS = ("file", "chunk")


def _normalize_name(value: Optional[str]) -> str:
    return (value or "").strip().lower()


def _file_key(file_id: Optional[str], file_name: Optional[str]) -> Optional[str]:
    if file_id:
        return f"id::{file_id.strip()}"
    normalized_name = _normalize_name(file_name)
    if normalized_name:
        return f"name::{normalized_name}"
    return None


def _chunk_key(
    file_id: Optional[str],
    file_name: Optional[str],
    chunk_index: Any,
) -> Optional[str]:
    file_marker = _file_key(file_id, file_name)
    if file_marker is None:
        return None

    try:
        numeric_index = int(chunk_index)
    except (TypeError, ValueError):
        return None

    return f"{file_marker}::chunk::{numeric_index}"


def _match_file_target(retrieved: Dict[str, Any], gold: Dict[str, Any]) -> bool:
    gold_file_id = (gold.get("file_id") or "").strip()
    gold_file_name = _normalize_name(gold.get("file_name"))

    retrieved_file_id = (retrieved.get("file_id") or "").strip()
    retrieved_file_name = _normalize_name(retrieved.get("file_name"))

    if gold_file_id and retrieved_file_id and gold_file_id == retrieved_file_id:
        return True
    if gold_file_name and retrieved_file_name and gold_file_name == retrieved_file_name:
        return True
    return False


def _match_chunk_target(retrieved: Dict[str, Any], gold: Dict[str, Any]) -> bool:
    try:
        gold_chunk_index = int(gold.get("chunk_index"))
    except (TypeError, ValueError):
        return False

    try:
        retrieved_chunk_index = int(retrieved.get("chunk_index"))
    except (TypeError, ValueError):
        return False

    if gold_chunk_index != retrieved_chunk_index:
        return False

    return _match_file_target(retrieved, gold)


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _truncate_preview(text: str, limit: int = 180) -> str:
    clean = " ".join((text or "").split())
    if len(clean) <= limit:
        return clean
    return clean[: limit - 3] + "..."


def _unique_preserve_order(items: Iterable[str]) -> List[str]:
    result: List[str] = []
    seen = set()
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        result.append(item)
    return result


@contextmanager
def _temporary_config(app, **overrides):
    sentinel = object()
    original: Dict[str, Any] = {}

    for key, value in overrides.items():
        if value is None:
            continue
        original[key] = app.config.get(key, sentinel)
        app.config[key] = value

    try:
        yield
    finally:
        for key, old_value in original.items():
            if old_value is sentinel:
                app.config.pop(key, None)
            else:
                app.config[key] = old_value


def resolve_collection_names(
    kb_ids: Optional[Sequence[str]] = None,
    collection_names: Optional[Sequence[str]] = None,
    custom_model_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Resolve collections from knowledge-base ids, explicit collection names,
    and/or a custom model binding.
    """

    from app.models import CustomModel, KnowledgeBase, ModelKnowledgeBinding

    resolved_collections: List[str] = []
    resolved_kbs: List[Dict[str, Any]] = []
    resolved_model: Optional[Dict[str, Any]] = None

    for kb_id in kb_ids or []:
        kb = KnowledgeBase.query.get(kb_id)
        if kb is None:
            raise ValueError(f"Knowledge base not found: {kb_id}")
        resolved_collections.append(kb.collection_name)
        resolved_kbs.append(
            {
                "id": kb.id,
                "name": kb.name,
                "collection_name": kb.collection_name,
                "file_count": kb.files.count(),
            }
        )

    if custom_model_id:
        custom_model = CustomModel.query.get(custom_model_id)
        if custom_model is None:
            raise ValueError(f"Custom model not found: {custom_model_id}")

        resolved_model = {
            "id": custom_model.id,
            "name": custom_model.name,
            "base_model": custom_model.base_model,
        }

        bindings = ModelKnowledgeBinding.query.filter_by(
            custom_model_id=custom_model_id
        ).all()
        for binding in bindings:
            kb = binding.knowledge_base
            if kb is None:
                continue
            resolved_collections.append(kb.collection_name)
            resolved_kbs.append(
                {
                    "id": kb.id,
                    "name": kb.name,
                    "collection_name": kb.collection_name,
                    "file_count": kb.files.count(),
                }
            )

    for collection_name in collection_names or []:
        collection_name = (collection_name or "").strip()
        if collection_name:
            resolved_collections.append(collection_name)

    deduped_collections = _unique_preserve_order(
        item for item in resolved_collections if item
    )

    deduped_kbs: List[Dict[str, Any]] = []
    seen_kb_ids = set()
    for item in resolved_kbs:
        kb_id = item["id"]
        if kb_id in seen_kb_ids:
            continue
        seen_kb_ids.add(kb_id)
        deduped_kbs.append(item)

    if not deduped_collections:
        raise ValueError("No collections resolved. Provide --kb-id, --collection, or --custom-model-id.")

    return {
        "collection_names": deduped_collections,
        "knowledge_bases": deduped_kbs,
        "custom_model": resolved_model,
    }


class RetrievalEvaluator:
    """Evaluate recall-oriented retrieval metrics with gold labels."""

    def __init__(self, rag_service=None):
        if rag_service is None:
            from app.services import get_rag_service

            rag_service = get_rag_service()
        self.rag_service = rag_service

    def evaluate_dataset(
        self,
        app,
        dataset: EvalDataset,
        collection_names: Sequence[str],
        k_values: Optional[Sequence[int]] = None,
        enable_rerank: bool = True,
        enable_hybrid: Optional[bool] = None,
        enable_multi_source: Optional[bool] = None,
        relevance_threshold: Optional[float] = None,
        preview_chars: int = 180,
    ) -> Dict[str, Any]:
        active_k_values = normalize_k_values(k_values or dataset.k_values)

        level_totals = {
            level: {
                "queries_with_labels": 0,
                "sums": {
                    str(k): {"recall": 0.0, "hit_rate": 0.0, "mrr": 0.0}
                    for k in active_k_values
                },
            }
            for level in METRIC_LEVELS
        }

        query_reports: List[Dict[str, Any]] = []
        skipped_queries = 0

        config_overrides = {}
        if relevance_threshold is not None:
            config_overrides["RELEVANCE_THRESHOLD"] = relevance_threshold

        with _temporary_config(app, **config_overrides):
            for example in dataset.queries:
                query_report = self._evaluate_query(
                    example=example,
                    collection_names=collection_names,
                    k_values=active_k_values,
                    enable_rerank=enable_rerank,
                    enable_hybrid=enable_hybrid,
                    enable_multi_source=enable_multi_source,
                    preview_chars=preview_chars,
                )
                query_reports.append(query_report)

                if query_report["skipped"]:
                    skipped_queries += 1

                for level in METRIC_LEVELS:
                    evaluation = query_report["evaluations"][level]
                    if evaluation["gold_count"] <= 0:
                        continue

                    level_totals[level]["queries_with_labels"] += 1
                    for k in active_k_values:
                        metrics = evaluation["metrics"][str(k)]
                        for metric_name in ("recall", "hit_rate", "mrr"):
                            level_totals[level]["sums"][str(k)][metric_name] += metrics[metric_name]

        summary = self._build_summary(
            level_totals=level_totals,
            k_values=active_k_values,
            dataset=dataset,
            collection_names=collection_names,
            skipped_queries=skipped_queries,
            total_queries=len(dataset.queries),
            enable_rerank=enable_rerank,
            enable_hybrid=enable_hybrid,
            enable_multi_source=enable_multi_source,
            relevance_threshold=(
                relevance_threshold
                if relevance_threshold is not None
                else app.config.get("RELEVANCE_THRESHOLD")
            ),
        )

        return {
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "dataset": {
                "name": dataset.name,
                "description": dataset.description,
                "query_count": len(dataset.queries),
                "k_values": active_k_values,
            },
            "retrieval_settings": {
                "collection_names": list(collection_names),
                "enable_rerank": enable_rerank,
                "enable_hybrid": (
                    app.config.get("ENABLE_HYBRID_SEARCH")
                    if enable_hybrid is None
                    else enable_hybrid
                ),
                "enable_multi_source": (
                    app.config.get("RAG_ENABLE_MULTI_SOURCE")
                    if enable_multi_source is None
                    else enable_multi_source
                ),
                "relevance_threshold": (
                    app.config.get("RELEVANCE_THRESHOLD")
                    if relevance_threshold is None
                    else relevance_threshold
                ),
            },
            "summary": summary,
            "queries": query_reports,
        }

    def _evaluate_query(
        self,
        example: EvalQuery,
        collection_names: Sequence[str],
        k_values: Sequence[int],
        enable_rerank: bool,
        enable_hybrid: Optional[bool],
        enable_multi_source: Optional[bool],
        preview_chars: int,
    ) -> Dict[str, Any]:
        max_k = max(k_values)
        raw_results = self.rag_service.query(
            query=example.query,
            collection_names=list(collection_names),
            n_results=max_k,
            enable_rerank=enable_rerank,
            enable_hybrid=enable_hybrid,
            enable_multi_source=enable_multi_source,
        )

        ranked_results: List[Dict[str, Any]] = []
        retrieved_match_inputs: List[Dict[str, Any]] = []

        for rank, result in enumerate(raw_results, start=1):
            metadata = result.get("metadata", {})
            file_id = metadata.get("file_id")
            file_name = metadata.get("file_name")
            chunk_index = metadata.get("chunk_index")

            ranked_results.append(
                {
                    "rank": rank,
                    "file_id": file_id,
                    "file_name": file_name,
                    "chunk_index": chunk_index,
                    "section_title": metadata.get("section_title"),
                    "section_path": metadata.get("section_path"),
                    "score": round(_safe_float(result.get("score"), 0.0), 6),
                    "distance": round(_safe_float(result.get("distance"), 0.0), 6),
                    "preview": _truncate_preview(result.get("content", ""), limit=preview_chars),
                }
            )
            retrieved_match_inputs.append(
                {
                    "file_id": file_id,
                    "file_name": file_name,
                    "chunk_index": chunk_index,
                }
            )

        gold_file_targets = self._build_gold_file_targets(example)
        gold_chunk_targets = self._build_gold_chunk_targets(example)

        file_evaluation = self._evaluate_level(
            level="file",
            gold_targets=gold_file_targets,
            retrieved_sequence=retrieved_match_inputs,
            k_values=k_values,
        )
        chunk_evaluation = self._evaluate_level(
            level="chunk",
            gold_targets=gold_chunk_targets,
            retrieved_sequence=retrieved_match_inputs,
            k_values=k_values,
        )

        return {
            "id": example.query_id,
            "query": example.query,
            "notes": example.notes,
            "metadata": example.metadata,
            "skipped": file_evaluation["gold_count"] == 0 and chunk_evaluation["gold_count"] == 0,
            "gold": {
                "files": gold_file_targets["targets"],
                "chunks": gold_chunk_targets["targets"],
            },
            "retrieved_results": ranked_results,
            "evaluations": {
                "file": file_evaluation,
                "chunk": chunk_evaluation,
            },
        }

    def _build_gold_file_targets(self, example: EvalQuery) -> Dict[str, Any]:
        targets: List[Dict[str, Any]] = []
        signatures: List[str] = []

        for item in example.relevant_files:
            signature = _file_key(item.file_id, item.file_name)
            if signature is None:
                continue
            signatures.append(signature)
            targets.append(item.to_dict())

        for item in example.relevant_chunks:
            signature = _file_key(item.file_id, item.file_name)
            if signature is None:
                continue
            signatures.append(signature)
            targets.append(
                {
                    "file_id": item.file_id,
                    "file_name": item.file_name,
                }
            )

        return self._deduplicate_targets(signatures=signatures, targets=targets)

    def _build_gold_chunk_targets(self, example: EvalQuery) -> Dict[str, Any]:
        targets: List[Dict[str, Any]] = []
        signatures: List[str] = []

        for item in example.relevant_chunks:
            signature = _chunk_key(item.file_id, item.file_name, item.chunk_index)
            if signature is None:
                continue
            signatures.append(signature)
            targets.append(item.to_dict())

        return self._deduplicate_targets(signatures=signatures, targets=targets)

    def _deduplicate_targets(
        self,
        signatures: Sequence[str],
        targets: Sequence[Dict[str, Any]],
    ) -> Dict[str, Any]:
        unique_targets: List[Dict[str, Any]] = []
        unique_signatures: List[str] = []
        seen = set()

        for signature, target in zip(signatures, targets):
            if signature in seen:
                continue
            seen.add(signature)
            unique_signatures.append(signature)
            unique_targets.append(target)

        return {
            "signatures": unique_signatures,
            "targets": unique_targets,
        }

    def _evaluate_level(
        self,
        level: str,
        gold_targets: Dict[str, Any],
        retrieved_sequence: Sequence[Dict[str, Any]],
        k_values: Sequence[int],
    ) -> Dict[str, Any]:
        gold_items = list(gold_targets["targets"])
        gold_count = len(gold_items)
        matcher = _match_file_target if level == "file" else _match_chunk_target

        metrics_by_k: Dict[str, Dict[str, Any]] = {}

        for k in k_values:
            top_k = list(retrieved_sequence[:k])
            matched_gold_indices = []
            for gold_index, gold_target in enumerate(gold_items):
                if any(matcher(retrieved, gold_target) for retrieved in top_k):
                    matched_gold_indices.append(gold_index)

            first_relevant_rank = next(
                (
                    index + 1
                    for index, retrieved in enumerate(top_k)
                    if any(matcher(retrieved, gold_target) for gold_target in gold_items)
                ),
                None,
            )

            recall = (len(matched_gold_indices) / gold_count) if gold_count else 0.0
            hit_rate = 1.0 if matched_gold_indices else 0.0
            mrr = (1.0 / first_relevant_rank) if first_relevant_rank else 0.0

            metrics_by_k[str(k)] = {
                "recall": round(recall, 6),
                "hit_rate": round(hit_rate, 6),
                "mrr": round(mrr, 6),
                "matched_count": len(matched_gold_indices),
                "gold_count": gold_count,
                "first_relevant_rank": first_relevant_rank,
            }

        return {
            "level": level,
            "gold_count": gold_count,
            "metrics": metrics_by_k,
        }

    def _build_summary(
        self,
        level_totals: Dict[str, Any],
        k_values: Sequence[int],
        dataset: EvalDataset,
        collection_names: Sequence[str],
        skipped_queries: int,
        total_queries: int,
        enable_rerank: bool,
        enable_hybrid: Optional[bool],
        enable_multi_source: Optional[bool],
        relevance_threshold: Optional[float],
    ) -> Dict[str, Any]:
        levels_summary: Dict[str, Any] = {}
        for level in METRIC_LEVELS:
            query_count = level_totals[level]["queries_with_labels"]
            averages: Dict[str, Any] = {}
            for k in k_values:
                if query_count <= 0:
                    averages[str(k)] = {
                        "recall": None,
                        "hit_rate": None,
                        "mrr": None,
                    }
                    continue

                averages[str(k)] = {
                    metric: round(total / query_count, 6)
                    for metric, total in level_totals[level]["sums"][str(k)].items()
                }

            levels_summary[level] = {
                "queries_with_labels": query_count,
                "queries_without_labels": total_queries - query_count,
                "averages": averages,
            }

        return {
            "dataset_name": dataset.name,
            "dataset_description": dataset.description,
            "total_queries": total_queries,
            "skipped_queries_without_any_labels": skipped_queries,
            "collection_count": len(collection_names),
            "collection_names": list(collection_names),
            "k_values": list(k_values),
            "levels": levels_summary,
            "settings": {
                "enable_rerank": enable_rerank,
                "enable_hybrid": enable_hybrid,
                "enable_multi_source": enable_multi_source,
                "relevance_threshold": relevance_threshold,
            },
        }
