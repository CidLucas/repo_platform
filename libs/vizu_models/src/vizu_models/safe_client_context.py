# vizu_models/safe_client_context.py
"""
SafeClientContext - Contexto seguro para exposição à LLM.

Este modelo contém APENAS os dados que são seguros para serem
expostos à LLM. Nenhuma informação sensível (API keys, IDs internos,
credenciais) deve estar aqui.

IMPORTANTE: Qualquer dado neste modelo pode potencialmente ser
incluído em prompts ou respostas da LLM.

PHASE 1: Dynamic Tool Allocation
- enabled_tools: Lista de ferramentas habilitadas (substitui 3 booleans)
- tier: Tier do cliente determina acesso baseline
"""

import uuid

from pydantic import BaseModel, ConfigDict


class SafeClientContext(BaseModel):
    """
    Contexto do cliente seguro para uso com LLM.

    NÃO INCLUIR:
    - api_key
    - credenciais de serviços externos
    - IDs internos (UUIDs)
    - qualquer dado que possa ser usado para impersonação
    """

    model_config = ConfigDict(
        frozen=True
    )  # Imutável para evitar modificações acidentais

    # Dados públicos seguros
    nome_empresa: str

    # PHASE 1: Dynamic Tool Allocation
    tier: str = "BASIC"  # Tier do cliente (BASIC, SME, ENTERPRISE)
    enabled_tools: list[str] = []  # Lista de ferramentas habilitadas

    # Configurações de comportamento (não sensíveis)
    prompt_base: str | None = None
    horario_funcionamento: dict | None = None
    collection_rag: str | None = None  # RAG collection name if tool is enabled


class InternalClientContext(BaseModel):
    """
    Contexto interno do cliente com dados sensíveis.

    Este modelo é usado APENAS para operações internas do servidor
    (autenticação, injeção de cliente_id em tools, etc.)

    NUNCA deve ser exposto à LLM ou incluído em prompts.

    Authentication: JWT-only (Supabase) - api_key is deprecated.
    """

    # Identificadores internos
    id: uuid.UUID

    # Contexto seguro (pode ser extraído para a LLM)
    safe_context: SafeClientContext

    @classmethod
    def from_vizu_client_context(cls, ctx) -> "InternalClientContext":
        """
        Cria um InternalClientContext a partir de um VizuClientContext.
        Separa claramente os dados sensíveis dos seguros.

        PHASE 1: Uses enabled_tools list as the single source of truth.
        No more boolean flags for individual tools - all tools are managed
        through the enabled_tools list.

        Authentication: JWT-only - api_key no longer required.
        """
        # Get enabled tools - this is the authoritative field
        enabled_tools = []
        if hasattr(ctx, 'get_enabled_tools_list'):
            enabled_tools = ctx.get_enabled_tools_list()
        elif hasattr(ctx, 'enabled_tools') and ctx.enabled_tools:
            enabled_tools = ctx.enabled_tools if isinstance(ctx.enabled_tools, list) else []

        # Get tier value
        tier_value = "BASIC"
        if hasattr(ctx, 'tier'):
            tier_value = ctx.tier.value if hasattr(ctx.tier, 'value') else str(ctx.tier)

        safe = SafeClientContext(
            nome_empresa=ctx.nome_empresa,
            tier=tier_value,
            enabled_tools=enabled_tools,
            prompt_base=getattr(ctx, 'prompt_base', None),
            horario_funcionamento=getattr(ctx, 'horario_funcionamento', None),
            collection_rag=getattr(ctx, 'collection_rag', None),
        )
        return cls(
            id=ctx.id,
            safe_context=safe,
        )

    def get_safe_context(self) -> SafeClientContext:
        """Retorna apenas o contexto seguro para uso com LLM."""
        return self.safe_context

    def get_client_id_for_tools(self) -> str:
        """Retorna o ID do cliente para injeção em tools (uso interno)."""
        return str(self.id)
