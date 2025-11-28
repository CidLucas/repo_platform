# Vizu File Upload API

This service provides a synchronous API for uploading and queuing files in the Vizu application.

## Overview

The Vizu File Upload API is a FastAPI application that handles file uploads from clients. When a file is uploaded, this service stores it in a Google Cloud Storage bucket and then publishes a message to a Pub/Sub topic to trigger a file processing worker.

### Key Technologies

*   **Framework:** FastAPI
*   **Cloud:** Google Cloud Platform (Cloud Storage, Pub/Sub)
*   **Package Manager:** Poetry
