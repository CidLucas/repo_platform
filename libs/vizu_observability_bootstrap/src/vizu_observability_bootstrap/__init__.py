"""
Vizu Observability Bootstrap

Unified observability setup for all Vizu services:
- OTLP traces → Grafana Tempo
- OTLP logs (INFO+ by default) → Grafana Loki
- OTLP metrics → Grafana Mimir
- Langfuse → LLM tracing with prompt versioning

Usage:
    from vizu_observability_bootstrap import setup_observability

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        yield
        await shutdown_observability()

    app = FastAPI(lifespan=lifespan)
    setup_observability(app, "my-service")
"""

from __future__ import annotations

import asyncio
import logging
import os
import warnings
from typing import TYPE_CHECKING, Any, Callable, Coroutine
from urllib.parse import unquote, urlparse

from fastapi import FastAPI
from opentelemetry import trace, metrics
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

# Export Grafana/observability integration
from .grafana import (
    GrafanaLokiFormatter,
    create_grafana_logger,
    is_grafana_enabled,
    record_metric,
)

# Export health check utilities
from .health import (
    check_database_url,
    check_http_endpoint,
    check_redis_url,
    create_health_router,
)

# Export Langfuse integration
from .langfuse import (
    LangfusePromptClient,
    flush_langfuse,
    flush_langfuse_async,
    get_langfuse_callback,
    is_langfuse_enabled,
    shutdown_langfuse,
    shutdown_langfuse_async,
)
from .logger import setup_structured_logging

if TYPE_CHECKING:
    from opentelemetry.sdk.metrics import MeterProvider
    from opentelemetry.sdk._logs import LoggerProvider

__all__ = [
    # Main setup
    "setup_observability",
    "shutdown_observability",
    "setup_structured_logging",
    # Health
    "create_health_router",
    "check_database_url",
    "check_redis_url",
    "check_http_endpoint",
    # Grafana/Logging
    "create_grafana_logger",
    "record_metric",
    "is_grafana_enabled",
    "GrafanaLokiFormatter",
    # Langfuse
    "get_langfuse_callback",
    "is_langfuse_enabled",
    "LangfusePromptClient",
    "flush_langfuse",
    "flush_langfuse_async",
    "shutdown_langfuse",
    "shutdown_langfuse_async",
]

logger = logging.getLogger(__name__)

# Global providers for shutdown
_tracer_provider: TracerProvider | None = None
_meter_provider: Any = None
_logger_provider: Any = None


def _parse_otlp_headers(headers_raw: str) -> dict[str, str]:
    """Parse URL-encoded OTLP headers: 'Key1=Value1,Key2=Value2'"""
    headers = {}
    if headers_raw:
        for pair in headers_raw.split(","):
            if "=" in pair:
                key, value = pair.split("=", 1)
                headers[unquote(key)] = unquote(value)
    return headers


def _setup_tracer(
    resource: Resource,
    otlp_endpoint: str | None,
    headers: dict[str, str],
) -> TracerProvider:
    """Configure OTLP trace exporter."""
    global _tracer_provider

    tracer_provider = TracerProvider(resource=resource)
    exporter = None

    if otlp_endpoint:
        parsed = urlparse(otlp_endpoint)

        if parsed.scheme == "https":
            try:
                from opentelemetry.exporter.otlp.proto.http.trace_exporter import (
                    OTLPSpanExporter as HTTPSpanExporter,
                )

                exporter = HTTPSpanExporter(
                    endpoint=f"{otlp_endpoint}/v1/traces",
                    headers=headers,
                )
                logger.debug(f"OTLP HTTP trace exporter: {otlp_endpoint}")
            except ImportError:
                logger.warning("opentelemetry-exporter-otlp-proto-http not installed")
            except Exception as e:
                logger.warning(f"Failed to configure OTLP HTTP trace exporter: {e}")
        else:
            try:
                from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
                    OTLPSpanExporter as GRPCSpanExporter,
                )

                exporter = GRPCSpanExporter(endpoint=otlp_endpoint)
                logger.debug(f"OTLP gRPC trace exporter: {otlp_endpoint}")
            except ImportError:
                logger.warning("opentelemetry-exporter-otlp-proto-grpc not installed")
            except Exception as e:
                logger.warning(f"Failed to configure OTLP gRPC trace exporter: {e}")

    if exporter:
        processor = BatchSpanProcessor(exporter)
        tracer_provider.add_span_processor(processor)

    trace.set_tracer_provider(tracer_provider)
    _tracer_provider = tracer_provider
    return tracer_provider


def _setup_metrics(
    resource: Resource,
    otlp_endpoint: str | None,
    headers: dict[str, str],
) -> Any:
    """Configure OTLP metrics exporter."""
    global _meter_provider

    if not otlp_endpoint:
        logger.debug("No OTLP endpoint, metrics disabled")
        return None

    try:
        from opentelemetry.sdk.metrics import MeterProvider
        from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader

        parsed = urlparse(otlp_endpoint)

        if parsed.scheme == "https":
            from opentelemetry.exporter.otlp.proto.http.metric_exporter import (
                OTLPMetricExporter as HTTPMetricExporter,
            )

            exporter = HTTPMetricExporter(
                endpoint=f"{otlp_endpoint}/v1/metrics",
                headers=headers,
            )
        else:
            from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import (
                OTLPMetricExporter as GRPCMetricExporter,
            )

            exporter = GRPCMetricExporter(endpoint=otlp_endpoint)

        reader = PeriodicExportingMetricReader(exporter, export_interval_millis=60000)
        meter_provider = MeterProvider(resource=resource, metric_readers=[reader])
        metrics.set_meter_provider(meter_provider)
        _meter_provider = meter_provider
        logger.debug("OTLP metrics exporter configured")
        return meter_provider

    except ImportError:
        logger.warning("opentelemetry metrics exporter not installed")
        return None
    except Exception as e:
        logger.warning(f"Failed to configure OTLP metrics: {e}")
        return None


def _setup_logs(
    resource: Resource,
    otlp_endpoint: str | None,
    headers: dict[str, str],
    min_level: int = logging.WARNING,
) -> Any:
    """
    Configure OTLP logs exporter with level filter.

    Only exports logs at min_level and above (default: WARNING).
    """
    global _logger_provider

    if not otlp_endpoint:
        logger.debug("No OTLP endpoint, log export disabled")
        return None

    try:
        from opentelemetry._logs import set_logger_provider
        from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
        from opentelemetry.sdk._logs.export import BatchLogRecordProcessor

        parsed = urlparse(otlp_endpoint)

        if parsed.scheme == "https":
            from opentelemetry.exporter.otlp.proto.http._log_exporter import (
                OTLPLogExporter as HTTPLogExporter,
            )

            exporter = HTTPLogExporter(
                endpoint=f"{otlp_endpoint}/v1/logs",
                headers=headers,
            )
        else:
            from opentelemetry.exporter.otlp.proto.grpc._log_exporter import (
                OTLPLogExporter as GRPCLogExporter,
            )

            exporter = GRPCLogExporter(endpoint=otlp_endpoint)

        logger_provider = LoggerProvider(resource=resource)
        logger_provider.add_log_record_processor(BatchLogRecordProcessor(exporter))
        set_logger_provider(logger_provider)

        # Add handler to root logger with level filter
        handler = LoggingHandler(level=min_level, logger_provider=logger_provider)
        logging.getLogger().addHandler(handler)

        _logger_provider = logger_provider
        logger.debug(f"OTLP logs exporter configured (min_level={logging.getLevelName(min_level)})")
        return logger_provider

    except ImportError:
        logger.warning("opentelemetry logs exporter not installed")
        return None
    except Exception as e:
        logger.warning(f"Failed to configure OTLP logs: {e}")
        return None


def setup_observability(
    app: FastAPI,
    service_name: str,
    *,
    otlp: bool = True,
    langfuse: bool = True,
    export_logs: bool = True,
    export_metrics: bool = True,
    log_min_level: int = logging.INFO,
    excluded_urls: list[str] | None = None,
) -> None:
    """
    Unified observability setup for Vizu services.

    Configures:
    - OTLP traces → Grafana Tempo
    - OTLP logs (INFO+ by default) → Grafana Loki
    - OTLP metrics → Grafana Mimir
    - Langfuse → LLM tracing (validates credentials)

    Args:
        app: FastAPI application instance
        service_name: Service name for telemetry resource
        otlp: Enable OTLP trace/log/metric export
        langfuse: Validate Langfuse is configured (warn if not)
        export_logs: Export logs via OTLP (WARN+ only)
        export_metrics: Export metrics via OTLP
        log_min_level: Minimum log level to export (default: INFO)
        excluded_urls: URL patterns to exclude from tracing (e.g., ["/mcp", "/health"])

    Environment variables:
        OTEL_EXPORTER_OTLP_ENDPOINT: OTLP gateway URL
        OTEL_EXPORTER_OTLP_HEADERS: Auth headers (URL-encoded)
        LANGFUSE_PUBLIC_KEY: Langfuse public key
        LANGFUSE_SECRET_KEY: Langfuse secret key
        LANGFUSE_HOST: Langfuse server (default: cloud.langfuse.com)
    """
    # Setup structured logging first (stdout JSON)
    setup_structured_logging()

    resource = Resource(attributes={"service.name": service_name})
    otlp_endpoint = os.environ.get("OTEL_EXPORTER_OTLP_TRACES_ENDPOINT") or os.environ.get(
        "OTEL_EXPORTER_OTLP_ENDPOINT"
    )
    headers = _parse_otlp_headers(os.environ.get("OTEL_EXPORTER_OTLP_HEADERS", ""))

    # Check if traces are explicitly disabled
    traces_exporter = os.environ.get("OTEL_TRACES_EXPORTER", "").lower()
    traces_disabled = traces_exporter == "none"

    # Default excluded URLs (MCP SSE creates noisy empty traces, health checks are noisy)
    default_excluded = ["/mcp", "/health", "/ready", "/live"]
    all_excluded = (excluded_urls or []) + default_excluded

    # Build exclusion pattern for OTEL (comma-separated URL patterns)
    exclude_pattern = ",".join(all_excluded) if all_excluded else None

    # OTLP Traces
    if otlp and not traces_disabled:
        _setup_tracer(resource, otlp_endpoint, headers)
        FastAPIInstrumentor.instrument_app(app, excluded_urls=exclude_pattern)

        if export_metrics:
            _setup_metrics(resource, otlp_endpoint, headers)

        if export_logs:
            _setup_logs(resource, otlp_endpoint, headers, min_level=log_min_level)
    elif traces_disabled:
        logger.info("OTLP traces disabled via OTEL_TRACES_EXPORTER=none")
        # Still setup metrics and logs if requested
        if otlp and export_metrics:
            _setup_metrics(resource, otlp_endpoint, headers)
        if otlp and export_logs:
            _setup_logs(resource, otlp_endpoint, headers, min_level=log_min_level)

    # Langfuse validation
    if langfuse:
        if is_langfuse_enabled():
            from .langfuse import get_langfuse_settings

            settings = get_langfuse_settings()
            logger.debug(f"Langfuse enabled: {settings['host']}")
        else:
            logger.warning(
                "Langfuse not configured (missing LANGFUSE_PUBLIC_KEY/SECRET_KEY). "
                "LLM tracing disabled."
            )

    logger.info(f"Observability configured for: {service_name}")


def setup_telemetry(app: FastAPI, service_name: str) -> None:
    """
    Configure OpenTelemetry tracing for a FastAPI app.

    .. deprecated:: 1.0
        Use :func:`setup_observability` instead for full stack (traces + logs + metrics).
    """
    warnings.warn(
        "setup_telemetry() is deprecated. Use setup_observability() instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    setup_observability(
        app,
        service_name,
        otlp=True,
        langfuse=False,
        export_logs=False,
        export_metrics=False,
    )


async def shutdown_observability(timeout: float = 5.0) -> None:
    """
    Gracefully shutdown observability providers.

    Call this in your FastAPI lifespan shutdown handler.

    Args:
        timeout: Maximum seconds to wait for flush operations
    """
    # Flush Langfuse first (async with timeout)
    await flush_langfuse_async(timeout=timeout)

    # Force flush OTLP providers
    if _tracer_provider:
        try:
            _tracer_provider.force_flush(timeout_millis=int(timeout * 1000))
            logger.debug("Tracer provider flushed")
        except Exception as e:
            logger.warning(f"Tracer flush failed: {e}")

    if _logger_provider:
        try:
            _logger_provider.force_flush(timeout_millis=int(timeout * 1000))
            logger.debug("Logger provider flushed")
        except Exception as e:
            logger.warning(f"Logger flush failed: {e}")

    if _meter_provider:
        try:
            _meter_provider.force_flush(timeout_millis=int(timeout * 1000))
            logger.debug("Meter provider flushed")
        except Exception as e:
            logger.warning(f"Meter flush failed: {e}")

    logger.debug("Observability shutdown complete")
