"""Dataset parsing helpers for RAG retrieval evaluation."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence
import json


def _clean_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _unique_preserve_order(items: Iterable[Any]) -> List[Any]:
    result: List[Any] = []
    seen = set()
    for item in items:
        marker = json.dumps(item, ensure_ascii=False, sort_keys=True)
        if marker in seen:
            continue
        seen.add(marker)
        result.append(item)
    return result


@dataclass(frozen=True)
class FileReference:
    """A gold reference at file level."""

    file_id: Optional[str] = None
    file_name: Optional[str] = None

    @classmethod
    def from_raw(cls, raw: Any) -> "FileReference":
        if isinstance(raw, str):
            file_name = _clean_text(raw)
            if not file_name:
                raise ValueError("File reference string cannot be empty")
            return cls(file_name=file_name)

        if not isinstance(raw, dict):
            raise ValueError("File reference must be a string or object")

        file_id = _clean_text(raw.get("file_id")) or None
        file_name = _clean_text(
            raw.get("file_name") or raw.get("filename") or raw.get("file")
        ) or None

        if not file_id and not file_name:
            raise ValueError("File reference must include file_id or file_name")

        return cls(file_id=file_id, file_name=file_name)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "file_id": self.file_id,
            "file_name": self.file_name,
        }


@dataclass(frozen=True)
class ChunkReference:
    """A gold reference at chunk level."""

    chunk_index: int
    file_id: Optional[str] = None
    file_name: Optional[str] = None

    @classmethod
    def from_raw(cls, raw: Any) -> "ChunkReference":
        if not isinstance(raw, dict):
            raise ValueError("Chunk reference must be an object")

        if "chunk_index" not in raw:
            raise ValueError("Chunk reference must include chunk_index")

        try:
            chunk_index = int(raw["chunk_index"])
        except (TypeError, ValueError) as exc:
            raise ValueError("chunk_index must be an integer") from exc

        file_id = _clean_text(raw.get("file_id")) or None
        file_name = _clean_text(
            raw.get("file_name") or raw.get("filename") or raw.get("file")
        ) or None

        if not file_id and not file_name:
            raise ValueError("Chunk reference must include file_id or file_name")

        return cls(
            chunk_index=chunk_index,
            file_id=file_id,
            file_name=file_name,
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "file_id": self.file_id,
            "file_name": self.file_name,
            "chunk_index": self.chunk_index,
        }


@dataclass(frozen=True)
class KGNodeReference:
    """A gold reference for a knowledge-graph node."""

    node_id: Optional[str] = None
    node_name: Optional[str] = None
    labels: List[str] = field(default_factory=list)

    @classmethod
    def from_raw(cls, raw: Any) -> "KGNodeReference":
        if isinstance(raw, str):
            node_name = _clean_text(raw)
            if not node_name:
                raise ValueError("KG node reference string cannot be empty")
            return cls(node_name=node_name)

        if not isinstance(raw, dict):
            raise ValueError("KG node reference must be a string or object")

        node_id = _clean_text(raw.get("node_id") or raw.get("id")) or None
        node_name = _clean_text(
            raw.get("node_name") or raw.get("name") or raw.get("node")
        ) or None

        labels_raw = raw.get("labels") or raw.get("node_labels") or []
        if labels_raw is None:
            labels_raw = []
        if not isinstance(labels_raw, list):
            raise ValueError("KG node reference labels must be a list")

        labels = [_clean_text(item) for item in labels_raw if _clean_text(item)]

        if not node_id and not node_name:
            raise ValueError("KG node reference must include node_id or node_name")

        return cls(node_id=node_id, node_name=node_name, labels=labels)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node_id": self.node_id,
            "node_name": self.node_name,
            "labels": list(self.labels),
        }


@dataclass
class EvalQuery:
    """One retrieval evaluation query."""

    query: str
    query_id: str
    notes: str = ""
    relevant_files: List[FileReference] = field(default_factory=list)
    relevant_chunks: List[ChunkReference] = field(default_factory=list)
    relevant_kg_nodes: List[KGNodeReference] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_raw(cls, raw: Dict[str, Any], index: int) -> "EvalQuery":
        if not isinstance(raw, dict):
            raise ValueError("Each query item must be an object")

        query = _clean_text(raw.get("query") or raw.get("question"))
        if not query:
            raise ValueError(f"Query at index {index} is missing query/question")

        query_id = _clean_text(raw.get("id")) or f"q{index:03d}"
        notes = _clean_text(raw.get("notes"))

        relevant_files_raw = raw.get("relevant_files") or raw.get("gold_files") or []
        relevant_chunks_raw = raw.get("relevant_chunks") or raw.get("gold_chunks") or []
        relevant_kg_nodes_raw = (
            raw.get("relevant_kg_nodes")
            or raw.get("gold_kg_nodes")
            or raw.get("relevant_nodes")
            or []
        )

        relevant_files = [FileReference.from_raw(item) for item in relevant_files_raw]
        relevant_chunks = [ChunkReference.from_raw(item) for item in relevant_chunks_raw]
        relevant_kg_nodes = [
            KGNodeReference.from_raw(item) for item in relevant_kg_nodes_raw
        ]

        metadata = raw.get("metadata") if isinstance(raw.get("metadata"), dict) else {}

        return cls(
            query=query,
            query_id=query_id,
            notes=notes,
            relevant_files=relevant_files,
            relevant_chunks=relevant_chunks,
            relevant_kg_nodes=relevant_kg_nodes,
            metadata=metadata,
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.query_id,
            "query": self.query,
            "notes": self.notes,
            "relevant_files": [item.to_dict() for item in self.relevant_files],
            "relevant_chunks": [item.to_dict() for item in self.relevant_chunks],
            "relevant_kg_nodes": [item.to_dict() for item in self.relevant_kg_nodes],
            "metadata": self.metadata,
        }


@dataclass
class EvalDataset:
    """The full evaluation dataset."""

    queries: List[EvalQuery]
    name: str = ""
    description: str = ""
    k_values: List[int] = field(default_factory=lambda: [1, 3, 5, 10])
    metadata: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_raw(cls, raw: Any) -> "EvalDataset":
        if isinstance(raw, list):
            metadata: Dict[str, Any] = {}
            queries_raw = raw
            name = ""
            description = ""
            k_values = [1, 3, 5, 10]
        elif isinstance(raw, dict):
            metadata = raw.get("metadata") if isinstance(raw.get("metadata"), dict) else {}
            queries_raw = raw.get("queries")
            if not isinstance(queries_raw, list):
                raise ValueError("Dataset JSON must contain a 'queries' array")

            name = _clean_text(raw.get("name") or metadata.get("name"))
            description = _clean_text(
                raw.get("description") or metadata.get("description")
            )

            k_values = raw.get("k_values") or metadata.get("default_k_values") or [1, 3, 5, 10]
        else:
            raise ValueError("Dataset JSON must be an object or list")

        parsed_k_values = normalize_k_values(k_values)
        queries = [EvalQuery.from_raw(item, index + 1) for index, item in enumerate(queries_raw)]

        return cls(
            queries=queries,
            name=name,
            description=description,
            k_values=parsed_k_values,
            metadata=metadata,
        )

    @classmethod
    def load(cls, path: str | Path) -> "EvalDataset":
        raw = _load_json(Path(path))
        return cls.from_raw(raw)

    def to_dict(self) -> Dict[str, Any]:
        metadata = dict(self.metadata)
        if self.name:
            metadata.setdefault("name", self.name)
        if self.description:
            metadata.setdefault("description", self.description)
        metadata.setdefault("default_k_values", self.k_values)

        return {
            "metadata": metadata,
            "queries": [item.to_dict() for item in self.queries],
        }

    def save(self, path: str | Path) -> Path:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("w", encoding="utf-8") as handle:
            json.dump(self.to_dict(), handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        return target


def normalize_k_values(k_values: Sequence[Any]) -> List[int]:
    if not k_values:
        return [1, 3, 5, 10]

    parsed: List[int] = []
    for item in k_values:
        try:
            value = int(item)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Invalid k value: {item}") from exc
        if value <= 0:
            raise ValueError("k values must be positive integers")
        parsed.append(value)

    return sorted(set(parsed))


def load_questions(path: str | Path) -> List[Dict[str, str]]:
    """Load questions from .txt or .json into a normalized list."""

    source = Path(path)
    if not source.exists():
        raise FileNotFoundError(f"Questions file not found: {source}")

    if source.suffix.lower() == ".txt":
        lines = [
            line.strip()
            for line in source.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        return [{"id": f"q{index + 1:03d}", "query": line} for index, line in enumerate(lines)]

    payload = _load_json(source)

    if isinstance(payload, dict):
        payload = payload.get("queries", [])

    if not isinstance(payload, list):
        raise ValueError("Questions JSON must be a list or an object containing a queries list")

    normalized: List[Dict[str, str]] = []
    for index, item in enumerate(payload, start=1):
        if isinstance(item, str):
            query = item.strip()
            if not query:
                continue
            normalized.append({"id": f"q{index:03d}", "query": query})
            continue

        if not isinstance(item, dict):
            raise ValueError("Each question must be a string or object")

        query = _clean_text(item.get("query") or item.get("question"))
        if not query:
            raise ValueError(f"Question item at index {index} is missing query/question")

        query_id = _clean_text(item.get("id")) or f"q{index:03d}"
        normalized.append({"id": query_id, "query": query})

    return normalized


def build_template_dataset(
    questions: Sequence[Dict[str, str]],
    k_values: Sequence[int],
    name: str = "",
    description: str = "",
) -> EvalDataset:
    queries = [
        EvalQuery(
            query=item["query"],
            query_id=item["id"],
            relevant_files=[],
            relevant_chunks=[],
            relevant_kg_nodes=[],
        )
        for item in questions
    ]

    dataset = EvalDataset(
        queries=queries,
        name=name,
        description=description,
        k_values=normalize_k_values(k_values),
        metadata={
            "annotation_tips": [
                "relevant_files 适合做 file-level Recall@K",
                "relevant_chunks 适合做 chunk-level Recall@K",
                "如果只标了 relevant_chunks，系统也会自动推导 file-level gold set",
            ]
        },
    )

    dataset.metadata["annotation_tips"] = [
        "relevant_files 适合做 file-level Recall@K",
        "relevant_chunks 适合做 chunk-level Recall@K",
        "relevant_kg_nodes 适合做 KG node Recall@K",
        "如果只标了 relevant_chunks，系统也会自动推导 file-level gold set",
        "融合评测时，文档 gold 优先用 relevant_chunks，没有 chunk 时退化为 relevant_files",
    ]

    for query in dataset.queries:
        query.metadata = {
            "label_status": "todo",
            "comment": "",
        }

    return dataset


def write_json(path: str | Path, payload: Dict[str, Any]) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    return target


def deduplicate_dict_items(items: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return _unique_preserve_order(items)
