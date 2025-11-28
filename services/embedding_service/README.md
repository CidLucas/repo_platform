# Vizu Embedding Service

This microservice is responsible for serving HuggingFace embedding models.

## Overview

The Vizu Embedding Service is a FastAPI application that provides an API for generating text embeddings using models from the HuggingFace Hub. It is used by other services in the Vizu ecosystem, such as the `file_processing_worker`, to create vector representations of text data.

### Key Technologies

*   **Framework:** FastAPI
*   **Embeddings:** HuggingFace, Sentence Transformers
*   **Package Manager:** Poetry
