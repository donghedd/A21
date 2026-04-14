"""Fusion retrieval evaluator for document + KG recall metrics."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional, Sequence

from .dataset import EvalDataset, EvalQuery, normalize_k_values
from .evaluator import (
    _chunk_key,
    _file_key,
    _match_chunk_target,
    _match_file_target,
    _normalize_name,
    _temporary_config,
)
from .fusion_retriever import FusionRetriever


FUSION_METRIC_LEVELS = ("file", "chunk", "kg_node", "fusion")


def _kg_node_key(node_id: Optional[str], node_name: Optional[str], labels: Sequence[str] | None = None) -> Optional[str]:
    if node_id:
        return f"id::{node_id.strip()}"

    normalized_name = _normalize_name(node_name)
    if not normalized_name:
        return None

    normalized_labels = sorted(
        label for label in (_normalize_name(item) for item in (labels or [])) if label
    )
    if normalized_labels:
        return f"name::{normalized_name}::labels::{','.join(normalized_labels)}"
    return f"name::{normalized_name}"


def _match_kg_node_target(retrieved: Dict[str, Any], gold: Dict[str, Any]) -> bool:
    gold_node_id = (gold.get("node_id") or "").strip()
    gold_node_name = _normalize_name(gold.get("node_name"))
    gold_labels = {
        label
        for label in (_normalize_name(item) for item in (gold.get("labels") or []))
        if label
    }

    retrieved_node_id = (retrieved.get("node_id") or "").strip()
    retrieved_node_name = _normalize_name(retrieved.get("node_name"))
    retrieved_labels = {
        label
        for label in (
            _normalize_name(item) for item in (retrieved.get("node_labels") or [])
        )
        if label
    }

    if gold_node_id and retrieved_node_id and gold_node_id == retrieved_node_id:
        return True

    if gold_node_name and retrieved_node_name and gold_node_name == retrieved_node_name:
        if gold_labels and retrieved_labels and not (gold_labels & retrieved_labels):
            return False
        return True

    return False


def _match_fusion_target(retrieved: Dict[str, Any], gold: Dict[str, Any]) -> bool:
    kind = gold.get("target_type")
    if kind == "chunk":
        return _match_chunk_target(retrieved, gold)
    if kind == "file":
        return _match_file_target(retrieved, gold)
    if kind == "kg_node":
        return _match_kg_node_target(retrieved, gold)
    return False


class FusionRetrievalEvaluator:
    """Evaluate fused document + KG retrieval with gold labels."""

    def __init__(self, retriever: Optional[FusionRetriever] = None):
        self.retriever = retriever or FusionRetriever()

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
        enable_kg: bool = True,
        document_limit: Optional[int] = None,
        kg_limit: Optional[int] = None,
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
            for level in FUSION_METRIC_LEVELS
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
                    enable_kg=enable_kg,
                    document_limit=document_limit,
                    kg_limit=kg_limit,
                    preview_chars=preview_chars,
                )
                query_reports.append(query_report)

                if query_report["skipped"]:
                    skipped_queries += 1

                for level in FUSION_METRIC_LEVELS:
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
            enable_kg=enable_kg,
            document_limit=document_limit,
            kg_limit=kg_limit,
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
                "enable_hybrid": enable_hybrid,
                "enable_multi_source": enable_multi_source,
                "relevance_threshold": (
                    app.config.get("RELEVANCE_THRESHOLD")
                    if relevance_threshold is None
                    else relevance_threshold
                ),
                "enable_kg": enable_kg,
                "document_limit": document_limit,
                "kg_limit": kg_limit,
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
        enable_kg: bool,
        document_limit: Optional[int],
        kg_limit: Optional[int],
        preview_chars: int,
    ) -> Dict[str, Any]:
        max_k = max(k_values)
        raw_results = self.retriever.retrieve(
            query=example.query,
            collection_names=collection_names,
            top_k=max_k,
            enable_rerank=enable_rerank,
            enable_hybrid=enable_hybrid,
            enable_multi_source=enable_multi_source,
            enable_kg=enable_kg,
            document_limit=document_limit,
            kg_limit=kg_limit,
            preview_chars=preview_chars,
        )

        ranked_results: List[Dict[str, Any]] = []
        retrieved_match_inputs: List[Dict[str, Any]] = []

        for result in raw_results:
            ranked_results.append(
                {
                    "rank": result.get("rank"),
                    "source_type": result.get("source_type"),
                    "file_id": result.get("file_id"),
                    "file_name": result.get("file_name"),
                    "chunk_index": result.get("chunk_index"),
                    "node_id": result.get("node_id"),
                    "node_name": result.get("node_name"),
                    "node_labels": result.get("node_labels") or [],
                    "section_title": result.get("section_title"),
                    "section_path": result.get("section_path"),
                    "score": result.get("score"),
                    "distance": result.get("distance"),
                    "preview": result.get("preview"),
                }
            )
            retrieved_match_inputs.append(
                {
                    "source_type": result.get("source_type"),
                    "file_id": result.get("file_id"),
                    "file_name": result.get("file_name"),
                    "chunk_index": result.get("chunk_index"),
                    "node_id": result.get("node_id"),
                    "node_name": result.get("node_name"),
                    "node_labels": result.get("node_labels") or [],
                }
            )

        gold_file_targets = self._build_gold_file_targets(example)
        gold_chunk_targets = self._build_gold_chunk_targets(example)
        gold_kg_targets = self._build_gold_kg_targets(example)
        gold_fusion_targets = self._build_gold_fusion_targets(example)

        file_evaluation = self._evaluate_level(
            matcher=_match_file_target,
            level="file",
            gold_targets=gold_file_targets,
            retrieved_sequence=retrieved_match_inputs,
            k_values=k_values,
        )
        chunk_evaluation = self._evaluate_level(
            matcher=_match_chunk_target,
            level="chunk",
            gold_targets=gold_chunk_targets,
            retrieved_sequence=retrieved_match_inputs,
            k_values=k_values,
        )
        kg_evaluation = self._evaluate_level(
            matcher=_match_kg_node_target,
            level="kg_node",
            gold_targets=gold_kg_targets,
            retrieved_sequence=retrieved_match_inputs,
            k_values=k_values,
        )
        fusion_evaluation = self._evaluate_level(
            matcher=_match_fusion_target,
            level="fusion",
            gold_targets=gold_fusion_targets,
            retrieved_sequence=retrieved_match_inputs,
            k_values=k_values,
        )

        return {
            "id": example.query_id,
            "query": example.query,
            "notes": example.notes,
            "metadata": example.metadata,
            "skipped": all(
                evaluation["gold_count"] == 0
                for evaluation in (
                    file_evaluation,
                    chunk_evaluation,
                    kg_evaluation,
                    fusion_evaluation,
                )
            ),
            "gold": {
                "files": gold_file_targets["targets"],
                "chunks": gold_chunk_targets["targets"],
                "kg_nodes": gold_kg_targets["targets"],
                "fusion": gold_fusion_targets["targets"],
            },
            "retrieved_results": ranked_results,
            "evaluations": {
                "file": file_evaluation,
                "chunk": chunk_evaluation,
                "kg_node": kg_evaluation,
                "fusion": fusion_evaluation,
            },
        }

    def _build_gold_file_targets(self, example: EvalQuery) -> Dict[str, Any]:
        signatures: List[str] = []
        targets: List[Dict[str, Any]] = []

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
            targets.append({"file_id": item.file_id, "file_name": item.file_name})

        return self._deduplicate_targets(signatures, targets)

    def _build_gold_chunk_targets(self, example: EvalQuery) -> Dict[str, Any]:
        signatures: List[str] = []
        targets: List[Dict[str, Any]] = []

        for item in example.relevant_chunks:
            signature = _chunk_key(item.file_id, item.file_name, item.chunk_index)
            if signature is None:
                continue
            signatures.append(signature)
            targets.append(item.to_dict())

        return self._deduplicate_targets(signatures, targets)

    def _build_gold_kg_targets(self, example: EvalQuery) -> Dict[str, Any]:
        signatures: List[str] = []
        targets: List[Dict[str, Any]] = []

        for item in example.relevant_kg_nodes:
            signature = _kg_node_key(item.node_id, item.node_name, item.labels)
            if signature is None:
                continue
            signatures.append(signature)
            targets.append(item.to_dict())

        return self._deduplicate_targets(signatures, targets)

    def _build_gold_fusion_targets(self, example: EvalQuery) -> Dict[str, Any]:
        signatures: List[str] = []
        targets: List[Dict[str, Any]] = []

        if example.relevant_chunks:
            for item in example.relevant_chunks:
                signature = _chunk_key(item.file_id, item.file_name, item.chunk_index)
                if signature is None:
                    continue
                signatures.append(f"chunk::{signature}")
                target = item.to_dict()
                target["target_type"] = "chunk"
                targets.append(target)
        else:
            for item in example.relevant_files:
                signature = _file_key(item.file_id, item.file_name)
                if signature is None:
                    continue
                signatures.append(f"file::{signature}")
                target = item.to_dict()
                target["target_type"] = "file"
                targets.append(target)

        for item in example.relevant_kg_nodes:
            signature = _kg_node_key(item.node_id, item.node_name, item.labels)
            if signature is None:
                continue
            signatures.append(f"kg::{signature}")
            target = item.to_dict()
            target["target_type"] = "kg_node"
            targets.append(target)

        return self._deduplicate_targets(signatures, targets)

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
        *,
        matcher,
        level: str,
        gold_targets: Dict[str, Any],
        retrieved_sequence: Sequence[Dict[str, Any]],
        k_values: Sequence[int],
    ) -> Dict[str, Any]:
        gold_items = list(gold_targets["targets"])
        gold_count = len(gold_items)

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
        *,
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
        enable_kg: bool,
        document_limit: Optional[int],
        kg_limit: Optional[int],
    ) -> Dict[str, Any]:
        levels_summary: Dict[str, Any] = {}
        for level in FUSION_METRIC_LEVELS:
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
                "enable_kg": enable_kg,
                "document_limit": document_limit,
                "kg_limit": kg_limit,
            },
        }
