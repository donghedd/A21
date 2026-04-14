"""Standalone RAG retrieval evaluation toolkit."""

from .dataset import (
    ChunkReference,
    EvalDataset,
    EvalQuery,
    FileReference,
    KGNodeReference,
)
from .evaluator import RetrievalEvaluator, resolve_collection_names
from .fusion_evaluator import FusionRetrievalEvaluator
from .generator import build_synthetic_dataset, SyntheticEvalDatasetBuilder

__all__ = [
    "EvalDataset",
    "EvalQuery",
    "FileReference",
    "ChunkReference",
    "KGNodeReference",
    "RetrievalEvaluator",
    "FusionRetrievalEvaluator",
    "resolve_collection_names",
    "build_synthetic_dataset",
    "SyntheticEvalDatasetBuilder",
]
