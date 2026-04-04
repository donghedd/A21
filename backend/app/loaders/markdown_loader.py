"""
Markdown File Loader - Reference: Open WebUI's TextLoader for .md files
Enhanced with content normalization and better metadata tracking.
"""
import os
from typing import List
from .base import BaseLoader, Document


class MarkdownLoader(BaseLoader):
    """Load Markdown files.
    
    Reference: Open WebUI uses TextLoader for .md files (retrieval/loaders/main.py L424)
    Key features:
    - Auto-detect encoding
    - Content normalization
    - Comprehensive metadata
    """
    
    def load(self, file_path: str) -> List[Document]:
        """Load Markdown file with content normalization."""
        try:
            # Try multiple encodings like Open WebUI's autodetect_encoding
            content = None
            encodings = ['utf-8', 'utf-8-sig', 'gbk', 'gb2312', 'latin-1']
            
            for encoding in encodings:
                try:
                    with open(file_path, 'r', encoding=encoding) as f:
                        content = f.read()
                    break
                except (UnicodeDecodeError, UnicodeError):
                    continue
            
            if content is None:
                raise ValueError(f"Failed to decode file with encodings: {encodings}")
            
            # Normalize content (fix encoding issues, line endings, etc.)
            content = self.normalize_content(content)
            
            if content.strip():
                # Extract filename without extension for better metadata
                file_name = os.path.basename(file_path)
                
                return [Document(
                    page_content=content,
                    metadata={
                        'source': file_path,
                        'file_name': file_name,
                        'file_type': 'markdown',
                        'file_size': os.path.getsize(file_path),
                    }
                )]
            return []
            
        except Exception as e:
            raise Exception(f"Failed to load Markdown file: {str(e)}")
