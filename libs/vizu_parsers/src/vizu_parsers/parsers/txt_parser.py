"""Plain text parser implementation."""

import io
import logging
from typing import BinaryIO

from vizu_parsers.parsers.base_parser import BaseParser

logger = logging.getLogger(__name__)


class TXTParser(BaseParser):
    """
    Parser for plain text files (.txt, .md, .json, etc.)
    """

    def __init__(self, encoding: str = "utf-8"):
        """
        Initialize the text parser.

        Args:
            encoding: Text encoding to use. Defaults to UTF-8.
        """
        self.encoding = encoding

    def parse(self, file_stream: io.BytesIO | BinaryIO) -> str:
        """
        Read a text file stream and return its content.

        Args:
            file_stream: The text file in memory (io.BytesIO) or file object.

        Returns:
            The text content of the file.
            Returns empty string if the file cannot be read.
        """
        logger.debug("Starting TXT parsing...")

        try:
            # Ensure stream pointer is at the beginning
            file_stream.seek(0)

            # Read and decode the content
            content = file_stream.read()

            if isinstance(content, bytes):
                # Try specified encoding, fall back to latin-1 if fails
                try:
                    text = content.decode(self.encoding)
                except UnicodeDecodeError:
                    logger.warning(f"Failed to decode with {self.encoding}, trying latin-1")
                    text = content.decode("latin-1")
            else:
                text = content

            if not text.strip():
                logger.warning("TXT file processed but is empty.")
                return ""

            logger.debug(f"TXT parsing complete. {len(text)} characters extracted.")
            return text

        except Exception as e:
            logger.error(f"Unexpected error during TXT parsing: {e}", exc_info=True)
            return ""
