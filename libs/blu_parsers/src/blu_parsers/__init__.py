"""
blu_parsers - File parsing and text chunking for RAG

This library provides:
- Parsers for PDF, CSV, TXT, and complex documents (via docling)
- Smart PDF parsing with OCR fallback
- Text chunking with configurable strategies
- File classification helpers (simple vs complex)
- Utilities for RAG document preparation
"""

from blu_parsers.chunker.models import Chunk
from blu_parsers.chunker.text_chunker import ChunkingStrategy, TextChunker
from blu_parsers.parsers.base_parser import BaseParser
from blu_parsers.parsers.csv_parser import CSVParser
from blu_parsers.parsers.docling_parser import DoclingExtractionOptions
from blu_parsers.parsers.pdf_parser import PDFParser
from blu_parsers.parsers.router import (
    COMPLEX_EXTENSIONS,
    SIMPLE_EXTENSIONS,
    ParserRouter,
    get_parser_for_file,
    is_complex_file,
)
from blu_parsers.parsers.smart_pdf_parser import SmartPDFParser
from blu_parsers.parsers.txt_parser import TXTParser
from blu_parsers.pipeline import chunk_text, parse_and_chunk

__all__ = [
    # Parsers
    "BaseParser",
    "PDFParser",
    "CSVParser",
    "TXTParser",
    "SmartPDFParser",
    "DoclingExtractionOptions",
    "get_parser_for_file",
    "is_complex_file",
    "ParserRouter",
    "COMPLEX_EXTENSIONS",
    "SIMPLE_EXTENSIONS",
    # Chunker
    "TextChunker",
    "ChunkingStrategy",
    "Chunk",
    # Pipeline
    "parse_and_chunk",
    "chunk_text",
]
