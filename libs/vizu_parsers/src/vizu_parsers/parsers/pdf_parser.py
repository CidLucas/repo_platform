"""PDF parser implementation using pypdf."""

import io
import logging
from typing import BinaryIO

from pypdf import PdfReader
from pypdf.errors import PdfReadError

from vizu_parsers.parsers.base_parser import BaseParser

logger = logging.getLogger(__name__)


class PDFParser(BaseParser):
    """
    Parser for extracting text from PDF files using pypdf.
    """

    def parse(self, file_stream: io.BytesIO | BinaryIO) -> str:
        """
        Read a PDF file stream and extract its textual content.

        Args:
            file_stream: The PDF file in memory (io.BytesIO) or file object.

        Returns:
            A single string containing concatenated text from all pages.
            Returns empty string if the PDF cannot be read or contains no text.
        """
        logger.debug("Starting PDF parsing...")

        try:
            # Ensure stream pointer is at the beginning
            file_stream.seek(0)

            # Open PDF directly from the in-memory stream
            reader = PdfReader(file_stream)

            extracted_pages = []
            for i, page in enumerate(reader.pages):
                try:
                    text = page.extract_text()
                    if text:
                        extracted_pages.append(text)
                except Exception as e:
                    # Log error for specific page but continue
                    logger.warning(
                        f"Error extracting text from page {i} of PDF: {e}"
                    )

            if not extracted_pages:
                logger.warning("PDF processed but no text was extracted.")
                return ""

            logger.debug(
                f"PDF parsing complete. {len(extracted_pages)} pages extracted."
            )
            # Join text from all pages with newlines
            return "\n".join(extracted_pages)

        except PdfReadError as e:
            logger.error(
                f"Failed to read PDF file. May be corrupted or encrypted. Error: {e}"
            )
            return ""
        except Exception as e:
            logger.error(
                f"Unexpected error during PDF parsing: {e}", exc_info=True
            )
            return ""
