"""Telemetria de domínio: spans agent_execution + mcp_tool_call (RF03).

Constantes replicadas do schema comum de telemetria congelado no ops-centro
(docs/schema.md, v1) — mecanismo de compartilhamento é replicação + teste de
paridade (tests/unit/test_telemetry.py); mudança de schema passa por PR lá
primeiro. Sem strings soltas: todo nome de span/atributo sai daqui.

Emissão é assíncrona via BatchSpanProcessor configurado pela
blu_observability_bootstrap (RNF04); sem provider configurado, os spans são
no-op e nada disto custa nem quebra.
"""

from __future__ import annotations

import logging
import os
from contextlib import contextmanager
from typing import Any, Iterator

from opentelemetry import trace
from opentelemetry.trace import Span, Status, StatusCode

from blu_agent_framework.mcp_executor import MCPToolExecutor, ToolResult

logger = logging.getLogger(__name__)

# --- Schema comum v1 (réplica congelada; fonte: ops-centro/ops_centro/conventions.py)
ATTR_APP_NAME = "app_name"
ATTR_ENVIRONMENT = "environment"
ATTR_TENANT_ID = "tenant_id"
ATTR_VERSION = "version"

APP_AGENTS_PLATFORM = "agents-platform"

SPAN_AGENT_EXECUTION = "agent_execution"
SPAN_MCP_TOOL_CALL = "mcp_tool_call"

ATTR_AGENT_NAME = "agent_name"
ATTR_MODEL = "model"
ATTR_TOKENS_INPUT = "tokens_input"
ATTR_TOKENS_OUTPUT = "tokens_output"
ATTR_SESSION_ID = "session_id"
ATTR_TOOL_NAME = "tool_name"
ATTR_MCP_SERVER = "mcp_server"

_KNOWN_ENVIRONMENTS = frozenset({"dev", "staging", "prod"})

_tracer = trace.get_tracer("agent_api")


def common_resource_attributes() -> dict[str, str]:
    """Atributos comuns do RF02 para o Resource (todo sinal os carrega).

    environment vem de ENVIRONMENT (fora do vocabulário canônico → warning e
    fallback para dev, sem derrubar o startup); version de APP_VERSION ou do
    pacote instalado. tenant_id é por request, nunca no Resource.
    """
    environment = os.environ.get("ENVIRONMENT", "dev")
    if environment not in _KNOWN_ENVIRONMENTS:
        logger.warning(
            "ENVIRONMENT=%r fora do vocabulário canônico %s — usando 'dev'",
            environment, sorted(_KNOWN_ENVIRONMENTS),
        )
        environment = "dev"

    version = os.environ.get("APP_VERSION", "")
    if not version:
        try:
            from importlib.metadata import version as pkg_version

            version = pkg_version("agent-api")
        except Exception:
            version = "0.0.0"

    return {
        ATTR_APP_NAME: APP_AGENTS_PLATFORM,
        ATTR_ENVIRONMENT: environment,
        ATTR_VERSION: version,
    }


@contextmanager
def agent_execution_span(
    *,
    agent_name: str,
    tenant_id: str | None = None,
    session_id: str | None = None,
    model: str | None = None,
) -> Iterator[Span]:
    """Span pai de uma execução de agente (§6 do plano).

    Exceção dentro do bloco → record_exception + status ERROR (default do SDK);
    saída limpa → status OK. Duração é implícita do span.
    """
    with _tracer.start_as_current_span(SPAN_AGENT_EXECUTION) as span:
        span.set_attribute(ATTR_AGENT_NAME, agent_name)
        if tenant_id:
            span.set_attribute(ATTR_TENANT_ID, str(tenant_id))
        if session_id:
            span.set_attribute(ATTR_SESSION_ID, session_id)
        if model:
            span.set_attribute(ATTR_MODEL, model)
        yield span
        span.set_status(Status(StatusCode.OK))


def set_usage_attributes(span: Span, messages: list[Any]) -> None:
    """Soma usage_metadata das AIMessages da execução em tokens_input/tokens_output."""
    tokens_in = tokens_out = 0
    for msg in messages or []:
        usage = getattr(msg, "usage_metadata", None)
        if usage:
            tokens_in += usage.get("input_tokens", 0) or 0
            tokens_out += usage.get("output_tokens", 0) or 0
    if tokens_in:
        span.set_attribute(ATTR_TOKENS_INPUT, tokens_in)
    if tokens_out:
        span.set_attribute(ATTR_TOKENS_OUTPUT, tokens_out)


class InstrumentedMCPToolExecutor(MCPToolExecutor):
    """MCPToolExecutor que emite um span mcp_tool_call por chamada (RF03).

    Todo tool call dos graphs passa por execute() — vira span filho do
    agent_execution ativo no contexto. tenant_id vem do context por request,
    não do Resource. execute() nunca levanta (converte falha em ToolResult),
    então o status sai de result.success.
    """

    async def execute(
        self,
        tool_name: str,
        tool_args: dict[str, Any],
        context: dict[str, Any],
    ) -> ToolResult:
        with _tracer.start_as_current_span(SPAN_MCP_TOOL_CALL) as span:
            span.set_attribute(ATTR_TOOL_NAME, tool_name)
            span.set_attribute(ATTR_MCP_SERVER, self.mcp_url)
            tenant_id = (context or {}).get("client_id")
            if tenant_id:
                span.set_attribute(ATTR_TENANT_ID, str(tenant_id))

            result = await super().execute(tool_name, tool_args, context)

            if result.success:
                span.set_status(Status(StatusCode.OK))
            else:
                span.set_status(Status(StatusCode.ERROR, (result.error or "")[:200]))
            return result
