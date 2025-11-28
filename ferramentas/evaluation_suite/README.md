# Vizu Evaluation Suite

This directory contains the source code for the Vizu Evaluation Suite, a Streamlit application used for evaluating the Vizu APIs.

## Overview

The Evaluation Suite is a tool for testing and validating the performance of the Vizu APIs, including prompts, models, and business logic.

### Key Technologies

*   **Framework:** Streamlit
*   **Data Manipulation:** Pandas
*   **HTTP Client:** httpx
*   **Package Manager:** Poetry

## Getting Started

The Evaluation Suite is run as a Docker container, as defined in the `docker-compose.yml` file. To run the suite, use the following command:

```bash
docker-compose up evaluation_suite
```

This will start the Streamlit application, which can be accessed at `http://localhost:8501`.
