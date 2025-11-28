# Vizu Tool Pool API

This service provides a client-agnostic pool of tools for the Vizu application.

## Overview

The Vizu Tool Pool API is a FastAPI application that acts as a central repository for tools that can be used by the `atendente_core` service. It uses `fastmcp` to expose a variety of tools, such as RAG and SQL tools, which are created using the `vizu_rag_factory` and `vizu_sql_factory` libraries.

This service allows for the dynamic addition and removal of tools without requiring a restart of the `atendente_core` service.

### Key Technologies

*   **Framework:** FastAPI
*   **Tooling:** FastMCP
*   **Package Manager:** Poetry
