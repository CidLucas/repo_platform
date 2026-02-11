"""
MCP Resources - Expõe dados read-only via protocolo MCP.

Resources são diferentes de Tools:
- Tools: executam ações (RAG search, SQL query)
- Resources: expõem dados estáticos/semi-estáticos (knowledge base, config, prompts)

Phase 3: Refactored to use vizu_tool_registry for dynamic tool filtering.
Phase 4: Prompts now use Langfuse-first strategy via PromptLoader.

Referência: https://fastmcp.mintlify.app/servers/resources
"""

import logging
from uuid import UUID

from fastmcp import FastMCP
from fastmcp.exceptions import ResourceError
from fastmcp.server.dependencies import get_access_token
from sqlmodel import select

from tool_pool_api.server.dependencies import (
    get_context_service,
    load_context_from_token,
)
from tool_pool_api.server.tool_helpers import (
    get_enabled_tools_for_context,
    get_tier_for_context,
)
from vizu_db_connector.database import SessionLocal
from vizu_llm_service.client import get_embedding_model
from vizu_models import KnowledgeBaseConfig, PromptTemplate
from vizu_models.vizu_client_context import VizuClientContext
from vizu_prompt_management import PromptLoader
from vizu_qdrant_client import get_qdrant_client

# Phase 3: Use vizu_tool_registry for dynamic tool filtering
from vizu_tool_registry import ToolRegistry

logger = logging.getLogger(__name__)


# =============================================================================
# HELPER: Resolver contexto do cliente
# =============================================================================


async def _resolve_client_context(
    cliente_id: str | None = None,
) -> VizuClientContext:
    """
    Resolve o contexto do cliente via ID explícito ou AccessToken do MCP.

    Args:
        cliente_id: ID do cliente (opcional, usado pelo atendente_core)

    Returns:
        VizuClientContext do cliente

    Raises:
        ResourceError: Se não conseguir resolver o contexto
    """
    ctx_service = get_context_service()

    if cliente_id:
        try:
            uuid_obj = UUID(cliente_id)
            context = await ctx_service.get_client_context_by_id(uuid_obj)
            if not context:
                raise ResourceError(f"Cliente não encontrado: {cliente_id}")
            return context
        except ValueError:
            raise ResourceError(f"ID de cliente inválido: {cliente_id}")
    else:
        # Fallback to AccessToken from MCP request
        access_token = get_access_token()
        return await load_context_from_token(ctx_service, access_token)


# =============================================================================
# RESOURCES: Knowledge Base
# =============================================================================


async def _get_knowledge_summary(cliente_id: str | None = None) -> str:
    """
    Retorna um resumo da base de conhecimento do cliente.

    Inclui:
    - Nome da coleção RAG
    - Número de documentos
    - Metadados disponíveis
    """
    context = await _resolve_client_context(cliente_id)

    enabled_tools = get_enabled_tools_for_context(context)
    if "executar_rag_cliente" not in enabled_tools:
        return f"# Base de Conhecimento - {context.nome_empresa}\n\n⚠️ RAG não habilitado para este cliente."

    # Get collection name from available_tools config or use client_id
    collection_name = (
        context.available_tools.get("rag_collection") if context.available_tools else None
    ) or str(context.id)

    try:
        qdrant = get_qdrant_client()

        # Verifica se a coleção existe
        if not qdrant.collection_exists(collection_name):
            return (
                f"# Base de Conhecimento - {context.nome_empresa}\n\n"
                f"📁 Coleção: `{collection_name}`\n"
                f"📊 Status: Coleção não encontrada\n\n"
                "A base de conhecimento ainda não foi populada."
            )

        # Obtém info da coleção
        collection_info = qdrant.client.get_collection(collection_name)
        points_count = collection_info.points_count
        vectors_config = collection_info.config.params.vectors

        # Extrai dimensão do vetor
        if hasattr(vectors_config, "size"):
            vector_size = vectors_config.size
        elif isinstance(vectors_config, dict):
            # Para configuração named vectors
            first_config = next(iter(vectors_config.values()), None)
            vector_size = first_config.size if first_config else "N/A"
        else:
            vector_size = "N/A"

        return (
            f"# Base de Conhecimento - {context.nome_empresa}\n\n"
            f"📁 **Coleção:** `{collection_name}`\n"
            f"📊 **Documentos:** {points_count}\n"
            f"🔢 **Dimensão do vetor:** {vector_size}\n"
            f"✅ **Status:** Ativo\n\n"
            "Use a ferramenta `executar_rag_cliente` para buscar informações."
        )

    except Exception as e:
        logger.error(f"Erro ao obter info da coleção {collection_name}: {e}")
        return (
            f"# Base de Conhecimento - {context.nome_empresa}\n\n"
            f"❌ Erro ao acessar a coleção: {e}"
        )


async def _search_knowledge(
    query: str, cliente_id: str | None = None, limit: int = 5
) -> str:
    """
    Busca documentos na base de conhecimento (read-only, sem LLM).

    Diferente do tool executar_rag_cliente, este resource apenas
    retorna os documentos brutos, sem passar pelo LLM.

    Args:
        query: Texto de busca
        cliente_id: ID do cliente
        limit: Número máximo de resultados

    Returns:
        Documentos encontrados em formato Markdown
    """
    context = await _resolve_client_context(cliente_id)

    enabled = get_enabled_tools_for_context(context)
    if "executar_rag_cliente" not in enabled:
        raise ResourceError("RAG não habilitado para este cliente.")

    # Get collection name from available_tools config or use client_id
    collection_name = (
        context.available_tools.get("rag_collection") if context.available_tools else None
    ) or str(context.id)

    try:
        qdrant = get_qdrant_client()
        embedding_model = get_embedding_model()

        if not qdrant.collection_exists(collection_name):
            return "Nenhum documento encontrado (coleção não existe)."

        # Obtém retriever
        retriever = qdrant.get_langchain_retriever(
            collection_name=collection_name, embeddings=embedding_model, search_k=limit
        )

        # Busca documentos
        docs = retriever.invoke(query)

        if not docs:
            return f"Nenhum documento encontrado para: '{query}'"

        # Formata resultado
        result = f"# Resultados para: '{query}'\n\n"
        result += f"Encontrados {len(docs)} documento(s):\n\n"

        for i, doc in enumerate(docs, 1):
            content = doc.page_content[:500]
            if len(doc.page_content) > 500:
                content += "..."

            metadata = doc.metadata or {}
            source = metadata.get("source", "N/A")

            result += f"## Documento {i}\n"
            result += f"**Fonte:** {source}\n\n"
            result += f"```\n{content}\n```\n\n"

        return result

    except Exception as e:
        logger.error(f"Erro na busca knowledge: {e}")
        raise ResourceError(f"Erro ao buscar documentos: {e}")


# =============================================================================
# RESOURCES: Client Configuration
# =============================================================================


async def _get_client_config(cliente_id: str | None = None) -> str:
    """
    Retorna a configuração do cliente em formato legível.

    Phase 3: Uses vizu_tool_registry for dynamic tool information.

    Inclui:
    - Nome da empresa
    - Horários de funcionamento
    - Ferramentas habilitadas (via ToolRegistry)
    - Tier do cliente
    - Prompt base (se configurado)
    """
    context = await _resolve_client_context(cliente_id)

    # Get enabled tools and tier
    enabled_tools = get_enabled_tools_for_context(context)
    tier = get_tier_for_context(context)

    # Get available tools from registry (validates against tier)
    available_tools = ToolRegistry.get_available_tools(
        enabled_tools=enabled_tools,
        tier=tier,
        include_google=True,
    )

    # Get business hours from team_structure if available
    horarios_str = "Não configurado"
    if context.team_structure and context.team_structure.get("business_hours"):
        horarios_str = context.team_structure["business_hours"]

    # Lista de ferramentas (from registry)
    tools_status = []
    for tool in available_tools:
        confirmation = " (requer confirmação)" if tool.requires_confirmation else ""
        tools_status.append(f"✅ {tool.name} - {tool.description}{confirmation}")

    # Show disabled tools
    all_tool_names = set(ToolRegistry.get_all_tools().keys())
    enabled_names = set(t.name for t in available_tools)
    disabled_tools = all_tool_names - enabled_names

    # Monta resposta
    result = f"# Configuração - {context.nome_empresa}\n\n"
    result += "## Identificação\n"
    result += f"- **ID:** `{context.id}`\n"
    result += f"- **Nome:** {context.nome_empresa}\n"
    result += f"- **Tier:** {tier}\n\n"

    result += "## Horário de Funcionamento\n"
    result += f"{horarios_str}\n\n"

    result += f"## Ferramentas Habilitadas ({len(available_tools)})\n"
    if tools_status:
        for tool in tools_status:
            result += f"{tool}\n"
    else:
        result += "Nenhuma ferramenta habilitada.\n"
    result += "\n"

    # Show some disabled tools (if any)
    if disabled_tools and len(disabled_tools) <= 10:
        result += "## Ferramentas Não Habilitadas\n"
        for name in sorted(list(disabled_tools)[:5]):
            tool_meta = ToolRegistry.get_tool(name)
            if tool_meta:
                result += f"❌ {name} (requer tier {tool_meta.tier_required.value})\n"
        result += "\n"

    # Show RAG collection from available_tools config
    rag_collection = context.available_tools.get("rag_collection") if context.available_tools else None
    if rag_collection:
        result += "## Base de Conhecimento\n"
        result += f"- **Coleção RAG:** `{rag_collection}`\n\n"

    return result


async def _get_client_prompt(cliente_id: str | None = None) -> str:
    """
    Retorna o prompt base configurado para o cliente.

    Note: Prompts are now managed via Langfuse. This resource shows
    the fallback prompt from available_tools.default_system_prompt if set.
    """
    context = await _resolve_client_context(cliente_id)

    default_prompt = (
        context.available_tools.get("default_system_prompt")
        if context.available_tools else None
    )

    if not default_prompt:
        return (
            f"# Prompt - {context.nome_empresa}\n\n"
            "⚠️ Nenhum prompt personalizado configurado.\n\n"
            "O agente usará o prompt do Langfuse (atendente/default)."
        )

    return f"# Prompt - {context.nome_empresa}\n\n" f"```\n{default_prompt}\n```"


# =============================================================================
# RESOURCES: Prompt Templates (Langfuse-first, DB fallback)
# =============================================================================

# Global PromptLoader instance
_prompt_loader: PromptLoader | None = None


def _get_prompt_loader() -> PromptLoader:
    """Get or create the global PromptLoader instance."""
    global _prompt_loader
    if _prompt_loader is None:
        _prompt_loader = PromptLoader()
    return _prompt_loader


async def _load_prompt(
    name: str, cliente_id: str | None = None, langfuse_label: str = "production"
) -> dict:
    """
    Load a prompt using the Langfuse-first strategy.

    Priority:
    1. Langfuse (label="production" by default)
    2. DB client-specific override (if cliente_id provided)
    3. DB global prompt
    4. Builtin template

    Args:
        name: Prompt name (e.g., 'atendente/system')
        cliente_id: Optional client ID for client-specific overrides
        langfuse_label: Langfuse label to use (default: "production")

    Returns:
        Dict with prompt info: {name, content, source, version, metadata}
    """
    loader = _get_prompt_loader()
    uuid_obj = UUID(cliente_id) if cliente_id else None

    loaded = await loader.load(
        name=name,
        cliente_id=uuid_obj,
        langfuse_label=langfuse_label,
    )

    return {
        "name": loaded.name,
        "content": loaded.content,
        "source": loaded.source,
        "version": loaded.version,
        "metadata": loaded.metadata,
        "trace_metadata": loaded.get_trace_metadata() if hasattr(loaded, "get_trace_metadata") else None,
    }


def _get_prompt_template(
    name: str, version: int | None = None, cliente_id: str | None = None
) -> PromptTemplate | None:
    """
    Busca um prompt template do banco de dados (legacy, for version-specific lookups).

    NOTE: For new code, prefer using _load_prompt() which uses Langfuse-first strategy.
    This function is kept for backward compatibility and version-specific lookups.

    Args:
        name: Nome do prompt (ex: 'atendente/system')
        version: Versão específica (None = mais recente ativa)
        cliente_id: ID do cliente para buscar override

    Returns:
        PromptTemplate ou None se não encontrado
    """
    with SessionLocal() as db:
        # Se cliente_id fornecido, tenta buscar prompt específico primeiro
        if cliente_id:
            try:
                uuid_obj = UUID(cliente_id)

                # Query para prompt específico do cliente
                query = select(PromptTemplate).where(
                    PromptTemplate.name == name,
                    PromptTemplate.client_id == uuid_obj,
                    PromptTemplate.is_active == True,
                )

                if version:
                    query = query.where(PromptTemplate.version == version)
                else:
                    query = query.order_by(PromptTemplate.version.desc())

                result = db.exec(query).first()
                if result:
                    return result

            except ValueError:
                logger.warning(f"cliente_id inválido: {cliente_id}")

        # Fallback: busca prompt global
        query = select(PromptTemplate).where(
            PromptTemplate.name == name,
            PromptTemplate.client_id == None,
            PromptTemplate.is_active == True,
        )

        if version:
            query = query.where(PromptTemplate.version == version)
        else:
            query = query.order_by(PromptTemplate.version.desc())

        return db.exec(query).first()


def _list_prompt_templates(cliente_id: str | None = None) -> list[PromptTemplate]:
    """
    Lista todos os prompts disponíveis (globais + específicos do cliente).
    """
    with SessionLocal() as db:
        # Busca prompts globais
        query = select(PromptTemplate).where(PromptTemplate.is_active == True)

        if cliente_id:
            try:
                uuid_obj = UUID(cliente_id)
                # Inclui prompts do cliente também
                query = query.where(
                    (PromptTemplate.client_id == None)
                    | (PromptTemplate.client_id == uuid_obj)
                )
            except ValueError:
                query = query.where(PromptTemplate.client_id == None)
        else:
            query = query.where(PromptTemplate.client_id == None)

        query = query.order_by(PromptTemplate.name, PromptTemplate.version.desc())

        return list(db.exec(query).all())


# =============================================================================
# RESOURCES: Knowledge Base Configs (from Database)
# =============================================================================


def _get_knowledge_base_configs(cliente_id: str) -> list[KnowledgeBaseConfig]:
    """
    Lista as configurações de knowledge bases de um cliente.
    """
    with SessionLocal() as db:
        try:
            uuid_obj = UUID(cliente_id)
            query = select(KnowledgeBaseConfig).where(
                KnowledgeBaseConfig.client_id == uuid_obj,
                KnowledgeBaseConfig.is_active == True,
            )
            return list(db.exec(query).all())
        except ValueError:
            logger.warning(f"cliente_id inválido: {cliente_id}")
            return []


# =============================================================================
# REGISTRO DOS RESOURCES
# =============================================================================


def register_resources(mcp: FastMCP) -> None:
    """
    Registra todos os resources no servidor MCP.

    Resources expõem dados read-only que podem ser consultados
    pelo LLM ou pelo cliente MCP.
    """

    # --- Knowledge Base Resources ---

    @mcp.resource("knowledge://summary")
    async def knowledge_summary() -> str:
        """Resumo da base de conhecimento do cliente autenticado."""
        return await _get_knowledge_summary()

    @mcp.resource("knowledge://{cliente_id}/summary")
    async def knowledge_summary_by_id(cliente_id: str) -> str:
        """Resumo da base de conhecimento de um cliente específico."""
        return await _get_knowledge_summary(cliente_id)

    @mcp.resource("knowledge://{cliente_id}/search/{query}")
    async def knowledge_search(cliente_id: str, query: str) -> str:
        """
        Busca documentos na base de conhecimento (sem LLM).
        Retorna documentos brutos encontrados.
        """
        return await _search_knowledge(query, cliente_id)

    @mcp.resource("knowledge://{cliente_id}/configs")
    def knowledge_configs(cliente_id: str) -> str:
        """
        Lista as configurações de knowledge bases do cliente (do banco de dados).
        """
        configs = _get_knowledge_base_configs(cliente_id)

        if not configs:
            return f"# Knowledge Bases\n\nNenhuma base de conhecimento configurada para o cliente `{cliente_id}`."

        result = f"# Knowledge Bases ({len(configs)})\n\n"
        for cfg in configs:
            result += f"## {cfg.name}\n"
            result += f"- **ID:** `{cfg.id}`\n"
            result += f"- **Descrição:** {cfg.description or 'N/A'}\n"
            result += f"- **Collection:** `{cfg.collection_name}`\n"
            result += f"- **Modelo Embedding:** {cfg.embedding_model}\n"
            result += f"- **Chunks:** {cfg.chunk_size} (overlap: {cfg.chunk_overlap})\n"
            result += f"- **Documentos:** {cfg.document_count}\n"
            if cfg.last_sync_at:
                result += f"- **Último sync:** {cfg.last_sync_at.isoformat()}\n"
            result += "\n"

        return result

    # --- Client Configuration Resources ---

    @mcp.resource("config://client")
    async def client_config() -> str:
        """Configuração do cliente autenticado."""
        return await _get_client_config()

    @mcp.resource("config://{cliente_id}/settings")
    async def client_config_by_id(cliente_id: str) -> str:
        """Configuração de um cliente específico."""
        return await _get_client_config(cliente_id)

    @mcp.resource("config://{cliente_id}/prompt")
    async def client_prompt(cliente_id: str) -> str:
        """Prompt personalizado do cliente (legado, do campo prompt_base)."""
        return await _get_client_prompt(cliente_id)

    # --- Tools Registry Resources (Phase 3) ---

    @mcp.resource("tools://registry")
    def tools_registry() -> str:
        """
        List all registered tools in the system.

        Returns tool metadata including:
        - Name and description
        - Category
        - Tier required
        - Whether confirmation is required
        """
        all_tools = ToolRegistry.get_all_tools()

        result = f"# Tool Registry ({len(all_tools)} tools)\n\n"

        # Group by category
        by_category = {}
        for tool in all_tools.values():
            cat = tool.category.value
            if cat not in by_category:
                by_category[cat] = []
            by_category[cat].append(tool)

        for category, tools in sorted(by_category.items()):
            result += f"## {category}\n\n"
            for tool in tools:
                confirmation = " ⚠️" if tool.requires_confirmation else ""
                result += f"- **{tool.name}**{confirmation}\n"
                result += f"  - {tool.description}\n"
                result += f"  - Tier: {tool.tier_required.value}\n"
            result += "\n"

        return result

    @mcp.resource("tools://{cliente_id}/available")
    async def tools_available_for_client(cliente_id: str) -> str:
        """
        List tools available for a specific client.

        Takes into account the client's tier and enabled_tools configuration.
        """
        context = await _resolve_client_context(cliente_id)

        enabled_tools = get_enabled_tools_for_context(context)
        tier = get_tier_for_context(context)

        available = ToolRegistry.get_available_tools(
            enabled_tools=enabled_tools,
            tier=tier,
            include_google=True,
        )

        result = f"# Available Tools - {context.nome_empresa}\n\n"
        result += f"**Tier:** {tier}\n"
        result += f"**Enabled tools:** {', '.join(enabled_tools) or 'None'}\n\n"

        if not available:
            result += "❌ No tools available for this client.\n"
            return result

        result += f"## Tools ({len(available)})\n\n"
        for tool in available:
            confirmation = " (requires confirmation)" if tool.requires_confirmation else ""
            result += f"### {tool.name}{confirmation}\n"
            result += f"{tool.description}\n\n"
            result += f"- **Category:** {tool.category.value}\n"
            result += f"- **Tags:** {', '.join(tool.tags)}\n\n"

        return result

    @mcp.resource("tools://tier/{tier}")
    def tools_for_tier(tier: str) -> str:
        """
        List all tools accessible at a given tier.

        Args:
            tier: BASIC, SME, or ENTERPRISE
        """
        tier_upper = tier.upper()
        if tier_upper not in ["BASIC", "SME", "ENTERPRISE", "FREE"]:
            return f"# Error\n\nInvalid tier: `{tier}`. Use BASIC, SME, or ENTERPRISE."

        tools = ToolRegistry.get_tools_for_tier(tier_upper)

        result = f"# Tools for {tier_upper} Tier ({len(tools)})\n\n"

        if not tools:
            result += "No tools available at this tier.\n"
            return result

        for tool in tools:
            result += f"- **{tool.name}** - {tool.description}\n"

        return result

    # --- Prompt Template Resources (Langfuse-first, DB fallback) ---

    @mcp.resource("prompts://list")
    def prompt_list() -> str:
        """
        Lista todos os prompts globais disponíveis (do banco de dados).

        NOTE: Prompts principais são gerenciados via Langfuse UI.
        Esta lista mostra apenas prompts armazenados no DB para referência.
        """
        templates = _list_prompt_templates()

        if not templates:
            return "# Prompt Templates (DB)\n\nNenhum prompt template encontrado no banco.\n\n💡 **Dica:** Prompts principais são gerenciados via Langfuse UI."

        result = f"# Prompt Templates - DB ({len(templates)})\n\n"
        result += "💡 **Nota:** Prompts principais são gerenciados via Langfuse UI.\n\n"

        # Agrupa por nome
        current_name = None
        for tpl in templates:
            if tpl.name != current_name:
                current_name = tpl.name
                result += f"## `{tpl.name}`\n"

            result += f"- **v{tpl.version}:** {tpl.description or 'Sem descrição'}"
            if tpl.tags:
                result += f" | Tags: {', '.join(tpl.tags)}"
            result += "\n"

        return result

    @mcp.resource("prompts://{cliente_id}/list")
    def prompt_list_for_client(cliente_id: str) -> str:
        """Lista prompts disponíveis para um cliente (globais + específicos)."""
        templates = _list_prompt_templates(cliente_id)

        if not templates:
            return f"# Prompt Templates\n\nNenhum prompt template encontrado para cliente `{cliente_id}`."

        result = f"# Prompt Templates para Cliente ({len(templates)})\n\n"

        current_name = None
        for tpl in templates:
            if tpl.name != current_name:
                current_name = tpl.name
                result += f"## `{tpl.name}`\n"

            scope = "🌐 Global" if not tpl.client_id else "🏢 Cliente"
            result += f"- **v{tpl.version}** ({scope}): {tpl.description or 'Sem descrição'}\n"

        return result

    @mcp.resource("prompts://{name}")
    async def prompt_get(name: str) -> str:
        """
        Obtém um prompt pelo nome usando estratégia Langfuse-first.

        O nome deve usar underscores em vez de barras (ex: atendente_system).

        Prioridade de carregamento:
        1. Langfuse (label="production")
        2. DB global
        3. Template builtin
        """
        # Converte underscores para barras (URI-safe)
        prompt_name = name.replace("_", "/")

        try:
            prompt_info = await _load_prompt(prompt_name)

            result = f"# {prompt_info['name']}\n\n"
            result += f"**Fonte:** {prompt_info['source']}\n"

            if prompt_info.get('version'):
                result += f"**Versão:** {prompt_info['version']}\n"

            if prompt_info.get('trace_metadata'):
                trace = prompt_info['trace_metadata']
                if trace.get('langfuse_prompt_version'):
                    result += f"**Langfuse Version:** {trace['langfuse_prompt_version']}\n"

            result += "\n## Conteúdo\n\n"
            result += f"```\n{prompt_info['content']}\n```\n"

            return result

        except Exception as e:
            logger.error(f"Erro ao carregar prompt {prompt_name}: {e}")
            return f"# Prompt não encontrado\n\n`{prompt_name}` não existe ou ocorreu um erro: {e}"

    @mcp.resource("prompts://{name}/v{version}")
    def prompt_get_version(name: str, version: str) -> str:
        """
        Obtém uma versão específica de um prompt template (apenas do DB).

        NOTE: Para prompts versionados do Langfuse, use a UI do Langfuse.
        """
        prompt_name = name.replace("_", "/")

        try:
            version_int = int(version)
        except ValueError:
            return f"# Erro\n\nVersão inválida: `{version}`"

        template = _get_prompt_template(prompt_name, version=version_int)

        if not template:
            return (
                f"# Prompt não encontrado\n\n`{prompt_name}` v{version_int} não existe."
            )

        result = f"# {template.name} (v{template.version})\n\n"
        result += f"```\n{template.content}\n```\n"

        return result

    logger.info(
        "MCP Resources registrados: "
        "knowledge://*, config://*, prompts://*, tools://*"
    )
