"""Smart PDF parser that tries fast extraction first, falls back to docling."""

import io
import logging
from typing import BinaryIO

from vizu_parsers.parsers.base_parser import BaseParser

logger = logging.getLogger(__name__)

# Heuristic thresholds
MIN_CHARS_PER_KB = 10  # Below this ratio → likely scanned/image PDF
MIN_FILE_SIZE_BYTES = 5000  # Don't trigger docling fallback for tiny files


class SmartPDFParser(BaseParser):
    """Try fast pypdf extraction first; fall back to docling for scanned/image PDFs.

    Heuristic: if the ratio of extracted characters to file size (chars/KB) is
    below a threshold, the PDF is likely scanned and needs OCR via docling.

    Falls back gracefully — if docling is not installed, returns whatever
    pypdf managed to extract.
    """

    def parse(self, file_stream: io.BytesIO | BinaryIO) -> str:
        """Extract text from PDF, using docling as fallback for scanned documents.

        Args:
            file_stream: The PDF file in memory (io.BytesIO) or file object.

        Returns:
            Extracted text content. May be markdown-formatted if docling was used.
        """
        from vizu_parsers.parsers.pdf_parser import PDFParser

        logger.debug("SmartPDFParser: trying fast pypdf extraction first...")

        # First try: fast text extraction with pypdf
        file_stream.seek(0)
        text = PDFParser().parse(file_stream)

        # Measure file size to compute density heuristic
        file_stream.seek(0, 2)  # Seek to end
        file_size = file_stream.tell()
        file_stream.seek(0)

        # If we got reasonable text, return it
        if text and file_size > 0:
            chars_per_kb = len(text) / max(file_size / 1024, 1)

            if chars_per_kb >= MIN_CHARS_PER_KB or file_size <= MIN_FILE_SIZE_BYTES:
                logger.debug(
                    f"SmartPDFParser: pypdf extraction sufficient "
                    f"(chars/KB={chars_per_kb:.1f}, {len(text)} chars)"
                )
                return text

            logger.info(
                f"SmartPDFParser: sparse text detected (chars/KB={chars_per_kb:.1f}), "
                f"attempting docling fallback for OCR..."
            )

        # Fallback: try docling for OCR/scanned PDF extraction
        try:
            from vizu_parsers.parsers.docling_parser import DoclingParser

            file_stream.seek(0)
            docling_text = DoclingParser().parse(file_stream)

            if docling_text:
                logger.info(
                    f"SmartPDFParser: docling extracted {len(docling_text)} chars "
                    f"(vs {len(text)} from pypdf)"
                )
                return docling_text

        except ImportError:
            logger.warning(
                "SmartPDFParser: docling not installed, returning pypdf result. "
                "Install with: pip install vizu-parsers[docling]"
            )
        except Exception as e:
            logger.warning(f"SmartPDFParser: docling fallback failed: {e}")

        # Return whatever pypdf got (may be empty for fully scanned docs)
        return text
