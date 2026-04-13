"""Synthetic evaluation dataset generator for RAG retrieval benchmarks."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime
import json
import os
from pathlib import Path
import random
import re
from typing import Any, Dict, Iterable, List, Optional, Sequence

import requests

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover
    load_dotenv = None

from rag_eval.dataset import EvalDataset, EvalQuery, FileReference, ChunkReference, normalize_k_values

try:
    from app.loaders.base import BaseLoader
    from app.utils.text_splitter import split_documents
except Exception:  # pragma: no cover
    from rag_eval.local_pipeline import BaseLoader, split_documents


if load_dotenv is not None:
    load_dotenv()


DEFAULT_EXTENSIONS = [".md", ".markdown", ".txt", ".pdf", ".doc", ".docx", ".xls", ".xlsx"]
DEFAULT_MODES = ["fact", "colloquial", "reasoning"]

MODE_SPECS = {
    "fact": {
        "label": "简单直给",
        "instruction": (
            "针对这段内容生成事实型、可直接定位答案的问题。"
            "问题要清晰、具体，适合检查系统是否能准确召回这一段。"
        ),
    },
    "colloquial": {
        "label": "口语模糊",
        "instruction": (
            "模拟不专业的一线船员，使用自然、口语化、略模糊的提问方式。"
            "问题仍然必须能由这段内容回答。"
        ),
    },
    "reasoning": {
        "label": "推理题",
        "instruction": (
            "如果这段内容包含参数、条件、步骤关系或因果关系，"
            "生成一个需要轻度逻辑推理的问题；如果不适合推理题，可以跳过。"
        ),
    },
}

MODE_ALIASES = {
    "fact": "fact",
    "simple": "fact",
    "direct": "fact",
    "事实": "fact",
    "直给": "fact",
    "colloquial": "colloquial",
    "oral": "colloquial",
    "spoken": "colloquial",
    "口语": "colloquial",
    "模糊": "colloquial",
    "reasoning": "reasoning",
    "infer": "reasoning",
    "推理": "reasoning",
}


@dataclass
class ChunkRecord:
    """A chunk aligned with the current RAG pipeline."""

    file_path: str
    file_name: str
    file_type: str
    chunk_index: int
    content: str
    section_title: str = ""
    section_path: Optional[List[str]] = None
    total_chunks: Optional[int] = None

    def to_query_metadata(self, mode: str, model: str) -> Dict[str, Any]:
        return {
            "synthetic": True,
            "generation_mode": mode,
            "generator_model": model,
            "source_file_path": self.file_path,
            "source_file_name": self.file_name,
            "source_chunk_index": self.chunk_index,
            "section_title": self.section_title,
            "section_path": self.section_path or [],
            "chunk_char_count": len(self.content),
            "source_preview": _truncate_preview(self.content, limit=220),
        }


def _truncate_preview(text: str, limit: int = 220) -> str:
    compact = " ".join((text or "").split())
    if len(compact) <= limit:
        return compact
    return compact[: limit - 3] + "..."


def _normalize_query_text(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip())


def _resolve_modes(modes: Sequence[str]) -> List[str]:
    resolved: List[str] = []
    for item in modes:
        key = MODE_ALIASES.get((item or "").strip().lower())
        if key is None:
            raise ValueError(f"Unsupported mode: {item}")
        if key not in resolved:
            resolved.append(key)
    if not resolved:
        return list(DEFAULT_MODES)
    return resolved


def _collect_files(inputs: Sequence[str], extensions: Sequence[str], recursive: bool = True) -> List[Path]:
    normalized_exts = {
        ext if ext.startswith(".") else f".{ext}"
        for ext in (item.lower() for item in extensions)
    }

    collected: List[Path] = []
    for raw in inputs:
        path = Path(raw).expanduser()
        if not path.exists():
            raise FileNotFoundError(f"Input path not found: {path}")

        if path.is_file():
            if path.suffix.lower() in normalized_exts:
                collected.append(path.resolve())
            continue

        iterator = path.rglob("*") if recursive else path.glob("*")
        for child in iterator:
            if child.is_file() and child.suffix.lower() in normalized_exts:
                collected.append(child.resolve())

    unique: List[Path] = []
    seen = set()
    for item in sorted(collected):
        marker = str(item).lower()
        if marker in seen:
            continue
        seen.add(marker)
        unique.append(item)
    return unique


def _file_type_from_path(path: Path) -> str:
    return path.suffix.lower().lstrip(".")


def load_chunks_from_files(
    input_paths: Sequence[str],
    chunk_size: int = 1000,
    chunk_overlap: int = 200,
    min_chunk_size: int = 200,
    use_markdown_splitter: bool = True,
    extensions: Sequence[str] = DEFAULT_EXTENSIONS,
    recursive: bool = True,
    min_chars: int = 80,
) -> List[ChunkRecord]:
    files = _collect_files(input_paths, extensions=extensions, recursive=recursive)
    all_chunks: List[ChunkRecord] = []

    for file_path in files:
        loader = BaseLoader.get_loader_for_file(str(file_path), _file_type_from_path(file_path))
        documents = loader.load(str(file_path))
        if not documents:
            continue

        for doc in documents:
            doc.metadata["source_file"] = file_path.name
            doc.metadata["file_name"] = file_path.name

        chunks = split_documents(
            documents,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            use_markdown_splitter=use_markdown_splitter,
            min_chunk_size=min_chunk_size,
        )

        for global_chunk_index, chunk in enumerate(chunks):
            content = (chunk.page_content or "").strip()
            if len(content) < min_chars:
                continue

            metadata = chunk.metadata or {}
            section_path = metadata.get("section_path") or []
            if isinstance(section_path, str):
                section_path = [item.strip() for item in section_path.split(">") if item.strip()]

            section_title = (
                metadata.get("Header 3")
                or metadata.get("Header 2")
                or metadata.get("Header 1")
                or ""
            )

            all_chunks.append(
                ChunkRecord(
                    file_path=str(file_path),
                    file_name=file_path.name,
                    file_type=_file_type_from_path(file_path),
                    chunk_index=global_chunk_index,
                    content=content,
                    section_title=section_title,
                    section_path=section_path,
                    total_chunks=len(chunks),
                )
            )

    return all_chunks


def _strip_code_fences(text: str) -> str:
    stripped = (text or "").strip()
    if stripped.startswith("```"):
        stripped = re.sub(r"^```[a-zA-Z0-9_-]*\s*", "", stripped)
        stripped = re.sub(r"\s*```$", "", stripped)
    return stripped.strip()


def _extract_json_payload(text: str) -> Any:
    stripped = _strip_code_fences(text)
    candidates = [stripped]

    left_bracket = stripped.find("[")
    right_bracket = stripped.rfind("]")
    if left_bracket != -1 and right_bracket != -1 and right_bracket > left_bracket:
        candidates.append(stripped[left_bracket:right_bracket + 1])

    left_brace = stripped.find("{")
    right_brace = stripped.rfind("}")
    if left_brace != -1 and right_brace != -1 and right_brace > left_brace:
        candidates.append(stripped[left_brace:right_brace + 1])

    seen = set()
    for candidate in candidates:
        if candidate in seen:
            continue
        seen.add(candidate)
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            continue

    raise ValueError("Model output is not valid JSON")


class OllamaQuestionGenerator:
    """Generate synthetic questions from chunk text using Ollama."""

    def __init__(
        self,
        model: str,
        base_url: Optional[str] = None,
        temperature: float = 0.3,
        timeout: int = 300,
        questions_per_mode: int = 1,
    ):
        self.model = model
        self.base_url = (base_url or os.getenv("OLLAMA_BASE_URL") or "http://localhost:11434").rstrip("/")
        self.temperature = temperature
        self.timeout = timeout
        self.questions_per_mode = questions_per_mode

    def generate(self, chunk: ChunkRecord, modes: Sequence[str]) -> List[Dict[str, Any]]:
        system_prompt = (
            "你是一个RAG检索评测集生成助手。"
            "你只能根据给定chunk内容出题，不允许引入chunk外知识。"
            "输出必须是严格JSON数组，不要输出解释、前后缀、Markdown。"
            "数组元素字段固定为 mode, query, notes。"
            "query 必须是可以直接拿去做用户提问的自然语言。"
            "不要在 query 里出现“根据本文”“根据这段内容”“本段提到”等措辞。"
            "如果某个模式不适合当前chunk，可以省略该项。"
        )

        mode_lines = []
        for mode in modes:
            spec = MODE_SPECS[mode]
            mode_lines.append(
                f'- mode="{mode}" ({spec["label"]}): {spec["instruction"]} '
                f'每种模式最多生成 {self.questions_per_mode} 个问题。'
            )

        section_path = " > ".join(chunk.section_path or [])
        user_prompt = "\n".join(
            [
                "请基于下面的chunk生成合成评测问题。",
                "返回格式示例：",
                '[{"mode":"fact","query":"...","notes":"为什么这个问题适合该chunk"}]',
                "要求：",
                "- 问题必须能由这个chunk本身回答。",
                "- 优先生成具有检索辨识度的问题，避免过泛的问法。",
                "- 如果chunk太短、信息不足或不适合某种模式，可以不生成该模式。",
                "- notes 用一句短话说明该问题覆盖的知识点。",
                "",
                "模式列表：",
                *mode_lines,
                "",
                f"文件名: {chunk.file_name}",
                f"chunk_index: {chunk.chunk_index}",
                f"章节标题: {chunk.section_title or '(无)'}",
                f"章节路径: {section_path or '(无)'}",
                "",
                "chunk内容：",
                chunk.content,
            ]
        )

        content = self._chat(system_prompt=system_prompt, user_prompt=user_prompt)
        parsed = _extract_json_payload(content)

        if isinstance(parsed, dict):
            parsed = parsed.get("questions") or parsed.get("items") or [parsed]

        if not isinstance(parsed, list):
            raise ValueError("Model output must be a JSON list")

        cleaned: List[Dict[str, Any]] = []
        per_mode_count: Dict[str, int] = {}

        for item in parsed:
            if not isinstance(item, dict):
                continue
            mode = MODE_ALIASES.get(str(item.get("mode", "")).strip().lower())
            if mode not in modes:
                continue

            query = _normalize_query_text(item.get("query"))
            if not query:
                continue

            per_mode_count.setdefault(mode, 0)
            if per_mode_count[mode] >= self.questions_per_mode:
                continue

            cleaned.append(
                {
                    "mode": mode,
                    "query": query,
                    "notes": _normalize_query_text(item.get("notes")),
                }
            )
            per_mode_count[mode] += 1

        return cleaned

    def _chat(self, system_prompt: str, user_prompt: str) -> str:
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "stream": False,
            "options": {
                "temperature": self.temperature,
            },
        }

        response = requests.post(
            f"{self.base_url}/api/chat",
            json=payload,
            timeout=self.timeout,
        )

        if response.status_code == 404:
            return self._generate(system_prompt=system_prompt, user_prompt=user_prompt)

        response.raise_for_status()
        data = response.json()
        return data.get("message", {}).get("content", "")

    def _generate(self, system_prompt: str, user_prompt: str) -> str:
        payload = {
            "model": self.model,
            "system": system_prompt,
            "prompt": user_prompt,
            "stream": False,
            "options": {
                "temperature": self.temperature,
            },
        }

        response = requests.post(
            f"{self.base_url}/api/generate",
            json=payload,
            timeout=self.timeout,
        )
        response.raise_for_status()
        data = response.json()
        return data.get("response", "")


class SyntheticEvalDatasetBuilder:
    """Build a labeled evaluation dataset from source chunks."""

    def __init__(self, question_generator):
        self.question_generator = question_generator

    def build(
        self,
        chunks: Sequence[ChunkRecord],
        modes: Sequence[str],
        dataset_name: str = "",
        dataset_description: str = "",
        k_values: Sequence[int] = (1, 3, 5, 10),
        max_questions: Optional[int] = None,
    ) -> EvalDataset:
        queries: List[EvalQuery] = []
        seen_queries = set()
        query_index = 1

        for chunk in chunks:
            generated_items = self.question_generator.generate(chunk, modes)
            for item in generated_items:
                normalized = _normalize_query_text(item["query"])
                marker = normalized.lower()
                if marker in seen_queries:
                    continue
                seen_queries.add(marker)

                metadata = chunk.to_query_metadata(
                    mode=item["mode"],
                    model=getattr(self.question_generator, "model", "unknown"),
                )
                metadata["generator_notes"] = item.get("notes", "")

                queries.append(
                    EvalQuery(
                        query=normalized,
                        query_id=f"auto_q{query_index:04d}",
                        notes=item.get("notes", ""),
                        relevant_files=[
                            FileReference(file_name=chunk.file_name)
                        ],
                        relevant_chunks=[
                            ChunkReference(
                                file_name=chunk.file_name,
                                chunk_index=chunk.chunk_index,
                            )
                        ],
                        metadata=metadata,
                    )
                )
                query_index += 1

                if max_questions is not None and len(queries) >= max_questions:
                    return EvalDataset(
                        queries=queries,
                        name=dataset_name,
                        description=dataset_description,
                        k_values=normalize_k_values(k_values),
                        metadata={},
                    )

        return EvalDataset(
            queries=queries,
            name=dataset_name,
            description=dataset_description,
            k_values=normalize_k_values(k_values),
            metadata={},
        )


def build_synthetic_dataset(
    input_paths: Sequence[str],
    model: str,
    output_path: str,
    modes: Sequence[str] = DEFAULT_MODES,
    chunk_size: int = 1000,
    chunk_overlap: int = 200,
    min_chunk_size: int = 200,
    min_chars: int = 80,
    use_markdown_splitter: bool = True,
    extensions: Sequence[str] = DEFAULT_EXTENSIONS,
    recursive: bool = True,
    shuffle: bool = False,
    random_seed: int = 42,
    max_chunks: Optional[int] = None,
    max_questions: Optional[int] = None,
    questions_per_mode: int = 1,
    temperature: float = 0.3,
    ollama_base_url: Optional[str] = None,
    timeout: int = 300,
    dataset_name: str = "",
    dataset_description: str = "",
    k_values: Sequence[int] = (1, 3, 5, 10),
) -> Path:
    resolved_modes = _resolve_modes(modes)
    chunks = load_chunks_from_files(
        input_paths=input_paths,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        min_chunk_size=min_chunk_size,
        use_markdown_splitter=use_markdown_splitter,
        extensions=extensions,
        recursive=recursive,
        min_chars=min_chars,
    )

    if not chunks:
        raise ValueError("No eligible chunks found. Check --input, --extensions, or --min-chars.")

    if shuffle:
        random.Random(random_seed).shuffle(chunks)

    if max_chunks is not None:
        chunks = list(chunks[:max_chunks])

    generator = OllamaQuestionGenerator(
        model=model,
        base_url=ollama_base_url,
        temperature=temperature,
        timeout=timeout,
        questions_per_mode=questions_per_mode,
    )
    builder = SyntheticEvalDatasetBuilder(question_generator=generator)
    dataset = builder.build(
        chunks=chunks,
        modes=resolved_modes,
        dataset_name=dataset_name,
        dataset_description=dataset_description,
        k_values=k_values,
        max_questions=max_questions,
    )

    dataset.metadata = {
        "name": dataset_name,
        "description": dataset_description,
        "default_k_values": normalize_k_values(k_values),
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "generator": {
            "type": "synthetic",
            "model": model,
            "modes": resolved_modes,
            "questions_per_mode": questions_per_mode,
            "temperature": temperature,
        },
        "chunking": {
            "chunk_size": chunk_size,
            "chunk_overlap": chunk_overlap,
            "min_chunk_size": min_chunk_size,
            "min_chars": min_chars,
            "use_markdown_splitter": use_markdown_splitter,
        },
        "source_files": sorted({chunk.file_name for chunk in chunks}),
        "source_file_count": len({chunk.file_path for chunk in chunks}),
        "source_chunk_count": len(chunks),
        "annotation_tips": [
            "这是自动生成的合成评测集，建议人工抽检后再用于正式基准。",
            "如果后续文件上传到知识库时改了文件名，请同步更新 relevant_files / relevant_chunks 里的 file_name。",
            "当前 chunk_index 已按现有 RAG 入库逻辑使用文件内全局递增索引生成。",
        ],
    }

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    dataset.save(output)
    return output


def _add_generate_samples_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--input",
        action="append",
        required=True,
        help="Input file or directory. Can be provided multiple times",
    )
    parser.add_argument("--output", required=True, help="Output JSON path")
    parser.add_argument(
        "--model",
        default=os.getenv("OLLAMA_DEFAULT_MODEL") or "qwen2.5:7b",
        help="Ollama model used to generate synthetic questions",
    )
    parser.add_argument(
        "--ollama-base-url",
        default=os.getenv("OLLAMA_BASE_URL") or "http://localhost:11434",
        help="Ollama base URL",
    )
    parser.add_argument(
        "--mode",
        action="append",
        default=[],
        help="Generation mode: fact, colloquial, reasoning. Can be provided multiple times",
    )
    parser.add_argument(
        "--questions-per-mode",
        type=int,
        default=1,
        help="Maximum generated questions for each selected mode per chunk",
    )
    parser.add_argument("--chunk-size", type=int, default=int(os.getenv("CHUNK_SIZE", 1000)))
    parser.add_argument("--chunk-overlap", type=int, default=int(os.getenv("CHUNK_OVERLAP", 200)))
    parser.add_argument("--min-chunk-size", type=int, default=int(os.getenv("CHUNK_MIN_SIZE", 200)))
    parser.add_argument("--min-chars", type=int, default=80, help="Skip chunks shorter than this")
    parser.add_argument(
        "--disable-markdown-splitter",
        action="store_true",
        help="Disable markdown header splitting before recursive chunking",
    )
    parser.add_argument(
        "--extensions",
        nargs="+",
        default=DEFAULT_EXTENSIONS,
        help="Accepted file extensions, e.g. .md .txt .pdf",
    )
    parser.add_argument(
        "--no-recursive",
        action="store_true",
        help="Do not recursively scan directories",
    )
    parser.add_argument("--shuffle", action="store_true", help="Shuffle chunks before generation")
    parser.add_argument("--random-seed", type=int, default=42)
    parser.add_argument("--max-chunks", type=int, default=None)
    parser.add_argument("--max-questions", type=int, default=None)
    parser.add_argument("--temperature", type=float, default=0.3)
    parser.add_argument("--timeout", type=int, default=300)
    parser.add_argument("--name", default="", help="Dataset name")
    parser.add_argument("--description", default="", help="Dataset description")
    parser.add_argument(
        "--k",
        nargs="+",
        type=int,
        default=[1, 3, 5, 10],
        help="Default K values to embed into the dataset metadata",
    )


def add_generate_samples_subparser(subparsers) -> None:
    parser = subparsers.add_parser(
        "generate-samples",
        help="Generate a synthetic labeled evaluation dataset from local files",
    )
    _add_generate_samples_arguments(parser)


def run_generate_samples_command(args: argparse.Namespace) -> int:
    resolved_modes = _resolve_modes(args.mode or DEFAULT_MODES)
    output_path = build_synthetic_dataset(
        input_paths=args.input,
        model=args.model,
        output_path=args.output,
        modes=resolved_modes,
        chunk_size=args.chunk_size,
        chunk_overlap=args.chunk_overlap,
        min_chunk_size=args.min_chunk_size,
        min_chars=args.min_chars,
        use_markdown_splitter=not args.disable_markdown_splitter,
        extensions=args.extensions,
        recursive=not args.no_recursive,
        shuffle=args.shuffle,
        random_seed=args.random_seed,
        max_chunks=args.max_chunks,
        max_questions=args.max_questions,
        questions_per_mode=args.questions_per_mode,
        temperature=args.temperature,
        ollama_base_url=args.ollama_base_url,
        timeout=args.timeout,
        dataset_name=args.name,
        dataset_description=args.description,
        k_values=args.k,
    )

    dataset = EvalDataset.load(output_path)

    print(f"Synthetic dataset written to: {output_path}")
    print(f"Modes: {', '.join(resolved_modes)}")
    print(f"Model: {args.model}")
    print(f"Queries: {len(dataset.queries)}")
    return 0


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Generate synthetic RAG evaluation datasets from local files"
    )
    _add_generate_samples_arguments(parser)
    args = parser.parse_args(argv)
    return run_generate_samples_command(args)


__all__ = [
    "ChunkRecord",
    "OllamaQuestionGenerator",
    "SyntheticEvalDatasetBuilder",
    "build_synthetic_dataset",
    "add_generate_samples_subparser",
    "run_generate_samples_command",
    "main",
]
