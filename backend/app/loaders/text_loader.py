"""
Text File Loader - Reference: Open WebUI's TextLoader
Enhanced with auto-detect encoding and content normalization.
"""
import os
from typing import List
from .base import BaseLoader, Document


class TextLoader(BaseLoader):
    """Load plain text files.
    
    Reference: Open WebUI's TextLoader with autodetect_encoding=True
    (retrieval/loaders/main.py L424, L484)
    Key features:
    - Auto-detect encoding (tries multiple encodings)
    - Content normalization
    - Comprehensive metadata tracking
    """
    
    def load(self, file_path: str) -> List[Document]:
        """Load text file with auto-detect encoding."""
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
                file_name = os.path.basename(file_path)
                
                return [Document(
                    page_content=content,
                    metadata={
                        'source': file_path,
                        'file_name': file_name,
                        'file_type': 'text',
                        'file_size': os.path.getsize(file_path),
                    }
                )]
            return []
            
        except Exception as e:
            raise Exception(f"Failed to load text file: {str(e)}")
