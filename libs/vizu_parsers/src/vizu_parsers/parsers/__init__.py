"""Parsers for extracting text from various file formats."""

from vizu_parsers.parsers.base_parser import BaseParser
from vizu_parsers.parsers.pdf_parser import PDFParser
from vizu_parsers.parsers.csv_parser import CSVParser
from vizu_parsers.parsers.txt_parser import TXTParser
from vizu_parsers.parsers.router import get_parser_for_file, ParserRouter

__all__ = [
    "BaseParser",
    "PDFParser",
    "CSVParser",
    "TXTParser",
    "get_parser_for_file",
    "ParserRouter",
]
