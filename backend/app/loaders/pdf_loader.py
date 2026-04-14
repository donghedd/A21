"""
PDF File Loader
"""
import logging
from typing import List
from flask import current_app, has_app_context
from .base import BaseLoader, Document
from .ocr_utils import ocr_pdf_page

logger = logging.getLogger(__name__)


class PDFLoader(BaseLoader):
    """Load PDF files using PyMuPDF"""
    
    def load(self, file_path: str) -> List[Document]:
        """Load PDF file and extract text from each page"""
        try:
            import fitz  # PyMuPDF
            
            documents = []
            doc = fitz.open(file_path)
            ocr_enabled = False
            ocr_dpi = 200
            min_text_chars = 20

            if has_app_context():
                ocr_enabled = current_app.config.get('ENABLE_PDF_OCR', True)
                ocr_dpi = current_app.config.get('PDF_OCR_DPI', 200)
                min_text_chars = current_app.config.get('PDF_OCR_MIN_TEXT_CHARS', 20)
                ocr_lang = current_app.config.get('PDF_OCR_LANGUAGE', 'chi_sim+eng')
                tesseract_cmd = current_app.config.get('TESSERACT_CMD')
            else:
                ocr_lang = 'chi_sim+eng'
                tesseract_cmd = None
            
            for page_num in range(len(doc)):
                page = doc[page_num]
                text = self.normalize_content(page.get_text() or '')
                used_ocr = False

                # Scanned PDFs often have no text layer at all. OCR only when
                # native extraction is empty or clearly too sparse.
                if ocr_enabled and len(text) < min_text_chars:
                    try:
                        ocr_text = self.normalize_content(
                            ocr_pdf_page(
                                page,
                                dpi=ocr_dpi,
                                lang=ocr_lang,
                                tesseract_cmd=tesseract_cmd
                            )
                        )
                        if len(ocr_text) > len(text):
                            text = ocr_text
                            used_ocr = True
                    except Exception as e:
                        logger.warning(
                            "OCR fallback failed for %s page %s: %s",
                            file_path,
                            page_num + 1,
                            e
                        )

                if text.strip():
                    documents.append(Document(
                        page_content=text,
                        metadata={
                            'source': file_path,
                            'page': page_num + 1,
                            'total_pages': len(doc),
                            'ocr_used': used_ocr
                        }
                    ))
            
            doc.close()
            return documents
            
        except Exception as e:
            raise Exception(f"Failed to load PDF file: {str(e)}")
