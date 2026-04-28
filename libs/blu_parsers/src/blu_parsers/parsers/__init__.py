"""Parsers for extracting text from various file formats."""

from blu_parsers.parsers.base_parser import BaseParser
from blu_parsers.parsers.csv_parser import CSVParser
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

__all__ = [
    "BaseParser",
    "PDFParser",
    "CSVParser",
    "TXTParser",
    "SmartPDFParser",
    "get_parser_for_file",
    "is_complex_file",
    "ParserRouter",
    "COMPLEX_EXTENSIONS",
    "SIMPLE_EXTENSIONS",
]
