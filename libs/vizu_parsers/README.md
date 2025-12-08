# vizu_parsers

Library for parsing files (PDF, CSV, TXT) and chunking text for RAG (Retrieval Augmented Generation).

## Features

- **Parsers**: Extract text from PDF, CSV, and plain text files
- **Chunker**: Split text into optimal chunks for embedding and RAG retrieval
- **File Router**: Automatically select the right parser based on file extension

## Installation

```bash
poetry add vizu-parsers --path ../libs/vizu_parsers
```

## Usage

### Parsing Files

```python
from vizu_parsers import PDFParser, CSVParser, TXTParser, get_parser_for_file

# Parse a PDF file
with open("document.pdf", "rb") as f:
    parser = PDFParser()
    text = parser.parse(f)

# Auto-detect parser from filename
parser = get_parser_for_file("data.csv")
with open("data.csv", "rb") as f:
    text = parser.parse(f)
```

### Chunking Text

```python
from vizu_parsers import TextChunker, ChunkingStrategy

# Default chunking (semantic, 512 tokens, 50 overlap)
chunker = TextChunker()
chunks = chunker.chunk(text)

# Custom chunking for large documents
chunker = TextChunker(
    chunk_size=1000,
    chunk_overlap=100,
    strategy=ChunkingStrategy.BY_PARAGRAPH
)
chunks = chunker.chunk(text)

# Each chunk has metadata
for chunk in chunks:
    print(f"Chunk {chunk.index}: {len(chunk.text)} chars")
    print(f"  Start: {chunk.start_char}, End: {chunk.end_char}")
```

### Full Pipeline (Parse + Chunk)

```python
from vizu_parsers import parse_and_chunk

# Parse file and chunk in one step
chunks = parse_and_chunk(
    file_path="document.pdf",
    chunk_size=512,
    chunk_overlap=50
)

for chunk in chunks:
    print(f"Chunk {chunk.index}: {chunk.text[:100]}...")
```

## Chunking Strategies

- `BY_SENTENCE`: Split on sentence boundaries (good for Q&A)
- `BY_PARAGRAPH`: Split on paragraph boundaries (good for summaries)
- `BY_TOKEN`: Split by token count (most precise for embeddings)
- `SEMANTIC`: Tries to keep related content together (default)

## Integration with Embedding Service

The chunker is designed to work with the `embedding_service`:

```python
from vizu_parsers import parse_and_chunk
import requests

# Parse and chunk a document
chunks = parse_and_chunk("manual.pdf", chunk_size=512)

# Send chunks to embedding service
texts = [chunk.text for chunk in chunks]
response = requests.post(
    "http://embedding_service:11435/embed",
    json={"texts": texts, "mode": "document"}
)
embeddings = response.json()["embeddings"]
```
