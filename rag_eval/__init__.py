"""Standalone RAG retrieval evaluation toolkit."""

from .dataset import EvalDataset, EvalQuery, FileReference, ChunkReference
from .evaluator import RetrievalEvaluator, resolve_collection_names
from .generator import build_synthetic_dataset, SyntheticEvalDatasetBuilder

__all__ = [
    "EvalDataset",
    "EvalQuery",
    "FileReference",
    "ChunkReference",
    "RetrievalEvaluator",
    "resolve_collection_names",
    "build_synthetic_dataset",
    "SyntheticEvalDatasetBuilder",
]
