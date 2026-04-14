"""
JSON loader with special support for PaddleOCR exported page results.
"""
import json
import os
from typing import List

from .base import BaseLoader, Document


class JsonLoader(BaseLoader):
    """Load JSON files, extracting OCR text when the structure matches PaddleOCR output."""

    def load(self, file_path: str) -> List[Document]:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            documents = self._load_paddleocr_json(data, file_path)
            if documents:
                return documents

            content = self.normalize_content(
                json.dumps(data, ensure_ascii=False, indent=2)
            )
            if not content.strip():
                return []

            file_name = os.path.basename(file_path)
            return [Document(
                page_content=content,
                metadata={
                    'source': file_path,
                    'file_name': file_name,
                    'file_type': 'json',
                    'file_size': os.path.getsize(file_path),
                }
            )]
        except Exception as e:
            raise Exception(f"Failed to load JSON file: {str(e)}")

    def _load_paddleocr_json(self, data, file_path: str) -> List[Document]:
        if not isinstance(data, list):
            return []

        documents = []
        file_name = os.path.basename(file_path)
        total_pages = len(data)

        for idx, page in enumerate(data, start=1):
            if not isinstance(page, dict):
                continue

            text = ""
            markdown = page.get('markdown')
            if isinstance(markdown, dict):
                text = markdown.get('text', '') or ''
            elif isinstance(markdown, str):
                text = markdown

            if not text:
                pruned = page.get('prunedResult', {})
                parsing_res_list = pruned.get('parsing_res_list', []) if isinstance(pruned, dict) else []
                text = '\n\n'.join(
                    block.get('block_content', '').strip()
                    for block in parsing_res_list
                    if isinstance(block, dict) and block.get('block_content')
                )

            text = self.normalize_content(text)
            if not text.strip():
                continue

            documents.append(Document(
                page_content=text,
                metadata={
                    'source': file_path,
                    'file_name': file_name,
                    'file_type': 'ocr_json',
                    'page': idx,
                    'total_pages': total_pages,
                    'source_format': 'paddleocr_json',
                    'file_size': os.path.getsize(file_path),
                }
            ))

        return documents
