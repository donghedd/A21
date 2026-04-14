"""File Loaders Package
"""
from .base import BaseLoader, Document
from .pdf_loader import PDFLoader
from .word_loader import WordLoader
from .excel_loader import ExcelLoader
from .markdown_loader import MarkdownLoader
from .text_loader import TextLoader
from .json_loader import JsonLoader

__all__ = [
    'BaseLoader', 'Document',
    'PDFLoader', 'WordLoader', 'ExcelLoader',
    'MarkdownLoader', 'TextLoader', 'JsonLoader'
]
