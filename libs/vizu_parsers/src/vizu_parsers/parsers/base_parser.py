"""Base parser interface for all file parsers."""

import io
from abc import ABC, abstractmethod
from typing import BinaryIO


class BaseParser(ABC):
    """
    Interface (Abstract Base Class) for all file parsers.

    Defines the contract that every parser (PDF, CSV, etc.) must follow.
    The 'parse' method receives a file-like object and returns the extracted text.
    """

    @abstractmethod
    def parse(self, file_stream: io.BytesIO | BinaryIO) -> str:
        """
        Extract textual content from a file stream.

        Args:
            file_stream: The file in memory (e.g., io.BytesIO) or file object.

        Returns:
            A single string containing all extracted text from the file.
        """
        pass

    def parse_file(self, file_path: str) -> str:
        """
        Convenience method to parse a file from disk.

        Args:
            file_path: Path to the file on disk.

        Returns:
            A single string containing all extracted text from the file.
        """
        with open(file_path, "rb") as f:
            return self.parse(f)
