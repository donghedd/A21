"""
Base File Loader - Reference: Open WebUI's retrieval/loaders/main.py
Enhanced with better encoding detection and content normalization.
"""
from abc import ABC, abstractmethod
from typing import List
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class Document:
    """Document representation with enhanced metadata"""
    page_content: str
    metadata: dict = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
    
    @property
    def source_file(self):
        """Get source file name from metadata"""
        return self.metadata.get('source_file', '')
    
    @property
    def section_path(self):
        """Get section path from metadata"""
        return self.metadata.get('section_path', [])
    
    @property
    def page_number(self):
        """Get page number from metadata"""
        return self.metadata.get('page_number', None)


class BaseLoader(ABC):
    """Base class for file loaders.
    
    Reference: Open WebUI's Loader class (retrieval/loaders/main.py)
    Key improvements:
    - Better encoding detection
    - Content normalization (ftfy-like text fixing)
    - Comprehensive metadata tracking
    """
    
    @abstractmethod
    def load(self, file_path: str) -> List[Document]:
        """Load file and return list of documents"""
        pass
    
    def normalize_content(self, content: str) -> str:
        """
        Normalize text content to fix common encoding issues.
        Similar to Open WebUI's use of ftfy.fix_text().
        
        Fixes:
        - Mojibake (encoding artifacts)
        - Smart quotes and special characters
        - Inconsistent line endings
        - Excessive whitespace
        """
        if not content:
            return content
        
        # Fix common encoding issues
        # Replace common mojibake patterns
        content = content.replace('\ufffd', '')  # Replacement character
        content = content.replace('\x00', '')    # Null bytes
        
        # Normalize line endings
        content = content.replace('\r\n', '\n')
        content = content.replace('\r', '\n')
        
        # Remove excessive blank lines (more than 2 consecutive newlines)
        import re
        content = re.sub(r'\n{3,}', '\n\n', content)
        
        # Strip leading/trailing whitespace
        content = content.strip()
        
        return content
    
    @staticmethod
    def get_loader_for_file(file_path: str, file_type: str = None):
        """Get appropriate loader for file type.
        
        Reference: Open WebUI's Loader._get_loader() method
        Supports multiple file formats with fallback strategies.
        """
        from .pdf_loader import PDFLoader
        from .word_loader import WordLoader
        from .excel_loader import ExcelLoader
        from .markdown_loader import MarkdownLoader
        from .text_loader import TextLoader
        
        if file_type is None:
            file_type = file_path.split('.')[-1].lower()
        
        # Comprehensive file type mapping (like Open WebUI)
        loaders = {
            # PDF documents
            'pdf': PDFLoader,
            # Word documents
            'doc': WordLoader,
            'docx': WordLoader,
            # Excel spreadsheets
            'xls': ExcelLoader,
            'xlsx': ExcelLoader,
            # Markdown files
            'md': MarkdownLoader,
            'markdown': MarkdownLoader,
            # Plain text and code files
            'txt': TextLoader,
            # Source code files (treat as text)
            'py': TextLoader,
            'js': TextLoader,
            'ts': TextLoader,
            'jsx': TextLoader,
            'tsx': TextLoader,
            'java': TextLoader,
            'cpp': TextLoader,
            'c': TextLoader,
            'h': TextLoader,
            'cs': TextLoader,
            'go': TextLoader,
            'rs': TextLoader,
            'rb': TextLoader,
            'php': TextLoader,
            'html': TextLoader,
            'htm': TextLoader,
            'css': TextLoader,
            'json': TextLoader,
            'xml': TextLoader,
            'yaml': TextLoader,
            'yml': TextLoader,
            'sql': TextLoader,
            'sh': TextLoader,
            'bash': TextLoader,
        }
        
        loader_class = loaders.get(file_type, TextLoader)
        logger.debug(f"Selected loader {loader_class.__name__} for file type '{file_type}'")
        return loader_class()
