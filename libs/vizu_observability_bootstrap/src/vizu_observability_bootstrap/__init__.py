import logging
import os
from urllib.parse import urlparse, unquote

from fastapi import FastAPI
from opentelemetry import trace
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
    setup_grafana_logging,
)

# Export health check utilities
from .health import (
    check_database_url,
    check_http_endpoint,
    check_qdrant_url,
    check_redis_url,
    create_health_router,
)
from .logger import setup_structured_logging

__all__ = [
    "setup_telemetry",
    "setup_structured_logging",
    # Health
    "create_health_router",
    "check_database_url",
    "check_redis_url",
    "check_qdrant_url",
    "check_http_endpoint",
    # Grafana/Logging
    "setup_grafana_logging",
    "create_grafana_logger",
    "record_metric",
    "is_grafana_enabled",
    "GrafanaLokiFormatter",
]

logger = logging.getLogger(__name__)


def setup_telemetry(app: FastAPI, service_name: str):
    """
    Configure OpenTelemetry tracing for a FastAPI app.

    Supports:
    - Grafana Cloud OTLP (HTTPS with Basic Auth)
    - Local OTLP collector (gRPC)
    - No-op fallback (silent, no console spam)

    Environment variables:
    - OTEL_EXPORTER_OTLP_ENDPOINT: OTLP endpoint URL
    - OTEL_EXPORTER_OTLP_HEADERS: Headers (URL-encoded, e.g., "Authorization=Basic%20...")
    """
    resource = Resource(attributes={"service.name": service_name})
    tracer_provider = TracerProvider(resource=resource)

    otlp_endpoint = os.environ.get("OTEL_EXPORTER_OTLP_TRACES_ENDPOINT") or os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT")
    otlp_headers_raw = os.environ.get("OTEL_EXPORTER_OTLP_HEADERS", "")

    # Parse headers from URL-encoded format: "Key1=Value1,Key2=Value2"
    headers = {}
    if otlp_headers_raw:
        for pair in otlp_headers_raw.split(","):
            if "=" in pair:
                key, value = pair.split("=", 1)
                headers[unquote(key)] = unquote(value)

    exporter = None

    if otlp_endpoint:
        parsed = urlparse(otlp_endpoint)

        # Grafana Cloud and other HTTPS endpoints use HTTP/protobuf
        if parsed.scheme == "https":
            try:
                from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter as HTTPSpanExporter
                exporter = HTTPSpanExporter(
                    endpoint=f"{otlp_endpoint}/v1/traces",
                    headers=headers,
                )
                logger.info(f"OTLP HTTP exporter configured: {otlp_endpoint}")
            except ImportError:
                logger.warning("opentelemetry-exporter-otlp-proto-http not installed, tracing disabled")
            except Exception as e:
                logger.warning(f"Failed to configure OTLP HTTP exporter: {e}")
        else:
            # Local gRPC collector (http:// or grpc://)
            try:
                from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter as GRPCSpanExporter
                exporter = GRPCSpanExporter(endpoint=otlp_endpoint)
                logger.info(f"OTLP gRPC exporter configured: {otlp_endpoint}")
            except ImportError:
                logger.warning("opentelemetry-exporter-otlp-proto-grpc not installed, tracing disabled")
            except Exception as e:
                logger.warning(f"Failed to configure OTLP gRPC exporter: {e}")
    else:
        # No endpoint configured - tracing disabled (silent, no console spam)
        logger.info("No OTEL_EXPORTER_OTLP_ENDPOINT configured, tracing disabled")

    if exporter:
        processor = BatchSpanProcessor(exporter)
        tracer_provider.add_span_processor(processor)

    trace.set_tracer_provider(tracer_provider)
    FastAPIInstrumentor.instrument_app(app)
    setup_structured_logging()

    logger.info(f"Telemetry configured for service: {service_name}")
