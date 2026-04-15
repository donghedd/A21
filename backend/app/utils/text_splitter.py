"""
Text Splitter for RAG - Enhanced with smart chunking strategies
"""
import re
from typing import List, Dict, Any, Optional
from ..loaders.base import Document


HEADING_PATTERNS = [
    (re.compile(r'^第[一二三四五六七八九十百零0-9]+篇\s+.+$'), 1),
    (re.compile(r'^第[一二三四五六七八九十百零0-9]+章\s+.+$'), 1),
    (re.compile(r'^第[一二三四五六七八九十百零0-9]+节\s+.+$'), 2),
    (re.compile(r'^\d+(?:\.\d+){1,3}\s+.+$'), None),
    (re.compile(r'^[（(]?\d+[)）]\s*[^\s].{0,36}$'), 4),
    (re.compile(r'^[一二三四五六七八九十]+[、.]\s*[^\s].{0,36}$'), 3),
]


def detect_heading_level(line: str) -> Optional[int]:
    """Detect title-like lines in OCR/txt content and map to markdown levels."""
    if not line:
        return None

    text = line.strip()
    if not text or text.startswith('#'):
        return None

    if len(text) > 60:
        return None

    if re.match(r'^(图|表)\s*\d', text):
        return None

    if text.endswith(('。', '；', ';', '：', ':', '？', '?', '！', '!')):
        return None

    for pattern, fixed_level in HEADING_PATTERNS:
        if not pattern.match(text):
            continue
        if fixed_level is not None:
            return fixed_level
        dot_count = text.split()[0].count('.')
        return min(4, dot_count + 1)

    return None


def normalize_structured_headings(text: str) -> str:
    """Convert plain-text numbered headings into markdown headings for better chunking."""
    if not text:
        return text

    normalized_lines = []
    for raw_line in text.split('\n'):
        line = raw_line.rstrip()
        level = detect_heading_level(line)
        if level is not None:
          normalized_lines.append(f"{'#' * level} {line.strip()}")
        else:
          normalized_lines.append(line)

    return '\n'.join(normalized_lines)


class MarkdownHeaderSplitter:
    """Split text by Markdown headers with enhanced breadcrumb tracking"""
    
    def __init__(self, headers_to_split_on: List[tuple] = None, strip_headers: bool = False):
        if headers_to_split_on is None:
            headers_to_split_on = [
                ('#', 'Header 1'),
                ('##', 'Header 2'),
                ('###', 'Header 3'),
                ('####', 'Header 4'),
                ('#####', 'Header 5'),
                ('######', 'Header 6'),
            ]
        self.headers_to_split_on = headers_to_split_on
        self.strip_headers = strip_headers
    
    def split_text(self, text: str, base_metadata: dict = None) -> List[Document]:
        """Split text by markdown headers with breadcrumb tracking"""
        if base_metadata is None:
            base_metadata = {}
            
        # Build regex pattern for headers
        header_patterns = '|'.join([
            f'^{re.escape(header[0])}\\s+(.+)$' 
            for header in self.headers_to_split_on
        ])
        
        lines = text.split('\n')
        chunks = []
        current_chunk = []
        current_headers = {}
        
        for line in lines:
            is_header = False
            for header_marker, header_name in self.headers_to_split_on:
                pattern = f'^{re.escape(header_marker)}\\s+(.+)$'
                match = re.match(pattern, line)
                if match:
                    is_header = True
                    # Save previous chunk
                    if current_chunk:
                        content = '\n'.join(current_chunk).strip()
                        if content:
                            # Build section path from headers
                            section_path = self._build_section_path(current_headers)
                            metadata = {
                                **base_metadata,
                                **current_headers,
                                'section_path': section_path
                            }
                            chunks.append(Document(
                                page_content=content,
                                metadata=metadata
                            ))
                        current_chunk = []
                    
                    # Update headers
                    header_level = len(header_marker)
                    current_headers[header_name] = match.group(1)
                    
                    # Clear lower level headers
                    for h_marker, h_name in self.headers_to_split_on:
                        if len(h_marker) > header_level:
                            current_headers.pop(h_name, None)
                    
                    if not self.strip_headers:
                        current_chunk.append(line)
                    break
            
            if not is_header:
                current_chunk.append(line)
        
        # Save last chunk
        if current_chunk:
            content = '\n'.join(current_chunk).strip()
            if content:
                section_path = self._build_section_path(current_headers)
                metadata = {
                    **base_metadata,
                    **current_headers,
                    'section_path': section_path
                }
                chunks.append(Document(
                    page_content=content,
                    metadata=metadata
                ))
        
        return chunks if chunks else [Document(
            page_content=text,
            metadata={**base_metadata, 'section_path': []}
        )]
    
    def _build_section_path(self, headers: Dict[str, str]) -> List[str]:
        """Build hierarchical section path from headers"""
        path = []
        for header_marker, header_name in self.headers_to_split_on:
            if header_name in headers:
                path.append(headers[header_name])
        return path


class RecursiveCharacterSplitter:
    """Recursively split text by characters with overlap.
    Reference: Open WebUI's RecursiveCharacterTextSplitter from langchain.
    Enhanced with smart boundary detection to avoid cutting between headers and content.
    """
    
    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200, 
                 separators: List[str] = None):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        # Order matters: try to split at larger boundaries first
        self.separators = separators or ['\n\n', '\n', '. ', ',', ' ', '']
    
    def split_text(self, text: str) -> List[str]:
        """Split text into chunks"""
        return self._split_text(text, self.separators)
    
    def _split_text(self, text: str, separators: List[str]) -> List[str]:
        """Recursive split implementation"""
        final_chunks = []
        separator = separators[-1]
        new_separators = []
        
        for i, sep in enumerate(separators):
            if sep == '':
                separator = sep
                break
            if sep in text:
                separator = sep
                new_separators = separators[i + 1:]
                break
        
        splits = text.split(separator) if separator else list(text)
        
        good_splits = []
        for split in splits:
            if len(split) < self.chunk_size:
                good_splits.append(split)
            else:
                if good_splits:
                    merged = self._merge_splits(good_splits, separator)
                    final_chunks.extend(merged)
                    good_splits = []
                
                if new_separators:
                    other_chunks = self._split_text(split, new_separators)
                    final_chunks.extend(other_chunks)
                else:
                    final_chunks.append(split)
        
        if good_splits:
            merged = self._merge_splits(good_splits, separator)
            final_chunks.extend(merged)
        
        return final_chunks
    
    def _merge_splits(self, splits: List[str], separator: str) -> List[str]:
        """Merge splits with overlap"""
        merged = []
        current = []
        current_len = 0
        
        for split in splits:
            split_len = len(split)
            
            if current_len + split_len + (len(separator) if current else 0) > self.chunk_size:
                if current:
                    merged.append(separator.join(current))
                    # Keep overlap
                    while current_len > self.chunk_overlap:
                        current_len -= len(current[0]) + len(separator)
                        current.pop(0)
            
            current.append(split)
            current_len += split_len + (len(separator) if len(current) > 1 else 0)
        
        if current:
            merged.append(separator.join(current))
        
        return merged
    
    def _is_likely_header_line(self, text: str) -> bool:
        """Check if a line is likely a markdown header.
        This helps avoid cutting right after a header.
        """
        lines = text.strip().split('\n')
        if not lines:
            return False
        # Check if the last line is a header
        last_line = lines[-1].strip()
        return last_line.startswith('#') and not last_line.startswith('##')
    
    def split_documents(self, documents: List[Document]) -> List[Document]:
        """Split documents into smaller chunks while preserving metadata"""
        result = []
        for doc in documents:
            chunks = self.split_text(doc.page_content)
            for i, chunk in enumerate(chunks):
                # Preserve section_path and other metadata
                result.append(Document(
                    page_content=chunk,
                    metadata={
                        **doc.metadata,
                        'chunk_index': i,
                        'total_chunks': len(chunks)
                    }
                ))
        return result


def merge_small_chunks(chunks: List[Document], min_size: int = 200,
                       max_size: int = 1000) -> List[Document]:
    """
    Merge small chunks into larger ones to avoid overly fragmented results.
    Reference: Open WebUI's merge_docs_to_target_size.
    
    Strategy (from Open WebUI):
    - If a chunk is smaller than min_size, merge it with the next chunk
      that shares the same file and section metadata
    - Merged result must not exceed max_size
    - Preserves metadata from the first chunk in each merge
    - Key improvement: Ensure headers stay with their content
    
    Args:
        chunks: List of Document chunks to merge
        min_size: Minimum chunk size target (Open WebUI: CHUNK_MIN_SIZE_TARGET)
        max_size: Maximum allowed merged chunk size (Open WebUI: CHUNK_SIZE)
    
    Returns:
        List of merged Document chunks
    """
    if not chunks:
        return chunks
    
    merged = []
    i = 0
    
    while i < len(chunks):
        current = chunks[i]
        current_len = len(current.page_content)
        
        # If chunk is large enough or it's the last one, keep as-is
        if current_len >= min_size or i == len(chunks) - 1:
            merged.append(current)
            i += 1
            continue
        
        # Try to merge with next chunk(s) if they share the same context
        merged_content = current.page_content
        merged_metadata = dict(current.metadata)
        j = i + 1
        
        while j < len(chunks) and len(merged_content) < min_size:
            next_chunk = chunks[j]
            # Check if same file and section
            same_file = (current.metadata.get('file_name') == 
                        next_chunk.metadata.get('file_name'))
            same_section = (current.metadata.get('section_path') == 
                           next_chunk.metadata.get('section_path'))
            
            if same_file and same_section:
                # Check combined size won't exceed max
                combined_len = len(merged_content) + len(next_chunk.page_content) + 2
                if combined_len <= max_size:
                    merged_content += '\n\n' + next_chunk.page_content
                    j += 1
                else:
                    # Even if we haven't reached min_size, can't merge more
                    break
            else:
                # Different section, stop merging
                break
        
        merged.append(Document(
            page_content=merged_content,
            metadata=merged_metadata
        ))
        i = j
    
    return merged


def split_documents(documents: List[Document], 
                   chunk_size: int = 1000, 
                   chunk_overlap: int = 200,
                   use_markdown_splitter: bool = True,
                   min_chunk_size: int = 200) -> List[Document]:
    """
    Split documents using Open-WebUI's strategy.
    
    Open-WebUI Pipeline:
    1. Markdown Header Splitter (optional) - Split by headers, keep headers in content
    2. Merge small chunks IMMEDIATELY after markdown split (KEY STEP!)
       - This ensures headers stay with their content before character splitting
    3. Recursive Character Splitter - Fine-grained splitting with overlap
    
    Reference: open-webui/backend/open_webui/routers/retrieval.py L1371-1409
    
    Args:
        documents: List of documents to split
        chunk_size: Maximum chunk size in characters
        chunk_overlap: Overlap between chunks in characters
        use_markdown_splitter: Whether to use markdown header splitting
        min_chunk_size: Minimum chunk size target for merging (CHUNK_MIN_SIZE_TARGET)
    
    Returns:
        List of split Document chunks
    """
    result = documents
    
    # First: Split by Markdown headers (if enabled)
    if use_markdown_splitter:
        md_splitter = MarkdownHeaderSplitter(strip_headers=False)
        new_docs = []
        for doc in result:
            normalized_text = normalize_structured_headings(doc.page_content)
            # Pass existing metadata as base_metadata
            split_docs = md_splitter.split_text(
                normalized_text,
                base_metadata=doc.metadata
            )
            for split_doc in split_docs:
                new_docs.append(Document(
                    page_content=split_doc.page_content,
                    metadata={**doc.metadata, **split_doc.metadata}
                ))
        result = new_docs
        
        # CRITICAL: Merge small chunks IMMEDIATELY after markdown split
        # This is the KEY difference from Open-WebUI's strategy!
        # It ensures headers stay with their content before character-level splitting
        if min_chunk_size > 0:
            before_count = len(result)
            result = merge_small_chunks(result, min_size=min_chunk_size, max_size=chunk_size)
            merged_count = before_count - len(result)
            if merged_count > 0:
                import logging
                logging.getLogger(__name__).info(
                    f"Merged {merged_count} small chunks after markdown split ({before_count} -> {len(result)})"
                )
    
    # Second: Split by characters with overlap (fine-grained splitting)
    char_splitter = RecursiveCharacterSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap
    )
    result = char_splitter.split_documents(result)
    
    return result
