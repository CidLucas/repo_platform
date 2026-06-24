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

from tool_pool_api.server.tool_modules import register_module

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Catálogo fechado de slugs válidos no AgentTypeRegistry.
# Qualquer slug fora desta lista é normalizado via SLUG_ALIASES ou rejeitado.
# ---------------------------------------------------------------------------
_VALID_SLUGS: set[str] = {
    # Slugs canônicos v3 — espelha AgentTypeRegistry em blu_agent_framework/registry.py
    "context-gatherer",
    "crm",
    "strategy",      # v3: merged de estrategia + synthesis
    "compras",
    "financeiro",
    "data-analyst",
    "platform",
    "agenda",        # slug canônico — prompt_name="agents/agenda" no Langfuse
    "doc-writer",
    "fiscal-agent",
    # nota: "documentos"/"estrategia"/"synthesis" são slugs v2 — ver aliases abaixo
    # nota: "supplier-agent" removido — domínio fornecedor roteado via "compras"
}

# Aliases: slugs v2 ou variações ortográficas → slug canônico v3
# REGRA: nunca mapear para um slug que não esteja em _VALID_SLUGS
# IMPORTANTE: NÃO adicionar aliases de domínio/keyword aqui.
#   O LLM escolhe o agente lendo o catálogo {{ available_agents }} no prompt do frontdesk,
#   que é gerado dinamicamente a partir de AgentTypeRegistry (description + routing_hint).
#   Aliases de keyword criam um segundo canal de decisão inconsistente — evitar.
_SLUG_ALIASES: dict[str, str] = {
    # v2 → v3 (slugs renomeados na migração de arquitetura)
    "estrategia":        "strategy",
    "estrategia_agent":  "strategy",
    "strategy_agent":    "strategy",
    "synthesis":         "strategy",
    # scheduler-agent → agenda (Langfuse prompt_name preservado, slug canônico mudou)
    "scheduler":         "agenda",
    "scheduler-agent":   "agenda",
    # variações ortográficas do slug canônico
    "doc_writer":        "doc-writer",
    "fiscal_agent":      "fiscal-agent",
    "data_entry":        "data-entry",
    "data_entry_nl":     "data-entry",
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
            "Choose the agent_slug based on the agent descriptions provided in your system prompt "
            "under 'available_agents' — do NOT guess slugs from keywords. "
            "Use the exact slug as listed there. "
            "Args: agent_slug (exact slug from available_agents), reason (one sentence why)."
        ),
    )
    async def route_to_specialist(agent_slug: str, reason: str) -> str:
        """Signal service.py to hand off to a specialist graph."""
        return _route_to_specialist_logic(agent_slug, reason)

    logger.info("[Common Module] Ferramentas registradas.")
    return ["ferramenta_publica_de_teste", "route_to_specialist"]
