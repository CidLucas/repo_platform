"""Router for selecting the appropriate parser based on file type."""

import logging
from pathlib import Path

from vizu_parsers.parsers.base_parser import BaseParser
from vizu_parsers.parsers.csv_parser import CSVParser
from vizu_parsers.parsers.pdf_parser import PDFParser
from vizu_parsers.parsers.txt_parser import TXTParser

logger = logging.getLogger(__name__)


class ParserRouter:
    """
    Routes files to the appropriate parser based on extension.
    """

    # Map of file extensions to parser classes
    PARSER_MAP = {
        # PDF
        ".pdf": PDFParser,
        # CSV/Excel-like
        ".csv": CSVParser,
        ".tsv": CSVParser,
        # Plain text
        ".txt": TXTParser,
        ".md": TXTParser,
        ".markdown": TXTParser,
        ".json": TXTParser,
        ".xml": TXTParser,
        ".html": TXTParser,
        ".htm": TXTParser,
        ".log": TXTParser,
        ".yaml": TXTParser,
        ".yml": TXTParser,
        ".toml": TXTParser,
        ".ini": TXTParser,
        ".cfg": TXTParser,
        ".conf": TXTParser,
        ".py": TXTParser,
        ".js": TXTParser,
        ".ts": TXTParser,
        ".java": TXTParser,
        ".c": TXTParser,
        ".cpp": TXTParser,
        ".h": TXTParser,
        ".hpp": TXTParser,
        ".rs": TXTParser,
        ".go": TXTParser,
        ".rb": TXTParser,
        ".php": TXTParser,
        ".sql": TXTParser,
        ".sh": TXTParser,
        ".bash": TXTParser,
        ".zsh": TXTParser,
    }

    @classmethod
    def get_parser(cls, filename: str) -> BaseParser | None:
        """
        Get the appropriate parser for a given filename.

        Args:
            filename: The name or path of the file.

        Returns:
            An instance of the appropriate parser, or None if unsupported.
        """
        ext = Path(filename).suffix.lower()

        parser_class = cls.PARSER_MAP.get(ext)
        if parser_class:
            logger.debug(f"Selected {parser_class.__name__} for extension '{ext}'")
            return parser_class()

        logger.warning(f"No parser found for extension '{ext}'")
        return None

    @classmethod
    def is_supported(cls, filename: str) -> bool:
        """
        Check if a file type is supported.

        Args:
            filename: The name or path of the file.

        Returns:
            True if the file type is supported, False otherwise.
        """
        ext = Path(filename).suffix.lower()
        return ext in cls.PARSER_MAP

    @classmethod
    def supported_extensions(cls) -> list[str]:
        """
        Get a list of all supported file extensions.

        Returns:
            List of supported extensions (with dots, e.g., ['.pdf', '.csv']).
        """
        return list(cls.PARSER_MAP.keys())


def get_parser_for_file(filename: str) -> BaseParser | None:
    """
    Convenience function to get a parser for a file.

    Args:
        filename: The name or path of the file.

    Returns:
        An instance of the appropriate parser, or None if unsupported.
    """
    return ParserRouter.get_parser(filename)
