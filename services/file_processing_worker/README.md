# Vizu File Processing Worker

> **⚠️ DEPRECATED** — This service is replaced by the Supabase-based RAG pipeline.
> Simple files are processed by the `process-document` Edge Function.
> Complex files are processed by `file_upload_api /v1/upload/process` with docling.
> See `docs/RAG_MIGRATION_GUIDE.md` for details.

This service is an asynchronous worker responsible for processing and embedding files.

## Overview

The Vizu File Processing Worker is an asynchronous worker that is triggered by messages on a Pub/Sub topic. When a new file is uploaded via the `file_upload_api`, a message is sent to the topic. This worker consumes the message, downloads the file from Google Cloud Storage, processes its content, and generates embeddings. The embeddings are then stored in the Qdrant vector database.

### Key Technologies

*   **Cloud:** Google Cloud Platform (Pub/Sub, Cloud Storage)
*   **Text Processing:** LangChain, PyPDF, Pandas
*   **Vector Database:** Qdrant
*   **Package Manager:** Poetry
