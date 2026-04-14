"""
OCR helpers for scanned PDF fallback.
"""
from __future__ import annotations

import io
import logging
from typing import Optional

logger = logging.getLogger(__name__)

def ocr_pdf_page(page, dpi: int = 200, lang: str = "chi_sim+eng",
                 tesseract_cmd: Optional[str] = None) -> str:
    """
    Render a PDF page to an image and run OCR on it.

    Returns extracted text or an empty string when OCR finds nothing.
    """
    import fitz
    from PIL import Image
    import pytesseract

    scale = max(dpi, 72) / 72.0
    matrix = fitz.Matrix(scale, scale)
    pix = page.get_pixmap(matrix=matrix, alpha=False)

    image = Image.open(io.BytesIO(pix.tobytes("png"))).convert("RGB")

    if tesseract_cmd:
        pytesseract.pytesseract.tesseract_cmd = tesseract_cmd

    try:
        text = pytesseract.image_to_string(image, lang=lang)
    except pytesseract.TesseractNotFoundError as e:
        raise RuntimeError(
            "Tesseract executable not found. Install Tesseract OCR and set "
            "TESSERACT_CMD if it is not on PATH."
        ) from e

    return text.strip()
