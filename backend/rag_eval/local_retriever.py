"""Local corpus retriever for offline RAG evaluation without Flask/Chroma."""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence

from rag_eval.generator import ChunkRecord, load_chunks_from_files


def tokenize(text: str) -> List[str]:
    text = (text or "").lower()
    ascii_tokens = re.findall(r"[a-z0-9_]+", text)
    chinese_chars = re.findall(r"[\u4e00-\u9fff]", text)
    chinese_bigrams = [
        chinese_chars[index] + chinese_chars[index + 1]
        for index in range(len(chinese_chars) - 1)
    ]
    return ascii_tokens + chinese_chars + chinese_bigrams


def get_enriched_text(chunk: ChunkRecord) -> str:
    parts = [chunk.file_name]
    if chunk.section_path:
        parts.append(" ".join(chunk.section_path))
    if chunk.section_title:
        parts.append(chunk.section_title)
    parts.append(chunk.content)
    return " ".join(part for part in parts if part)


@dataclass
class LocalChunkResult:
    content: str
    metadata: Dict[str, Any]
    score: float
    distance: float
    id: str


class SimpleBM25Index:
    """Tiny BM25 implementation suitable for local offline evaluation."""

    def __init__(self, documents: Sequence[ChunkRecord], k1: float = 1.5, b: float = 0.75):
        self.documents = list(documents)
        self.k1 = k1
        self.b = b
        self.doc_tokens: List[List[str]] = [tokenize(get_enriched_text(doc)) for doc in self.documents]
        self.doc_lengths = [len(tokens) for tokens in self.doc_tokens]
        self.avgdl = sum(self.doc_lengths) / len(self.doc_lengths) if self.doc_lengths else 0.0
        self.doc_freqs: Dict[str, int] = {}
        self.term_freqs: List[Dict[str, int]] = []

        for tokens in self.doc_tokens:
            tf: Dict[str, int] = {}
            for token in tokens:
                tf[token] = tf.get(token, 0) + 1
            self.term_freqs.append(tf)
            for token in tf.keys():
                self.doc_freqs[token] = self.doc_freqs.get(token, 0) + 1

        self.doc_count = len(self.documents)

    def score(self, query: str) -> List[float]:
        query_tokens = tokenize(query)
        scores = [0.0 for _ in self.documents]
        if not query_tokens or self.doc_count == 0:
            return scores

        for token in query_tokens:
            df = self.doc_freqs.get(token, 0)
            if df == 0:
                continue
            idf = math.log(1 + (self.doc_count - df + 0.5) / (df + 0.5))

            for index, tf in enumerate(self.term_freqs):
                freq = tf.get(token, 0)
                if freq <= 0:
                    continue
                dl = self.doc_lengths[index] or 1
                denom = freq + self.k1 * (1 - self.b + self.b * dl / (self.avgdl or 1.0))
                scores[index] += idf * (freq * (self.k1 + 1)) / denom

        return scores


class LocalCorpusRAGService:
    """Drop-in query adapter compatible with RetrievalEvaluator."""

    def __init__(self, chunks: Sequence[ChunkRecord]):
        self.chunks = list(chunks)
        self.index = SimpleBM25Index(self.chunks)

    @classmethod
    def from_inputs(
        cls,
        input_paths: Sequence[str],
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        min_chunk_size: int = 200,
        use_markdown_splitter: bool = True,
        min_chars: int = 80,
    ) -> "LocalCorpusRAGService":
        chunks = load_chunks_from_files(
            input_paths=input_paths,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            min_chunk_size=min_chunk_size,
            use_markdown_splitter=use_markdown_splitter,
            min_chars=min_chars,
        )
        if not chunks:
            raise ValueError("No local chunks loaded from the provided inputs.")
        return cls(chunks)

    def query(
        self,
        query: str,
        collection_names: Sequence[str] | None = None,
        n_results: int | None = None,
        enable_rerank: bool = True,
        enable_hybrid: Optional[bool] = None,
        enable_multi_source: Optional[bool] = None,
    ) -> List[Dict[str, Any]]:
        limit = n_results or 10
        scores = self.index.score(query)
        ranked = sorted(
            enumerate(scores),
            key=lambda item: item[1],
            reverse=True,
        )

        results: List[Dict[str, Any]] = []
        for rank, (chunk_idx, score) in enumerate(ranked[:limit], start=1):
            chunk = self.chunks[chunk_idx]
            metadata = {
                "file_name": chunk.file_name,
                "file_id": None,
                "chunk_index": chunk.chunk_index,
                "section_title": chunk.section_title,
                "section_path": chunk.section_path or [],
                "source_file": chunk.file_name,
            }
            results.append(
                {
                    "content": chunk.content,
                    "metadata": metadata,
                    "distance": 1.0 / (1.0 + max(score, 0.0)),
                    "score": score,
                    "id": f"{chunk.file_name}::{chunk.chunk_index}",
                    "collection": "local_corpus",
                    "rank": rank,
                }
            )

        return results


__all__ = [
    "LocalCorpusRAGService",
    "SimpleBM25Index",
    "tokenize",
]
