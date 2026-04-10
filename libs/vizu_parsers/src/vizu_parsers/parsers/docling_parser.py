"""Parser using docling for complex document extraction (OCR, tables, images)."""

import io
import logging
import os
import tempfile
from dataclasses import dataclass, field
from typing import Any, BinaryIO

from vizu_parsers.parsers.base_parser import BaseParser

logger = logging.getLogger(__name__)


@dataclass
class DoclingExtractionOptions:
    """Configurable options for Docling document extraction.

    These options can be set by an agent at runtime to tune extraction
    quality for specific document types (e.g., Portuguese financial tables).
    """

    ocr_enabled: bool = True
    ocr_languages: list[str] = field(default_factory=lambda: ["en"])
    table_mode: str = "fast"  # "fast" or "accurate"
    do_table_structure: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "ocr_enabled": self.ocr_enabled,
            "ocr_languages": self.ocr_languages,
            "table_mode": self.table_mode,
            "do_table_structure": self.do_table_structure,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "DoclingExtractionOptions":
        return cls(
            ocr_enabled=data.get("ocr_enabled", True),
            ocr_languages=data.get("ocr_languages", ["en"]),
            table_mode=data.get("table_mode", "fast"),
            do_table_structure=data.get("do_table_structure", True),
        )


class DoclingParser(BaseParser):
    """Handles complex documents: scanned PDFs, DOCX with images, PPTX, XLSX.

    Requires the 'docling' extra: pip install vizu-parsers[docling]

    Uses docling's DocumentConverter for:
    - OCR on scanned PDFs
    - Table extraction
    - Layout analysis
    - Image-based document parsing
    - PPTX/XLSX structured extraction

    Supports configurable extraction options via DoclingExtractionOptions.
    """

    def __init__(self, options: DoclingExtractionOptions | None = None) -> None:
        """Initialize DoclingParser, verifying docling is installed.

        Args:
            options: Extraction options. If None, uses defaults (no OCR languages,
                     fast table mode). Pass configured options for better quality on
                     specific document types.
        """
        try:
            from docling.document_converter import DocumentConverter

            self._converter_cls = DocumentConverter
        except ImportError:
            raise ImportError(
                "docling is required for complex document parsing. "
                "Install with: pip install vizu-parsers[docling]"
            )
        self._options = options or DoclingExtractionOptions()

    def _build_converter(self):
        """Build a DocumentConverter with the configured pipeline options."""
        try:
            from docling.datamodel.base_models import InputFormat
            from docling.datamodel.pipeline_options import (
                EasyOcrOptions,
                PdfPipelineOptions,
            )
            from docling.document_converter import PdfFormatOption

            pipeline_options = PdfPipelineOptions()
            pipeline_options.do_ocr = self._options.ocr_enabled
            pipeline_options.do_table_structure = self._options.do_table_structure

            if self._options.ocr_languages and self._options.ocr_enabled:
                pipeline_options.ocr_options = EasyOcrOptions(
                    lang=self._options.ocr_languages,
                )

            if hasattr(pipeline_options, "table_structure_options"):
                pipeline_options.table_structure_options.mode = self._options.table_mode

            return self._converter_cls(
                format_options={
                    InputFormat.PDF: PdfFormatOption(
                        pipeline_options=pipeline_options
                    ),
                }
            )
        except Exception as e:
            logger.warning(f"Could not build configured converter: {e}. Using defaults.")
            return self._converter_cls()

    def _convert_file(self, file_path: str):
        """Run docling conversion on a file path. Returns the raw result."""
        converter = self._build_converter()
        return converter.convert(file_path)

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
        logger.debug(
            "Starting docling parsing (ocr=%s, langs=%s, table_mode=%s)...",
            self._options.ocr_enabled,
            self._options.ocr_languages,
            self._options.table_mode,
        )

        file_stream.seek(0)
        tmp_path: str | None = None

        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".bin") as tmp:
                tmp.write(file_stream.read())
                tmp_path = tmp.name

            result = self._convert_file(tmp_path)
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

    def parse_structured(self, file_stream: io.BytesIO | BinaryIO) -> dict[str, Any]:
        """Extract structured data from a document: markdown + tables + metadata.

        This method goes beyond plain text extraction — it returns tables as
        JSON-serializable data along with the full markdown and extraction stats.

        Args:
            file_stream: The file in memory (io.BytesIO) or file object.

        Returns:
            Dict with keys:
                - markdown: Full document as markdown string
                - tables: List of table dicts with columns, data, and metadata
                - stats: Extraction statistics
            Returns empty result dict if parsing fails.
        """
        logger.debug("Starting structured docling extraction...")

        file_stream.seek(0)
        tmp_path: str | None = None

        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".bin") as tmp:
                tmp.write(file_stream.read())
                tmp_path = tmp.name

            result = self._convert_file(tmp_path)
            doc = result.document
            markdown = doc.export_to_markdown()

            # Extract tables as structured data
            tables = []
            for i, table in enumerate(doc.tables):
                try:
                    df = table.export_to_dataframe(doc=doc)
                    tables.append({
                        "index": i,
                        "columns": list(df.columns),
                        "data": df.to_dict(orient="records"),
                        "num_rows": len(df),
                        "num_cols": len(df.columns),
                        "markdown": table.export_to_markdown(doc=doc),
                    })
                except Exception as e:
                    logger.warning(f"Could not export table {i}: {e}")

            return {
                "markdown": markdown or "",
                "tables": tables,
                "stats": {
                    "total_chars": len(markdown) if markdown else 0,
                    "num_tables": len(tables),
                    "options": self._options.to_dict(),
                },
            }

        except Exception as e:
            logger.error(f"Error during structured docling extraction: {e}", exc_info=True)
            return {"markdown": "", "tables": [], "stats": {"error": str(e)}}
        finally:
            if tmp_path and os.path.exists(tmp_path):
                os.unlink(tmp_path)
