"""Router for selecting the appropriate parser based on file type."""

import logging
from pathlib import Path

from vizu_parsers.parsers.base_parser import BaseParser
from vizu_parsers.parsers.csv_parser import CSVParser
from vizu_parsers.parsers.pdf_parser import PDFParser
from vizu_parsers.parsers.txt_parser import TXTParser

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# File classification constants for upload routing
# ---------------------------------------------------------------------------

# Extensions that need Python-side processing (docling)
# Note: .pdf CAN be simple too — default conservative: mark as complex.
# Frontend can offer a toggle "Use advanced processing" for ambiguous types.
COMPLEX_EXTENSIONS = {".pdf", ".docx", ".pptx", ".xlsx"}

# Extensions that Edge Functions (Deno) can handle natively
SIMPLE_EXTENSIONS = {
    ".txt",
    ".md",
    ".csv",
    ".json",
    ".xml",
    ".html",
    ".yaml",
    ".yml",
    ".htm",
}


def is_complex_file(filename: str) -> bool:
    """Returns True if the file likely needs Python/docling processing.

    Used by frontend/backend to decide upload path:
    - True  → TUS resumable upload → file_upload_api /v1/upload/process
    - False → standard upload → process-document Edge Function

    Note: .pdf and .docx can be either simple or complex.
    Default conservative: mark them as complex. Frontend can offer
    a toggle "Use advanced processing" for these ambiguous types.
    """
    ext = Path(filename).suffix.lower()
    return ext in COMPLEX_EXTENSIONS


def _get_docling_parser_class() -> type[BaseParser] | None:
    """Try to import DoclingParser; return None if docling is not installed."""
    try:
        from vizu_parsers.parsers.docling_parser import DoclingParser

        return DoclingParser
    except ImportError:
        logger.debug("docling not installed — DoclingParser unavailable")
        return None


def _get_smart_pdf_parser_class() -> type[BaseParser]:
    """Return SmartPDFParser (always available, graceful fallback inside)."""
    from vizu_parsers.parsers.smart_pdf_parser import SmartPDFParser

    return SmartPDFParser


class ParserRouter:
    """
    Routes files to the appropriate parser based on extension.
    """

    # Map of file extensions to parser classes
    PARSER_MAP: dict[str, type[BaseParser]] = {
        # PDF — SmartPDFParser tries pypdf first, falls back to docling
        ".pdf": _get_smart_pdf_parser_class(),
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
    def _ensure_docling_parsers(cls) -> None:
        """Lazily register docling-based parsers for complex formats."""
        docling_exts = {".docx", ".pptx", ".xlsx"}
        if any(ext in cls.PARSER_MAP for ext in docling_exts):
            return  # Already registered

        docling_cls = _get_docling_parser_class()
        if docling_cls:
            for ext in docling_exts:
                cls.PARSER_MAP[ext] = docling_cls
            logger.debug("Registered DoclingParser for .docx, .pptx, .xlsx")
        else:
            logger.debug("DoclingParser unavailable — .docx/.pptx/.xlsx not registered")

    @classmethod
    def get_parser(cls, filename: str) -> BaseParser | None:
        """
        Get the appropriate parser for a given filename.

        Args:
            filename: The name or path of the file.

        Returns:
            An instance of the appropriate parser, or None if unsupported.
        """
        # Ensure docling-based parsers are registered if available
        cls._ensure_docling_parsers()

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
