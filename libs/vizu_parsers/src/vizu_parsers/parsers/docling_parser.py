"""Parser using docling for complex document extraction (OCR, tables, images)."""

import io
import logging
import os
import tempfile
from typing import BinaryIO

from vizu_parsers.parsers.base_parser import BaseParser

logger = logging.getLogger(__name__)


class DoclingParser(BaseParser):
    """Handles complex documents: scanned PDFs, DOCX with images, PPTX, XLSX.

    Requires the 'docling' extra: pip install vizu-parsers[docling]

    Uses docling's DocumentConverter for:
    - OCR on scanned PDFs
    - Table extraction
    - Layout analysis
    - Image-based document parsing
    - PPTX/XLSX structured extraction
    """

    def __init__(self) -> None:
        """Initialize DoclingParser, verifying docling is installed."""
        try:
            from docling.document_converter import DocumentConverter

            self._converter_cls = DocumentConverter
        except ImportError:
            raise ImportError(
                "docling is required for complex document parsing. "
                "Install with: pip install vizu-parsers[docling]"
            )

    def parse(self, file_stream: io.BytesIO | BinaryIO) -> str:
        """Extract text from complex documents using docling.

        Docling requires a file path, so the stream is written to a
        temporary file for processing.

        Args:
            file_stream: The file in memory (io.BytesIO) or file object.

        Returns:
            Markdown-formatted text extracted from the document.
            Returns empty string if parsing fails.
        """
        logger.debug("Starting docling parsing...")

        file_stream.seek(0)
        tmp_path: str | None = None

        try:
            # Docling needs a file path — write stream to temp file
            with tempfile.NamedTemporaryFile(delete=False, suffix=".bin") as tmp:
                tmp.write(file_stream.read())
                tmp_path = tmp.name

            converter = self._converter_cls()
            result = converter.convert(tmp_path)
            text = result.document.export_to_markdown()

            if not text or not text.strip():
                logger.warning("Docling processed document but no text was extracted.")
                return ""

            logger.debug(f"Docling parsing complete. {len(text)} characters extracted.")
            return text

        except Exception as e:
            logger.error(f"Error during docling parsing: {e}", exc_info=True)
            return ""
        finally:
            if tmp_path and os.path.exists(tmp_path):
                os.unlink(tmp_path)
