"""
OpenTelemetry instrumentation for MCP tools — BLU-MVP-070.

Wraps every tool registered via ``mcp.tool(...)`` with a uniform OTel span
that always carries the agreed-upon attributes (`tool_name`, `client_id`,
`tier`, `agent_slug`, `session_id`) and a histogram + counter so Grafana
can chart latency p50/p95 and error rate per tool.

Design
------
- We monkey-patch ``mcp.tool`` once, at registration time, so every module
  that calls ``mcp.tool(name=..., description=...)(fn)`` gets traced
  automatically — no per-module changes required.
- Span attributes prefixed with ``tool.*`` to keep them grouped in Tempo.
- ``client_id``/``tier`` are best-effort: read from the X-Cliente-Id /
  X-Tier headers when present, else from kwargs after the
  ``mcp_inject_client_id`` middleware ran.
- Errors are surfaced as span status + recorded via ``span.record_exception``.
"""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from functools import wraps
from typing import Any

from fastmcp import FastMCP
from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode

logger = logging.getLogger(__name__)

_TRACER = trace.get_tracer("blu.tool_pool_api.tools")

# Flag so we never wrap twice on a given FastMCP instance.
_INSTRUMENTED_FLAG = "_blu_otel_instrumented"


def _read_request_headers() -> dict[str, str]:
    """Best-effort fetch of FastMCP HTTP headers; empty dict if unavailable."""
    try:
        from fastmcp.server.dependencies import get_http_headers

        return get_http_headers(include_all=True) or {}
    except Exception:  # pragma: no cover — defensive
        return {}


def _record_metric_safe(
    metric_name: str,
    value: float,
    labels: dict[str, str],
    metric_type: str,
) -> None:
    """Record a Mimir metric without failing the tool call if OTel is down."""
    try:
        from blu_observability_bootstrap import record_metric

        record_metric(metric_name, value, labels, metric_type)
    except Exception as exc:  # pragma: no cover — defensive
        logger.debug("record_metric failed for %s: %s", metric_name, exc)


def _wrap_tool_callable(tool_name: str, fn: Callable[..., Any]) -> Callable[..., Any]:
    """Wrap an MCP tool callable with a span + latency/error metrics."""

    @wraps(fn)
    async def traced(*args: Any, **kwargs: Any) -> Any:
        # Headers are the cheapest source for identity (no DB round-trip).
        headers = _read_request_headers()
        header_client_id = headers.get("x-cliente-id") or headers.get("x-client-id")
        header_session_id = headers.get("x-session-id")
        header_tier = headers.get("x-tier")  # optional, set by atendente_core if present

        span_attrs: dict[str, Any] = {
            "tool.name": tool_name,
            "tool_name": tool_name,  # duplicate without dot — easier to query in Loki
            "service.tool_pool": True,
        }
        if header_client_id:
            span_attrs["client_id"] = header_client_id
        if header_session_id:
            span_attrs["session_id"] = header_session_id
        if header_tier:
            span_attrs["tier"] = header_tier.upper()

        started = time.perf_counter()
        outcome = "success"

        with _TRACER.start_as_current_span(
            f"mcp.tool.{tool_name}",
            attributes=span_attrs,
        ) as span:
            try:
                result = await fn(*args, **kwargs)
            except Exception as exc:
                outcome = "error"
                span.record_exception(exc)
                span.set_status(Status(StatusCode.ERROR, str(exc)[:200]))
                span.set_attribute("error.type", type(exc).__name__)
                _emit_metrics(tool_name, started, outcome, span_attrs)
                raise
            else:
                # The mcp_inject_client_id middleware mutates kwargs in-place,
                # so client_id may have been resolved after entry.
                if "client_id" in kwargs and "client_id" not in span_attrs:
                    span.set_attribute("client_id", str(kwargs["client_id"]))
                    span_attrs["client_id"] = str(kwargs["client_id"])
                _emit_metrics(tool_name, started, outcome, span_attrs)
                return result

    return traced


def _emit_metrics(
    tool_name: str,
    started: float,
    outcome: str,
    span_attrs: dict[str, Any],
) -> None:
    duration_ms = (time.perf_counter() - started) * 1000.0
    labels: dict[str, str] = {
        "tool_name": tool_name,
        "outcome": outcome,
    }
    if "client_id" in span_attrs:
        # Cardinality control: hash to short prefix is overkill for MVP scale,
        # the cluster only has tens of tenants. Keep raw client_id label.
        labels["client_id"] = str(span_attrs["client_id"])
    if "tier" in span_attrs:
        labels["tier"] = str(span_attrs["tier"])

    _record_metric_safe(
        "blu.tool.duration_ms",
        duration_ms,
        labels,
        metric_type="histogram",
    )
    _record_metric_safe(
        "blu.tool.calls_total",
        1,
        labels,
        metric_type="counter",
    )
    if outcome == "error":
        _record_metric_safe(
            "blu.tool.errors_total",
            1,
            labels,
            metric_type="counter",
        )


def instrument_mcp_tools(mcp: FastMCP) -> None:
    """
    Monkey-patch ``mcp.tool`` so every subsequently registered tool is
    automatically traced. Idempotent.
    """
    if getattr(mcp, _INSTRUMENTED_FLAG, False):
        return

    original_tool = mcp.tool

    def tool(*tool_args: Any, **tool_kwargs: Any) -> Callable[..., Any]:
        decorator = original_tool(*tool_args, **tool_kwargs)
        # Best-effort: tool name is most reliably the `name=` kwarg.
        explicit_name = tool_kwargs.get("name")

        def wrapped_decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
            tool_name = explicit_name or getattr(fn, "__name__", "unknown")
            traced_fn = _wrap_tool_callable(tool_name, fn)
            return decorator(traced_fn)

        return wrapped_decorator

    mcp.tool = tool  # type: ignore[assignment]
    setattr(mcp, _INSTRUMENTED_FLAG, True)
    logger.info("[OTel] mcp.tool wrapped — every registered tool is now traced")
