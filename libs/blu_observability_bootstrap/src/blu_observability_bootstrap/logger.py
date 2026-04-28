import logging
import os

from pythonjsonlogger import jsonlogger


def setup_structured_logging():
    """
    Configure Python root logger for structured JSON output.

    This function removes existing handlers, creates a JSON formatter that
    automatically includes OpenTelemetry trace/span IDs, and adds a handler
    for stdout.

    Log level is controlled by LOG_LEVEL env var (default: INFO).
    """
    logger = logging.getLogger()

    # Remove existing handlers to avoid duplicate logs
    if logger.hasHandlers():
        logger.handlers.clear()

    # Create stdout handler
    handler = logging.StreamHandler()

    # JSON formatter with trace context
    formatter = jsonlogger.JsonFormatter(
        "%(asctime)s %(name)s %(levelname)s %(message)s %(trace_id)s %(span_id)s"
    )

    handler.setFormatter(formatter)
    logger.addHandler(handler)

    # Set level from env (default INFO, can be DEBUG for troubleshooting)
    log_level = os.environ.get("LOG_LEVEL", "INFO").upper()
    logger.setLevel(getattr(logging, log_level, logging.INFO))

    # Silence verbose third-party loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("langfuse").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("opentelemetry").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("anyio").setLevel(logging.WARNING)
