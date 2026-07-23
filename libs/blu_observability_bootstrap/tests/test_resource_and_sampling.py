"""Unit tests for the 0.3.0 increments: resource_attributes merge + error-biased sampling."""

import pytest
from fastapi import FastAPI
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from opentelemetry.trace import Status, StatusCode

from blu_observability_bootstrap import (
    ErrorBiasedSpanProcessor,
    _resolve_sampling_ratio,
    setup_observability,
)


# ---------------------------------------------------------------------------
# _resolve_sampling_ratio
# ---------------------------------------------------------------------------


def test_ratio_defaults_to_one(monkeypatch):
    monkeypatch.delenv("OTEL_TRACES_SAMPLER_ARG", raising=False)
    assert _resolve_sampling_ratio(None) == 1.0


def test_ratio_from_env(monkeypatch):
    monkeypatch.setenv("OTEL_TRACES_SAMPLER_ARG", "0.1")
    assert _resolve_sampling_ratio(None) == 0.1


def test_explicit_ratio_wins_over_env(monkeypatch):
    monkeypatch.setenv("OTEL_TRACES_SAMPLER_ARG", "0.1")
    assert _resolve_sampling_ratio(0.5) == 0.5


def test_invalid_env_falls_back_to_one(monkeypatch):
    monkeypatch.setenv("OTEL_TRACES_SAMPLER_ARG", "banana")
    assert _resolve_sampling_ratio(None) == 1.0


def test_ratio_is_clamped():
    assert _resolve_sampling_ratio(7.0) == 1.0
    assert _resolve_sampling_ratio(-1.0) == 0.0


# ---------------------------------------------------------------------------
# ErrorBiasedSpanProcessor
# ---------------------------------------------------------------------------


def _make_provider(ratio: float) -> tuple[TracerProvider, InMemorySpanExporter]:
    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(ErrorBiasedSpanProcessor(exporter, ratio))
    return provider, exporter


def test_ratio_zero_exports_only_errors():
    provider, exporter = _make_provider(0.0)
    tracer = provider.get_tracer("test")

    with tracer.start_as_current_span("ok_span"):
        pass
    with tracer.start_as_current_span("error_span") as span:
        span.set_status(Status(StatusCode.ERROR, "boom"))

    provider.force_flush()
    exported = [s.name for s in exporter.get_finished_spans()]
    assert exported == ["error_span"]


def test_ratio_one_exports_everything():
    provider, exporter = _make_provider(1.0)
    tracer = provider.get_tracer("test")

    with tracer.start_as_current_span("ok_span"):
        pass

    provider.force_flush()
    assert [s.name for s in exporter.get_finished_spans()] == ["ok_span"]


def test_partial_ratio_keeps_or_drops_whole_traces():
    """Spans of the same trace share the sampling decision (deterministic trace_id test)."""
    provider, exporter = _make_provider(0.5)
    tracer = provider.get_tracer("test")

    for i in range(50):
        with tracer.start_as_current_span(f"root_{i}"):
            with tracer.start_as_current_span(f"child_{i}"):
                pass

    provider.force_flush()
    spans = exporter.get_finished_spans()
    # Some traces in, some out at ratio 0.5 over 50 traces
    assert 0 < len(spans) < 100
    # Whole-trace consistency: a child is exported iff its root is
    by_trace: dict[int, set[str]] = {}
    for s in spans:
        by_trace.setdefault(s.context.trace_id, set()).add(s.name.split("_")[0])
    for names in by_trace.values():
        assert names == {"root", "child"}


# ---------------------------------------------------------------------------
# setup_observability: resource_attributes merged into the Resource
# ---------------------------------------------------------------------------


def test_setup_observability_merges_resource_attributes(monkeypatch):
    monkeypatch.delenv("OTEL_EXPORTER_OTLP_ENDPOINT", raising=False)
    monkeypatch.delenv("OTEL_EXPORTER_OTLP_TRACES_ENDPOINT", raising=False)

    from opentelemetry import trace

    # Reset global provider so set_tracer_provider takes effect in this test
    trace._TRACER_PROVIDER_SET_ONCE._done = False
    trace._TRACER_PROVIDER = None

    app = FastAPI()
    setup_observability(
        app,
        "svc-test",
        langfuse=False,
        export_logs=False,
        export_metrics=False,
        resource_attributes={
            "app_name": "agents-platform",
            "environment": "dev",
            "version": "1.2.3",
        },
    )

    resource = trace.get_tracer_provider().resource
    assert resource.attributes["service.name"] == "svc-test"
    assert resource.attributes["app_name"] == "agents-platform"
    assert resource.attributes["environment"] == "dev"
    assert resource.attributes["version"] == "1.2.3"
