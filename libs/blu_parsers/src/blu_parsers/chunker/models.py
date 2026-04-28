"""Data models for text chunking."""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Chunk:
    """
    Represents a chunk of text extracted from a document.

    Attributes:
        text: The actual text content of the chunk.
        index: The sequential index of this chunk in the document.
        start_char: Starting character position in the original document.
        end_char: Ending character position in the original document.
        metadata: Optional dictionary for additional metadata.
    """

    text: str
    index: int
    start_char: int
    end_char: int
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def length(self) -> int:
        """Return the length of the chunk text."""
        return len(self.text)

    def to_dict(self) -> dict[str, Any]:
        """Convert chunk to a dictionary."""
        return {
            "text": self.text,
            "index": self.index,
            "start_char": self.start_char,
            "end_char": self.end_char,
            "length": self.length,
            "metadata": self.metadata,
        }

    def __repr__(self) -> str:
        preview = self.text[:50] + "..." if len(self.text) > 50 else self.text
        return f"Chunk(index={self.index}, length={self.length}, text='{preview}')"
