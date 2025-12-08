"""
vizu_parsers - File parsing and text chunking for RAG

This library provides:
- Parsers for PDF, CSV, and TXT files
- Text chunking with configurable strategies
- Utilities for RAG document preparation
"""

from vizu_parsers.parsers.base_parser import BaseParser
from vizu_parsers.parsers.pdf_parser import PDFParser
from vizu_parsers.parsers.csv_parser import CSVParser
from vizu_parsers.parsers.txt_parser import TXTParser
from vizu_parsers.parsers.router import get_parser_for_file, ParserRouter

from vizu_parsers.chunker.text_chunker import TextChunker, ChunkingStrategy
from vizu_parsers.chunker.models import Chunk

from vizu_parsers.pipeline import parse_and_chunk, chunk_text

__all__ = [
    # Parsers
    "BaseParser",
    "PDFParser",
    "CSVParser",
    "TXTParser",
    "get_parser_for_file",
    "ParserRouter",
    # Chunker
    "TextChunker",
    "ChunkingStrategy",
    "Chunk",
    # Pipeline
    "parse_and_chunk",
    "chunk_text",
]
