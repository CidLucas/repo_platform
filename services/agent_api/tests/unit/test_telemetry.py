"""Testes dos spans agent_execution/mcp_tool_call e da paridade do schema comum.

O teste de paridade pina os valores literais do schema v1 congelado no ops-centro
(docs/schema.md §4) — o mesmo teste existe lá; os dois só mudam juntos.
"""

from __future__ import annotations

import pytest
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from opentelemetry.trace import StatusCode

from agent_api.core import telemetry as t
from blu_agent_framework.mcp_executor import MCPToolExecutor, ToolResult

_exporter = InMemorySpanExporter()


@pytest.fixture(autouse=True)
def _tracer_provider():
    # set_tracer_provider é once-per-process; força reset para testes
    trace._TRACER_PROVIDER_SET_ONCE._done = False
    trace._TRACER_PROVIDER = None
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(_exporter))
    trace.set_tracer_provider(provider)
    _exporter.clear()
    yield


def test_paridade_schema_congelado_v1():
    assert t.ATTR_APP_NAME == "app_name"
    assert t.ATTR_ENVIRONMENT == "environment"
    assert t.ATTR_TENANT_ID == "tenant_id"
    assert t.ATTR_VERSION == "version"
    assert t.APP_AGENTS_PLATFORM == "agents-platform"
    assert t.SPAN_AGENT_EXECUTION == "agent_execution"
    assert t.SPAN_MCP_TOOL_CALL == "mcp_tool_call"
    assert t.ATTR_AGENT_NAME == "agent_name"
    assert t.ATTR_MODEL == "model"
    assert t.ATTR_TOKENS_INPUT == "tokens_input"
    assert t.ATTR_TOKENS_OUTPUT == "tokens_output"
    assert t.ATTR_SESSION_ID == "session_id"
    assert t.ATTR_TOOL_NAME == "tool_name"
    assert t.ATTR_MCP_SERVER == "mcp_server"


def test_common_resource_attributes(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "prod")
    monkeypatch.setenv("APP_VERSION", "1.2.3")
    attrs = t.common_resource_attributes()
    assert attrs == {"app_name": "agents-platform", "environment": "prod", "version": "1.2.3"}


def test_common_resource_attributes_environment_invalido_cai_para_dev(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "producao")
    monkeypatch.setenv("APP_VERSION", "1.2.3")
    assert t.common_resource_attributes()["environment"] == "dev"


def test_agent_execution_span_sucesso():
    with t.agent_execution_span(
        agent_name="frontdesk", tenant_id="acme", session_id="s1", model="gpt-x"
    ):
        pass

    (span,) = _exporter.get_finished_spans()
    assert span.name == "agent_execution"
    assert span.attributes["agent_name"] == "frontdesk"
    assert span.attributes["tenant_id"] == "acme"
    assert span.attributes["session_id"] == "s1"
    assert span.attributes["model"] == "gpt-x"
    assert span.status.status_code is StatusCode.OK


def test_agent_execution_span_erro():
    with pytest.raises(RuntimeError):
        with t.agent_execution_span(agent_name="frontdesk", tenant_id="acme"):
            raise RuntimeError("boom")

    (span,) = _exporter.get_finished_spans()
    assert span.status.status_code is StatusCode.ERROR
    assert span.events[0].name == "exception"


def test_set_usage_attributes():
    class _Msg:
        def __init__(self, usage):
            self.usage_metadata = usage

    with t.agent_execution_span(agent_name="a", tenant_id="x") as span:
        t.set_usage_attributes(
            span,
            [_Msg({"input_tokens": 10, "output_tokens": 5}), _Msg({"input_tokens": 7}), object()],
        )

    (exported,) = _exporter.get_finished_spans()
    assert exported.attributes["tokens_input"] == 17
    assert exported.attributes["tokens_output"] == 5


async def test_mcp_tool_call_vira_span_filho(monkeypatch):
    async def _fake_execute(self, tool_name, tool_args, context):
        return ToolResult(tool_name=tool_name, success=True, result="ok")

    monkeypatch.setattr(MCPToolExecutor, "execute", _fake_execute)
    executor = t.InstrumentedMCPToolExecutor(mcp_url="http://mcp:8000/mcp")

    with t.agent_execution_span(agent_name="frontdesk", tenant_id="acme"):
        result = await executor.execute("execute_sql", {"q": "select 1"}, {"client_id": "acme"})

    assert result.success
    tool_span, parent_span = _exporter.get_finished_spans()
    assert tool_span.name == "mcp_tool_call"
    assert parent_span.name == "agent_execution"
    assert tool_span.parent.span_id == parent_span.context.span_id
    assert tool_span.attributes["tool_name"] == "execute_sql"
    assert tool_span.attributes["mcp_server"] == "http://mcp:8000/mcp"
    assert tool_span.attributes["tenant_id"] == "acme"
    assert tool_span.status.status_code is StatusCode.OK


async def test_mcp_tool_call_falha_marca_status_error(monkeypatch):
    async def _fake_execute(self, tool_name, tool_args, context):
        return ToolResult(tool_name=tool_name, success=False, error="tool exploded")

    monkeypatch.setattr(MCPToolExecutor, "execute", _fake_execute)
    executor = t.InstrumentedMCPToolExecutor(mcp_url="http://mcp:8000/mcp")

    result = await executor.execute("execute_sql", {}, {})

    assert not result.success
    (tool_span,) = _exporter.get_finished_spans()
    assert tool_span.status.status_code is StatusCode.ERROR
    assert "tool exploded" in tool_span.status.description
