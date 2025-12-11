"""Pipeline utilities for parsing and chunking files."""

import io
import logging
from typing import BinaryIO

from vizu_parsers.chunker.models import Chunk
from vizu_parsers.chunker.text_chunker import ChunkingStrategy, TextChunker
from vizu_parsers.parsers.router import get_parser_for_file

logger = logging.getLogger(__name__)


def parse_and_chunk(
    file_path: str | None = None,
    file_stream: io.BytesIO | BinaryIO | None = None,
    filename: str | None = None,
    chunk_size: int = 512,
    chunk_overlap: int = 50,
    strategy: ChunkingStrategy = ChunkingStrategy.SEMANTIC,
    min_chunk_size: int = 100,
    metadata: dict | None = None,
) -> list[Chunk]:
    """
    Parse a file and chunk its content in one step.

    Args:
        file_path: Path to the file on disk. Either this or file_stream is required.
        file_stream: File stream to parse. Either this or file_path is required.
        filename: Filename for determining parser (required if using file_stream).
        chunk_size: Target size for each chunk in characters.
        chunk_overlap: Number of characters to overlap between chunks.
        strategy: The chunking strategy to use.
        min_chunk_size: Minimum chunk size (smaller chunks are merged).
        metadata: Optional metadata to include in each chunk.

    Returns:
        List of Chunk objects.

    Raises:
        ValueError: If neither file_path nor file_stream is provided.
        ValueError: If file_stream is provided without filename.
    """
    # Validate inputs
    if not file_path and not file_stream:
        raise ValueError("Either file_path or file_stream must be provided")

    if file_stream and not filename:
        raise ValueError("filename is required when using file_stream")

    # Determine the filename for parser selection
    parse_filename = file_path if file_path else filename

    # Get the appropriate parser
    parser = get_parser_for_file(parse_filename)
    if not parser:
        logger.error(f"No parser available for file: {parse_filename}")
        return []

    # Parse the file
    if file_path:
        logger.info(f"Parsing file: {file_path}")
        text = parser.parse_file(file_path)
    else:
        logger.info(f"Parsing stream: {filename}")
        text = parser.parse(file_stream)

    if not text:
        logger.warning(f"No text extracted from file: {parse_filename}")
        return []

    logger.info(f"Extracted {len(text)} characters from {parse_filename}")

    # Create chunker and chunk the text
    chunker = TextChunker(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        strategy=strategy,
        min_chunk_size=min_chunk_size,
    )

    # Add source file to metadata
    chunk_metadata = metadata.copy() if metadata else {}
    chunk_metadata["source_file"] = str(parse_filename)

    chunks = chunker.chunk(text, metadata=chunk_metadata)
    logger.info(f"Created {len(chunks)} chunks from {parse_filename}")

    return chunks


def chunk_text(
    text: str,
    chunk_size: int = 512,
    chunk_overlap: int = 50,
    strategy: ChunkingStrategy = ChunkingStrategy.SEMANTIC,
    min_chunk_size: int = 100,
    metadata: dict | None = None,
) -> list[Chunk]:
    """
    Chunk raw text without parsing.

    Args:
        text: The text to chunk.
        chunk_size: Target size for each chunk in characters.
        chunk_overlap: Number of characters to overlap between chunks.
        strategy: The chunking strategy to use.
        min_chunk_size: Minimum chunk size (smaller chunks are merged).
        metadata: Optional metadata to include in each chunk.

    Returns:
        List of Chunk objects.
    """
    chunker = TextChunker(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        strategy=strategy,
        min_chunk_size=min_chunk_size,
    )

    return chunker.chunk(text, metadata=metadata)
