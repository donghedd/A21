"""Local fallback chunking pipeline for synthetic dataset generation.

Used when the full backend app package cannot be imported.
Supports text and markdown files with the same chunking strategy family
as the main RAG pipeline.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from typing import Dict, List, Optional


@dataclass
class Document:
    page_content: str
    metadata: dict | None = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


def _normalize_content(content: str) -> str:
    if not content:
        return content
    content = content.replace("\ufffd", "")
    content = content.replace("\x00", "")
    content = content.replace("\r\n", "\n").replace("\r", "\n")
    content = re.sub(r"\n{3,}", "\n\n", content)
    return content.strip()


def _read_text_file(file_path: str) -> str:
    encodings = ["utf-8", "utf-8-sig", "gbk", "gb2312", "latin-1"]
    for encoding in encodings:
        try:
            return Path(file_path).read_text(encoding=encoding)
        except (UnicodeDecodeError, UnicodeError):
            continue
    raise ValueError(f"Failed to decode file: {file_path}")


class TextLoader:
    def load(self, file_path: str) -> List[Document]:
        content = _normalize_content(_read_text_file(file_path))
        if not content:
            return []
        path = Path(file_path)
        return [
            Document(
                page_content=content,
                metadata={
                    "source": str(path),
                    "file_name": path.name,
                    "file_type": "text",
                    "file_size": path.stat().st_size,
                },
            )
        ]


class MarkdownLoader(TextLoader):
    pass


def get_loader_for_file(file_path: str, file_type: str | None = None):
    suffix = (file_type or Path(file_path).suffix.lstrip(".")).lower()
    if suffix in {"md", "markdown", "txt"}:
        return MarkdownLoader() if suffix in {"md", "markdown"} else TextLoader()
    raise RuntimeError(
        f"Fallback pipeline only supports text/markdown files, got: {suffix}"
    )


class MarkdownHeaderSplitter:
    def __init__(self, headers_to_split_on: Optional[List[tuple]] = None, strip_headers: bool = False):
        self.headers_to_split_on = headers_to_split_on or [
            ("#", "Header 1"),
            ("##", "Header 2"),
            ("###", "Header 3"),
            ("####", "Header 4"),
            ("#####", "Header 5"),
            ("######", "Header 6"),
        ]
        self.strip_headers = strip_headers

    def split_text(self, text: str, base_metadata: dict | None = None) -> List[Document]:
        base_metadata = base_metadata or {}
        lines = text.split("\n")
        chunks: List[Document] = []
        current_chunk: List[str] = []
        current_headers: Dict[str, str] = {}

        for line in lines:
            is_header = False
            for header_marker, header_name in self.headers_to_split_on:
                match = re.match(f"^{re.escape(header_marker)}\\s+(.+)$", line)
                if not match:
                    continue
                is_header = True
                if current_chunk:
                    content = "\n".join(current_chunk).strip()
                    if content:
                        chunks.append(
                            Document(
                                page_content=content,
                                metadata={
                                    **base_metadata,
                                    **current_headers,
                                    "section_path": self._build_section_path(current_headers),
                                },
                            )
                        )
                    current_chunk = []

                header_level = len(header_marker)
                current_headers[header_name] = match.group(1)
                for marker, name in self.headers_to_split_on:
                    if len(marker) > header_level:
                        current_headers.pop(name, None)
                if not self.strip_headers:
                    current_chunk.append(line)
                break

            if not is_header:
                current_chunk.append(line)

        if current_chunk:
            content = "\n".join(current_chunk).strip()
            if content:
                chunks.append(
                    Document(
                        page_content=content,
                        metadata={
                            **base_metadata,
                            **current_headers,
                            "section_path": self._build_section_path(current_headers),
                        },
                    )
                )

        return chunks or [Document(page_content=text, metadata={**base_metadata, "section_path": []})]

    def _build_section_path(self, headers: Dict[str, str]) -> List[str]:
        path = []
        for _, header_name in self.headers_to_split_on:
            if header_name in headers:
                path.append(headers[header_name])
        return path


class RecursiveCharacterSplitter:
    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200, separators: Optional[List[str]] = None):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.separators = separators or ["\n\n", "\n", ". ", ",", " ", ""]

    def split_text(self, text: str) -> List[str]:
        return self._split_text(text, self.separators)

    def _split_text(self, text: str, separators: List[str]) -> List[str]:
        final_chunks = []
        separator = separators[-1]
        new_separators: List[str] = []

        for index, sep in enumerate(separators):
            if sep == "":
                separator = sep
                break
            if sep in text:
                separator = sep
                new_separators = separators[index + 1 :]
                break

        splits = text.split(separator) if separator else list(text)

        good_splits: List[str] = []
        for split in splits:
            if len(split) < self.chunk_size:
                good_splits.append(split)
                continue

            if good_splits:
                final_chunks.extend(self._merge_splits(good_splits, separator))
                good_splits = []

            if new_separators:
                final_chunks.extend(self._split_text(split, new_separators))
            else:
                final_chunks.append(split)

        if good_splits:
            final_chunks.extend(self._merge_splits(good_splits, separator))

        return final_chunks

    def _merge_splits(self, splits: List[str], separator: str) -> List[str]:
        merged: List[str] = []
        current: List[str] = []
        current_len = 0

        for split in splits:
            split_len = len(split)
            if current_len + split_len + (len(separator) if current else 0) > self.chunk_size:
                if current:
                    merged.append(separator.join(current))
                    while current_len > self.chunk_overlap and current:
                        current_len -= len(current[0]) + len(separator)
                        current.pop(0)

            current.append(split)
            current_len += split_len + (len(separator) if len(current) > 1 else 0)

        if current:
            merged.append(separator.join(current))

        return merged

    def split_documents(self, documents: List[Document]) -> List[Document]:
        result: List[Document] = []
        for doc in documents:
            chunks = self.split_text(doc.page_content)
            for index, chunk in enumerate(chunks):
                result.append(
                    Document(
                        page_content=chunk,
                        metadata={
                            **doc.metadata,
                            "chunk_index": index,
                            "total_chunks": len(chunks),
                        },
                    )
                )
        return result


def merge_small_chunks(chunks: List[Document], min_size: int = 200, max_size: int = 1000) -> List[Document]:
    if not chunks:
        return chunks

    merged: List[Document] = []
    index = 0
    while index < len(chunks):
        current = chunks[index]
        current_len = len(current.page_content)
        if current_len >= min_size or index == len(chunks) - 1:
            merged.append(current)
            index += 1
            continue

        merged_content = current.page_content
        merged_metadata = dict(current.metadata)
        pointer = index + 1

        while pointer < len(chunks) and len(merged_content) < min_size:
            next_chunk = chunks[pointer]
            same_file = current.metadata.get("file_name") == next_chunk.metadata.get("file_name")
            same_section = current.metadata.get("section_path") == next_chunk.metadata.get("section_path")
            if not (same_file and same_section):
                break

            if len(merged_content) + len(next_chunk.page_content) + 2 > max_size:
                break

            merged_content += "\n\n" + next_chunk.page_content
            pointer += 1

        merged.append(Document(page_content=merged_content, metadata=merged_metadata))
        index = pointer

    return merged


def split_documents(
    documents: List[Document],
    chunk_size: int = 1000,
    chunk_overlap: int = 200,
    use_markdown_splitter: bool = True,
    min_chunk_size: int = 200,
) -> List[Document]:
    result = documents

    if use_markdown_splitter:
        md_splitter = MarkdownHeaderSplitter(strip_headers=False)
        new_docs: List[Document] = []
        for doc in result:
            split_docs = md_splitter.split_text(doc.page_content, base_metadata=doc.metadata)
            for split_doc in split_docs:
                new_docs.append(
                    Document(
                        page_content=split_doc.page_content,
                        metadata={**doc.metadata, **split_doc.metadata},
                    )
                )
        result = new_docs
        if min_chunk_size > 0:
            result = merge_small_chunks(result, min_size=min_chunk_size, max_size=chunk_size)

    char_splitter = RecursiveCharacterSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )
    return char_splitter.split_documents(result)


class BaseLoader:
    @staticmethod
    def get_loader_for_file(file_path: str, file_type: str | None = None):
        return get_loader_for_file(file_path, file_type)
