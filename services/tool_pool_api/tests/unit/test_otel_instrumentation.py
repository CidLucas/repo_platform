"""BLU-MVP-070 — unit tests for OTel instrumentation of MCP tools."""

from __future__ import annotations

import asyncio
from unittest.mock import MagicMock

import pytest


def _make_fake_mcp() -> MagicMock:
    """Minimal fake FastMCP with a working ``.tool(...)`` decorator API."""
    mcp = MagicMock(spec=["tool"])
    registered: dict[str, callable] = {}

    def tool(*, name: str, description: str = "", **_kw):
        def decorator(fn):
            registered[name] = fn
            return fn

        return decorator

    mcp.tool = tool
    mcp._registered = registered  # type: ignore[attr-defined]
    return mcp


def test_instrument_mcp_tools_wraps_registered_callables(monkeypatch):
    from tool_pool_api.server.otel_instrumentation import instrument_mcp_tools

    mcp = _make_fake_mcp()
    instrument_mcp_tools(mcp)

    async def my_logic(*, cliente_id: str | None = None) -> str:
        return f"hello-{cliente_id}"

    mcp.tool(name="probe_tool", description="probe")(my_logic)

    wrapped = mcp._registered["probe_tool"]
    assert wrapped is not my_logic, "tool callable must be wrapped"

    # Wrapper must remain awaitable & return the original result.
    result = asyncio.run(wrapped(cliente_id="abc-123"))
    assert result == "hello-abc-123"


def test_instrument_mcp_tools_is_idempotent():
    from tool_pool_api.server.otel_instrumentation import instrument_mcp_tools

    mcp = _make_fake_mcp()
    instrument_mcp_tools(mcp)
    first_tool = mcp.tool
    instrument_mcp_tools(mcp)  # second call — must be a no-op
    assert mcp.tool is first_tool, "instrumentation must not double-wrap"


def test_wrapped_tool_preserves_exceptions():
    from tool_pool_api.server.otel_instrumentation import instrument_mcp_tools

    mcp = _make_fake_mcp()
    instrument_mcp_tools(mcp)

    async def boom():
        raise RuntimeError("boom")

    mcp.tool(name="boom_tool", description="x")(boom)
    with pytest.raises(RuntimeError, match="boom"):
        asyncio.run(mcp._registered["boom_tool"]())
