"""Text chunking implementation for RAG."""

import logging
import re
from enum import Enum

from vizu_parsers.chunker.models import Chunk

logger = logging.getLogger(__name__)


class ChunkingStrategy(Enum):
    """Available chunking strategies."""

    BY_SENTENCE = "by_sentence"  # Split on sentence boundaries
    BY_PARAGRAPH = "by_paragraph"  # Split on paragraph boundaries
    BY_CHAR = "by_char"  # Split by character count
    SEMANTIC = "semantic"  # Keep related content together (default)


class TextChunker:
    """
    Text chunker for preparing documents for RAG.

    Splits text into overlapping chunks while respecting semantic boundaries
    (sentences, paragraphs) when possible.
    """

    # Sentence ending patterns
    SENTENCE_ENDINGS = re.compile(r"[.!?]+[\s\n]+")

    # Paragraph separator pattern (2+ newlines or newline + indentation)
    PARAGRAPH_SEP = re.compile(r"\n\s*\n+")

    def __init__(
        self,
        chunk_size: int = 512,
        chunk_overlap: int = 50,
        strategy: ChunkingStrategy = ChunkingStrategy.SEMANTIC,
        min_chunk_size: int = 100,
    ):
        """
        Initialize the text chunker.

        Args:
            chunk_size: Target size for each chunk in characters.
            chunk_overlap: Number of characters to overlap between chunks.
            strategy: The chunking strategy to use.
            min_chunk_size: Minimum chunk size (smaller chunks are merged).
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.strategy = strategy
        self.min_chunk_size = min_chunk_size

        if chunk_overlap >= chunk_size:
            raise ValueError("chunk_overlap must be less than chunk_size")

    def chunk(self, text: str, metadata: dict | None = None) -> list[Chunk]:
        """
        Split text into chunks.

        Args:
            text: The text to chunk.
            metadata: Optional metadata to include in each chunk.

        Returns:
            List of Chunk objects.
        """
        if not text or not text.strip():
            return []

        # Normalize whitespace
        text = self._normalize_text(text)

        if self.strategy == ChunkingStrategy.BY_SENTENCE:
            return self._chunk_by_sentence(text, metadata)
        elif self.strategy == ChunkingStrategy.BY_PARAGRAPH:
            return self._chunk_by_paragraph(text, metadata)
        elif self.strategy == ChunkingStrategy.BY_CHAR:
            return self._chunk_by_char(text, metadata)
        else:  # SEMANTIC (default)
            return self._chunk_semantic(text, metadata)

    def _normalize_text(self, text: str) -> str:
        """Normalize whitespace in text."""
        # Replace multiple spaces with single space
        text = re.sub(r"[ \t]+", " ", text)
        # Normalize line endings
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        return text.strip()

    def _chunk_by_char(self, text: str, metadata: dict | None = None) -> list[Chunk]:
        """Simple character-based chunking."""
        chunks = []
        start = 0
        index = 0

        while start < len(text):
            end = min(start + self.chunk_size, len(text))

            chunk_text = text[start:end]
            chunk = Chunk(
                text=chunk_text,
                index=index,
                start_char=start,
                end_char=end,
                metadata=metadata.copy() if metadata else {},
            )
            chunks.append(chunk)

            # Move start forward, accounting for overlap
            start = end - self.chunk_overlap if end < len(text) else end
            index += 1

        return chunks

    def _chunk_by_sentence(self, text: str, metadata: dict | None = None) -> list[Chunk]:
        """Chunk text respecting sentence boundaries."""
        # Split into sentences
        sentences = self.SENTENCE_ENDINGS.split(text)
        sentences = [s.strip() for s in sentences if s.strip()]

        return self._combine_segments(sentences, text, metadata)

    def _chunk_by_paragraph(self, text: str, metadata: dict | None = None) -> list[Chunk]:
        """Chunk text respecting paragraph boundaries."""
        # Split into paragraphs
        paragraphs = self.PARAGRAPH_SEP.split(text)
        paragraphs = [p.strip() for p in paragraphs if p.strip()]

        return self._combine_segments(paragraphs, text, metadata)

    def _chunk_semantic(self, text: str, metadata: dict | None = None) -> list[Chunk]:
        """
        Semantic chunking - tries to keep related content together.

        Strategy:
        1. First split by paragraphs
        2. If paragraphs are too large, split by sentences
        3. Combine small paragraphs to reach target chunk size
        """
        # First split by paragraphs
        paragraphs = self.PARAGRAPH_SEP.split(text)
        paragraphs = [p.strip() for p in paragraphs if p.strip()]

        # Process each paragraph
        segments = []
        for para in paragraphs:
            if len(para) <= self.chunk_size:
                segments.append(para)
            else:
                # Paragraph too large, split by sentences
                sentences = self.SENTENCE_ENDINGS.split(para)
                sentences = [s.strip() for s in sentences if s.strip()]
                segments.extend(sentences)

        return self._combine_segments(segments, text, metadata)

    def _combine_segments(
        self, segments: list[str], original_text: str, metadata: dict | None = None
    ) -> list[Chunk]:
        """
        Combine segments into chunks of target size.

        Args:
            segments: List of text segments (sentences, paragraphs, etc.)
            original_text: The original text (for calculating positions)
            metadata: Optional metadata to include in each chunk
        """
        if not segments:
            return []

        chunks = []
        current_text = ""
        current_start = 0
        index = 0

        for segment in segments:
            # Check if adding this segment exceeds chunk size
            potential_text = current_text + (" " if current_text else "") + segment

            if len(potential_text) <= self.chunk_size:
                # Can fit in current chunk
                current_text = potential_text
            else:
                # Need to start new chunk
                if current_text:
                    # Save current chunk
                    end_pos = self._find_position(original_text, current_text, current_start)
                    chunk = Chunk(
                        text=current_text,
                        index=index,
                        start_char=current_start,
                        end_char=end_pos,
                        metadata=metadata.copy() if metadata else {},
                    )
                    chunks.append(chunk)
                    index += 1

                    # Calculate overlap start position
                    if self.chunk_overlap > 0 and len(current_text) > self.chunk_overlap:
                        overlap_text = current_text[-self.chunk_overlap :]
                        current_start = end_pos - len(overlap_text)
                        current_text = overlap_text + " " + segment
                    else:
                        current_start = end_pos
                        current_text = segment
                else:
                    current_text = segment

        # Don't forget the last chunk
        if current_text:
            end_pos = min(current_start + len(current_text), len(original_text))
            chunk = Chunk(
                text=current_text,
                index=index,
                start_char=current_start,
                end_char=end_pos,
                metadata=metadata.copy() if metadata else {},
            )
            chunks.append(chunk)

        # Merge any chunks that are too small
        chunks = self._merge_small_chunks(chunks)

        logger.debug(f"Created {len(chunks)} chunks from {len(segments)} segments")
        return chunks

    def _find_position(self, original: str, substring: str, start_from: int = 0) -> int:
        """Find the end position of a substring in the original text."""
        # Simple approximation - just use character count
        return min(start_from + len(substring), len(original))

    def _merge_small_chunks(self, chunks: list[Chunk]) -> list[Chunk]:
        """Merge chunks that are smaller than min_chunk_size."""
        if not chunks or len(chunks) <= 1:
            return chunks

        merged = []
        current = chunks[0]

        for next_chunk in chunks[1:]:
            if current.length < self.min_chunk_size:
                # Merge with next chunk
                merged_text = current.text + " " + next_chunk.text
                current = Chunk(
                    text=merged_text,
                    index=current.index,
                    start_char=current.start_char,
                    end_char=next_chunk.end_char,
                    metadata={**current.metadata, **next_chunk.metadata},
                )
            else:
                merged.append(current)
                current = Chunk(
                    text=next_chunk.text,
                    index=len(merged),
                    start_char=next_chunk.start_char,
                    end_char=next_chunk.end_char,
                    metadata=next_chunk.metadata,
                )

        # Don't forget the last chunk
        if current:
            merged.append(current)

        return merged
