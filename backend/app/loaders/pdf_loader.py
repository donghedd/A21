"""
PDF File Loader
"""
from typing import List
from .base import BaseLoader, Document


class PDFLoader(BaseLoader):
    """Load PDF files using PyMuPDF"""
    
    def load(self, file_path: str) -> List[Document]:
        """Load PDF file and extract text from each page"""
        try:
            import fitz  # PyMuPDF
            
            documents = []
            doc = fitz.open(file_path)
            
            for page_num in range(len(doc)):
                page = doc[page_num]
                text = page.get_text()
                
                if text.strip():
                    documents.append(Document(
                        page_content=text,
                        metadata={
                            'source': file_path,
                            'page': page_num + 1,
                            'total_pages': len(doc)
                        }
                    ))
            
            doc.close()
            return documents
            
        except Exception as e:
            raise Exception(f"Failed to load PDF file: {str(e)}")
