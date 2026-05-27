# tool_pool_api/server/tool_modules/common_module.py
"""
Módulo Common - Ferramentas Públicas/Comuns

Este módulo contém tools públicas disponíveis para todos os clientes.

NOTA: Ferramentas de diagnóstico (ping, server_info) foram movidas para
endpoints HTTP determinísticos em mcp_server.py:
  - GET /health → health check para k8s/load balancers
  - GET /info   → metadata do servidor para admin/debug

Apenas ferramentas úteis para a LLM ficam aqui.
"""

import logging

from fastmcp import FastMCP

from . import register_module

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Catálogo fechado de slugs válidos no AgentTypeRegistry.
# Qualquer slug fora desta lista é normalizado via SLUG_ALIASES ou rejeitado.
# ---------------------------------------------------------------------------
_VALID_SLUGS: set[str] = {
    "context-gatherer",
    "crm",
    "estrategia",
    "compras",
    "financeiro",
    "agenda",
    "documentos",
    "synthesis",
    "data-analyst",
    "platform",
    "supplier-agent",
    "scheduler-agent",
    "doc-writer",
    "fiscal-agent",
}

# Aliases: slugs inventados pelo LLM → slug real
_SLUG_ALIASES: dict[str, str] = {
    # inserção / transações / registro
    "finance_strategy_specialist": "context-gatherer",
    "financeiro_especialista": "context-gatherer",
    "financial": "context-gatherer",
    "data_entry": "context-gatherer",
    "data_entry_nl": "context-gatherer",
    "register_transaction": "context-gatherer",
    "transacao": "context-gatherer",
    "transaction": "context-gatherer",
    "registro": "context-gatherer",
    # metas e rotinas
    "automatizacao_e_rotinas": "context-gatherer",
    "rotinas": "context-gatherer",
    "routines": "context-gatherer",
    "routine": "context-gatherer",
    "automation": "context-gatherer",
    "meta": "context-gatherer",
    "goals": "context-gatherer",
    "definir_meta": "context-gatherer",
    # fornecedores
    "fornecedor": "context-gatherer",
    "supplier": "context-gatherer",
    "add_supplier": "context-gatherer",
    # outros mapeamentos comuns
    "fiscal": "fiscal-agent",
    "fiscal_agent": "fiscal-agent",
    "crm_agent": "crm",
    "analytics": "data-analyst",
    "platform_agent": "platform",
    "scheduler": "scheduler-agent",
    "doc_writer": "doc-writer",
}


def _normalize_slug(slug: str) -> str:
    """Normaliza slug para catálogo válido. Retorna slug ou melhor guess."""
    if slug in _VALID_SLUGS:
        return slug
    normalized = _SLUG_ALIASES.get(slug)
    if normalized:
        logger.warning("[Common] route_to_specialist: slug=%r normalizado para %r", slug, normalized)
        return normalized
    # fallback seguro
    logger.error("[Common] route_to_specialist: slug=%r desconhecido — usando context-gatherer", slug)
    return "context-gatherer"


# =============================================================================
# LÓGICA DE NEGÓCIO (Testável)
# =============================================================================


def _ferramenta_publica_de_teste_logic() -> str:
    """
    Ferramenta de teste para verificar conectividade MCP.
    Útil para validar que o agente consegue executar tools.

    Returns:
        Mensagem de confirmação
    """
    logger.info("[Common] Ferramenta pública de teste executada.")
    return "Ferramenta pública executada com sucesso!"


def _route_to_specialist_logic(agent_slug: str, reason: str) -> str:
    """
    Sinaliza ao service.py que o frontdesk quer delegar para um especialista.

    O retorno segue o protocolo __ROUTE_TO_SPECIALIST__:<slug>:<reason>
    que service.py intercepta após graph.ainvoke() para instanciar o
    specialist_graph correto.  A tool em si não executa nada — é apenas
    um sinal estruturado que atravessa o estado do grafo.

    Args:
        agent_slug: Slug do especialista (ex: 'financeiro', 'compras', 'agenda').
        reason: Frase curta explicando por que o especialista é necessário.

    Returns:
        String de protocolo para interceptação pelo service.py.
    """
    logger.info("[Common] route_to_specialist: slug=%s reason=%s", agent_slug, reason)
    slug = _normalize_slug(agent_slug)
    return f"__ROUTE_TO_SPECIALIST__:{slug}:{reason}"


# =============================================================================
# REGISTRO DO MÓDULO
# =============================================================================


@register_module
def register_tools(mcp: FastMCP) -> list[str]:
    """Registra as tools do módulo Common."""

    @mcp.tool(
        name="ferramenta_publica_de_teste",
        description=(
            "[USO INTERNO] Ferramenta de diagnóstico para testes de conectividade. "
            "NÃO use para responder clientes."
        ),
    )
    async def ferramenta_publica_de_teste() -> str:
        """Diagnostic tool for connectivity tests."""
        return _ferramenta_publica_de_teste_logic()

    @mcp.tool(
        name="route_to_specialist",
        description=(
            "Delegate the current request to a domain specialist agent. "
            "Use when the user wants to CREATE, REGISTER, SAVE, or UPDATE data "
            "(transactions, suppliers, goals, routines), or when the task requires "
            "domain expertise beyond SQL queries. "
            "VALID slugs: context-gatherer (data entry, suppliers, goals, routines), "
            "financeiro (financial analysis), compras (procurement), crm (client comms), "
            "estrategia (strategy), agenda (calendar), documentos (documents), "
            "fiscal-agent (taxes). "
            "Args: agent_slug (one of the valid slugs above), reason (one sentence why)."
        ),
    )
    async def route_to_specialist(agent_slug: str, reason: str) -> str:
        """Signal service.py to hand off to a specialist graph."""
        return _route_to_specialist_logic(agent_slug, reason)

    logger.info("[Common Module] Ferramentas registradas.")
    return ["ferramenta_publica_de_teste", "route_to_specialist"]
