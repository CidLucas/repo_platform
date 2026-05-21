# tool_pool_api/server/tool_modules/notion_module.py
"""
Módulo Notion - Ferramentas de Documentação e Base de Conhecimento

Integração com a API do Notion para listagem de páginas,
leitura de conteúdo, busca e criação de páginas.
"""

import logging

import httpx
from fastmcp import Context, FastMCP
from fastmcp.exceptions import ToolError

from blu_auth.mcp.auth_middleware import mcp_inject_client_id
from tool_pool_api.server.dependencies import get_context_service
from tool_pool_api.server.tool_modules import register_module

logger = logging.getLogger(__name__)

NOTION_API_URL = "https://api.notion.com/v1"
NOTION_VERSION = "2026-03-11"


# =============================================================================
# HELPERS
# =============================================================================


async def _get_notion_token(client_id: str | None) -> str:
    """Fetch Notion token from integration_tokens for the current client."""
    if not client_id:
        raise ToolError("Missing client_id")

    ctx_service = get_context_service()
    token_wrapper = await ctx_service.get_integration_tokens(
        client_id,
        "notion",
        auto_refresh=False,
    )

    if not token_wrapper or not token_wrapper.is_valid():
        raise ToolError(
            "Notion não conectado. Vá em Admin > Integrações para conectar."
        )

    token = token_wrapper.get_decrypted_tokens().get("access_token")
    if not token:
        raise ToolError(
            "Notion não conectado. Vá em Admin > Integrações para conectar."
        )

    return token


def _notion_headers(token: str) -> dict:
    return {
        "Authorization": f"Bearer {token}",
        "Notion-Version": NOTION_VERSION,
        "Content-Type": "application/json",
    }


def _extract_notion_title(result: dict) -> str:
    """Extract title from a Notion search result (robust multi-strategy)."""
    props = result.get("properties", {})
    # Strategy 1 & 2: try known title keys
    for key in ("title", "Name"):
        prop = props.get(key, {})
        items = prop.get("title", [])
        if items:
            return items[0].get("plain_text", "Sem título")
    # Strategy 3: iterate all properties looking for a 'title' list
    for prop in props.values():
        if isinstance(prop, dict):
            items = prop.get("title", [])
            if isinstance(items, list) and items:
                return items[0].get("plain_text", "Sem título")
    # Strategy 4: fallback
    return "Sem título"


def _summarize_notion_properties(properties: dict) -> dict:
    """Create a lightweight summary for simple Notion property types."""
    summary: dict[str, str] = {}

    for prop_name, prop in properties.items():
        if not isinstance(prop, dict):
            continue

        prop_type = prop.get("type")
        value: str | None = None

        if prop_type in ("rich_text", "text"):
            rich_text = prop.get("rich_text", [])
            if isinstance(rich_text, list) and rich_text:
                value = "".join(item.get("plain_text", "") for item in rich_text).strip()
        elif prop_type == "title":
            title_items = prop.get("title", [])
            if isinstance(title_items, list) and title_items:
                value = "".join(item.get("plain_text", "") for item in title_items).strip()
        elif prop_type == "number":
            number = prop.get("number")
            if number is not None:
                value = str(number)
        elif prop_type == "select":
            select_data = prop.get("select")
            if isinstance(select_data, dict):
                value = select_data.get("name")
        elif prop_type == "date":
            date_data = prop.get("date")
            if isinstance(date_data, dict):
                start = date_data.get("start")
                end = date_data.get("end")
                if start and end:
                    value = f"{start} → {end}"
                elif start:
                    value = start

        if value:
            summary[prop_name] = str(value)

    return summary


# =============================================================================
# LÓGICA DE NEGÓCIO (Testável)
# =============================================================================


async def _notion_list_pages_logic(
    client_id: str | None,
    query: str = "",
    limit: int = 20,
) -> dict:
    """
    Lista páginas do Notion do cliente.

    Args:
        query: Filtro de busca (opcional)
        limit: Máximo de páginas a retornar (padrão 20)

    Returns:
        Dict com {total, pages: [{id, title, url, last_edited, object_type}]}
    """
    try:
        token = await _get_notion_token(client_id)
        body = {
            "query": query,
            "page_size": limit,
            "filter": {"property": "object", "value": "page"},
        }
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                f"{NOTION_API_URL}/search",
                headers=_notion_headers(token),
                json=body,
            )
            response.raise_for_status()
            data = response.json()

        results = data.get("results", [])
        pages = [
            {
                "id": r["id"],
                "title": _extract_notion_title(r),
                "url": r.get("url", ""),
                "last_edited": r.get("last_edited_time", ""),
                "object_type": r.get("object", "page"),
            }
            for r in results
        ]
        logger.info(f"[Notion] Listed {len(pages)} pages for client_id={client_id}")
        return {"total": len(pages), "pages": pages}
    except ToolError:
        raise
    except Exception as e:
        logger.exception(f"[Notion] Error listing pages: {e}")
        raise ToolError(f"Erro ao listar páginas do Notion: {e}")


async def _notion_read_page_logic(
    client_id: str | None,
    page_id: str,
) -> dict:
    """
    Lê o conteúdo de uma página do Notion.

    Args:
        page_id: ID da página

    Returns:
        Dict com {page_id, title, url, content, block_count}
    """
    if not page_id or not page_id.strip():
        raise ToolError("page_id é obrigatório.")

    try:
        token = await _get_notion_token(client_id)
        async with httpx.AsyncClient(timeout=30) as client:
            # Get page metadata
            page_resp = await client.get(
                f"{NOTION_API_URL}/pages/{page_id}",
                headers=_notion_headers(token),
            )
            page_resp.raise_for_status()
            page_data = page_resp.json()

            # Get blocks
            blocks_resp = await client.get(
                f"{NOTION_API_URL}/blocks/{page_id}/children",
                headers=_notion_headers(token),
                params={"page_size": 100},
            )
            blocks_resp.raise_for_status()
            blocks_data = blocks_resp.json()

        title = _extract_notion_title(page_data)
        blocks = blocks_data.get("results", [])

        lines = []
        for block in blocks:
            btype = block.get("type", "")
            bdata = block.get(btype, {})
            rich_text = bdata.get("rich_text", [])
            text = "".join(rt.get("plain_text", "") for rt in rich_text)

            if btype in ("paragraph", "heading_1", "heading_2", "heading_3"):
                if text:
                    lines.append(text)
            elif btype == "bulleted_list_item":
                lines.append(f"• {text}")
            elif btype == "numbered_list_item":
                lines.append(f"1. {text}")
            elif btype == "to_do":
                checked = bdata.get("checked", False)
                prefix = "[x]" if checked else "[ ]"
                lines.append(f"{prefix} {text}")
            elif btype == "quote":
                lines.append(f"> {text}")
            elif btype == "code":
                lines.append(f"`{text}`")
            # others: skip

        logger.info(
            f"[Notion] Read page {page_id}: {len(blocks)} blocks for client_id={client_id}"
        )
        return {
            "page_id": page_id,
            "title": title,
            "url": page_data.get("url", ""),
            "content": "\n".join(lines),
            "block_count": len(blocks),
        }
    except ToolError:
        raise
    except Exception as e:
        logger.exception(f"[Notion] Error reading page: {e}")
        raise ToolError(f"Erro ao ler página {page_id}: {e}")


async def _notion_search_logic(
    client_id: str | None,
    query: str,
    limit: int = 10,
) -> dict:
    """
    Busca conteúdo no Notion (páginas e databases).

    Args:
        query: Texto de busca
        limit: Máximo de resultados (padrão 10)

    Returns:
        Dict com {results: [{id, title, type, url, last_edited}]}
    """
    try:
        token = await _get_notion_token(client_id)
        body = {"query": query, "page_size": limit}
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                f"{NOTION_API_URL}/search",
                headers=_notion_headers(token),
                json=body,
            )
            response.raise_for_status()
            data = response.json()

        results = [
            {
                "id": r["id"],
                "title": _extract_notion_title(r),
                "type": r.get("object", ""),
                "url": r.get("url", ""),
                "last_edited": r.get("last_edited_time", ""),
            }
            for r in data.get("results", [])
        ]
        logger.info(
            f"[Notion] Search '{query}' returned {len(results)} results for client_id={client_id}"
        )
        return {"results": results}
    except ToolError:
        raise
    except Exception as e:
        logger.exception(f"[Notion] Error searching: {e}")
        raise ToolError(f"Erro ao buscar no Notion: {e}")


async def _notion_create_page_logic(
    client_id: str | None,
    parent_id: str,
    title: str,
    content: str,
    parent_type: str = "page",
) -> dict:
    """
    Cria uma nova página no Notion.

    Args:
        parent_id: ID do parent (página ou database)
        title: Título da nova página
        content: Conteúdo em texto simples (parágrafos separados por linha em branco)
        parent_type: 'page' ou 'database' (padrão 'page')

    Returns:
        Dict com {page_id, title, url}
    """
    if not parent_id or not parent_id.strip():
        raise ToolError("parent_id é obrigatório.")
    if not title or not title.strip():
        raise ToolError("title é obrigatório.")

    try:
        token = await _get_notion_token(client_id)
        parent_key = "page_id" if parent_type == "page" else "database_id"
        paragraphs = [chunk for chunk in content.split("\n\n") if chunk.strip()]
        children = [
            {
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [
                        {
                            "type": "text",
                            "text": {"content": chunk[:2000]},
                        }
                    ]
                },
            }
            for chunk in paragraphs[:100]
        ]

        body = {
            "parent": {parent_key: parent_id},
            "properties": {
                "title": {
                    "title": [{"type": "text", "text": {"content": title}}]
                }
            },
            "children": children,
        }

        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                f"{NOTION_API_URL}/pages",
                headers=_notion_headers(token),
                json=body,
            )
            response.raise_for_status()
            result = response.json()

        logger.info(
            f"[Notion] Created page '{title}' (id={result.get('id')}) for client_id={client_id}"
        )
        return {
            "page_id": result["id"],
            "title": title,
            "url": result.get("url", ""),
        }
    except ToolError:
        raise
    except Exception as e:
        logger.exception(f"[Notion] Error creating page: {e}")
        raise ToolError(f"Erro ao criar página no Notion: {e}")


async def _notion_update_page_logic(
    client_id: str | None,
    page_id: str,
    properties: dict,
    archived: bool | None = None,
) -> dict:
    """Atualiza propriedades de uma página no Notion."""
    if not page_id or not page_id.strip():
        raise ToolError("page_id é obrigatório.")
    if not isinstance(properties, dict):
        raise ToolError("properties deve ser um objeto JSON (dict).")

    try:
        token = await _get_notion_token(client_id)
        body: dict[str, object] = {"properties": properties}
        if archived is not None:
            body["archived"] = archived

        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.patch(
                f"{NOTION_API_URL}/pages/{page_id}",
                headers=_notion_headers(token),
                json=body,
            )
            response.raise_for_status()
            result = response.json()

        return {
            "page_id": result.get("id", page_id),
            "url": result.get("url", ""),
            "last_edited_time": result.get("last_edited_time", ""),
        }
    except ToolError:
        raise
    except Exception as e:
        logger.exception(f"[Notion] Error updating page: {e}")
        raise ToolError(f"Erro ao atualizar página {page_id}: {e}")


async def _notion_append_blocks_logic(
    client_id: str | None,
    page_id: str,
    blocks: list,
) -> dict:
    """Adiciona blocos ao final de uma página/bloco no Notion."""
    if not page_id or not page_id.strip():
        raise ToolError("page_id é obrigatório.")
    if not isinstance(blocks, list):
        raise ToolError("blocks deve ser uma lista de blocos Notion.")

    try:
        token = await _get_notion_token(client_id)
        body = {"children": blocks}

        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.patch(
                f"{NOTION_API_URL}/blocks/{page_id}/children",
                headers=_notion_headers(token),
                json=body,
            )
            response.raise_for_status()
            result = response.json()

        return {
            "added_count": len(result.get("results", [])),
            "page_id": page_id,
        }
    except ToolError:
        raise
    except Exception as e:
        logger.exception(f"[Notion] Error appending blocks: {e}")
        raise ToolError(f"Erro ao adicionar blocos na página {page_id}: {e}")


async def _notion_delete_block_logic(
    client_id: str | None,
    block_id: str,
) -> dict:
    """Arquiva/deleta um bloco no Notion."""
    if not block_id or not block_id.strip():
        raise ToolError("block_id é obrigatório.")

    try:
        token = await _get_notion_token(client_id)

        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.delete(
                f"{NOTION_API_URL}/blocks/{block_id}",
                headers=_notion_headers(token),
            )
            response.raise_for_status()

        return {"deleted": True, "block_id": block_id}
    except ToolError:
        raise
    except Exception as e:
        logger.exception(f"[Notion] Error deleting block: {e}")
        raise ToolError(f"Erro ao deletar bloco {block_id}: {e}")


async def _notion_query_database_logic(
    client_id: str | None,
    database_id: str,
    filter_dict: dict | None = None,
    sorts: list | None = None,
    page_size: int = 20,
) -> dict:
    """Consulta linhas de uma database no Notion."""
    if not database_id or not database_id.strip():
        raise ToolError("database_id é obrigatório.")

    try:
        token = await _get_notion_token(client_id)
        body: dict = {"page_size": page_size}
        if filter_dict is not None:
            body["filter"] = filter_dict
        if sorts is not None:
            body["sorts"] = sorts

        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                f"{NOTION_API_URL}/databases/{database_id}/query",
                headers=_notion_headers(token),
                json=body,
            )
            response.raise_for_status()
            data = response.json()

        results = data.get("results", [])
        rows = [
            {
                "id": row.get("id", ""),
                "title": _extract_notion_title(row),
                "url": row.get("url", ""),
                "last_edited": row.get("last_edited_time", ""),
                "properties_summary": _summarize_notion_properties(
                    row.get("properties", {})
                ),
            }
            for row in results
        ]

        return {
            "database_id": database_id,
            "total": len(results),
            "rows": rows,
        }
    except ToolError:
        raise
    except Exception as e:
        logger.exception(f"[Notion] Error querying database: {e}")
        raise ToolError(f"Erro ao consultar database {database_id}: {e}")


async def _notion_list_databases_logic(
    client_id: str | None,
    query: str = "",
    limit: int = 10,
) -> dict:
    """Lista databases do Notion para o cliente."""
    try:
        token = await _get_notion_token(client_id)
        body = {
            "query": query,
            "page_size": limit,
            "filter": {"property": "object", "value": "database"},
        }

        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                f"{NOTION_API_URL}/search",
                headers=_notion_headers(token),
                json=body,
            )
            response.raise_for_status()
            data = response.json()

        databases = []
        for result in data.get("results", []):
            title = "Sem título"
            try:
                title = result["title"][0]["plain_text"]
            except (KeyError, IndexError, TypeError):
                pass

            databases.append(
                {
                    "id": result.get("id", ""),
                    "title": title,
                    "url": result.get("url", ""),
                    "last_edited": result.get("last_edited_time", ""),
                }
            )

        return {"total": len(databases), "databases": databases}
    except ToolError:
        raise
    except Exception as e:
        logger.exception(f"[Notion] Error listing databases: {e}")
        raise ToolError(f"Erro ao listar databases do Notion: {e}")


# =============================================================================
# REGISTRO DE TOOLS
# =============================================================================


@register_module
def register_tools(mcp: FastMCP) -> list[str]:
    """Register Notion tools with the MCP server."""

    @mcp.tool
    @mcp_inject_client_id
    async def notion_list_pages(
        ctx: Context,
        client_id: str | None = None,
        query: str = "",
        limit: int = 20,
    ) -> dict:
        """
        Lista páginas do Notion do cliente.

        Args:
            query: Filtro de busca (opcional)
            limit: Máximo de páginas a retornar (padrão 20)

        Returns:
            Dict com {total, pages: [{id, title, url, last_edited, object_type}]}
        """
        return await _notion_list_pages_logic(
            client_id=client_id, query=query, limit=limit
        )

    @mcp.tool
    @mcp_inject_client_id
    async def notion_read_page(
        ctx: Context,
        page_id: str,
        client_id: str | None = None,
    ) -> dict:
        """
        Lê o conteúdo completo de uma página do Notion.

        Args:
            page_id: ID da página Notion

        Returns:
            Dict com {page_id, title, url, content, block_count}
        """
        return await _notion_read_page_logic(client_id=client_id, page_id=page_id)

    @mcp.tool
    @mcp_inject_client_id
    async def notion_search(
        ctx: Context,
        query: str,
        client_id: str | None = None,
        limit: int = 10,
    ) -> dict:
        """
        Busca páginas e databases no Notion.

        Args:
            query: Texto de busca
            limit: Máximo de resultados (padrão 10)

        Returns:
            Dict com {results: [{id, title, type, url, last_edited}]}
        """
        return await _notion_search_logic(
            client_id=client_id, query=query, limit=limit
        )

    @mcp.tool
    @mcp_inject_client_id
    async def notion_create_page(
        ctx: Context,
        parent_id: str,
        title: str,
        content: str,
        client_id: str | None = None,
        parent_type: str = "page",
    ) -> dict:
        """
        Cria uma nova página no Notion.

        Args:
            parent_id: ID do parent (página ou database)
            title: Título da nova página
            content: Conteúdo da página (parágrafos separados por linha em branco)
            parent_type: 'page' ou 'database' (padrão 'page')

        Returns:
            Dict com {page_id, title, url}
        """
        return await _notion_create_page_logic(
            client_id=client_id,
            parent_id=parent_id,
            title=title,
            content=content,
            parent_type=parent_type,
        )

    @mcp.tool
    @mcp_inject_client_id
    async def notion_update_page(
        ctx: Context,
        page_id: str,
        properties: dict,
        client_id: str | None = None,
        archived: bool | None = None,
    ) -> dict:
        """
        Atualiza propriedades de uma página no Notion.

        Args:
            page_id: ID da página Notion
            properties: Dict de propriedades no schema Notion
            archived: Se informado, arquiva/desarquiva a página

        Returns:
            Dict com {page_id, url, last_edited_time}
        """
        return await _notion_update_page_logic(
            client_id=client_id,
            page_id=page_id,
            properties=properties,
            archived=archived,
        )

    @mcp.tool
    @mcp_inject_client_id
    async def notion_append_blocks(
        ctx: Context,
        page_id: str,
        blocks: list,
        client_id: str | None = None,
    ) -> dict:
        """
        Adiciona blocos ao final de uma página/bloco no Notion.

        Args:
            page_id: ID da página/bloco pai
            blocks: Lista de blocos no schema Notion

        Returns:
            Dict com {added_count, page_id}
        """
        return await _notion_append_blocks_logic(
            client_id=client_id,
            page_id=page_id,
            blocks=blocks,
        )

    @mcp.tool
    @mcp_inject_client_id
    async def notion_delete_block(
        ctx: Context,
        block_id: str,
        client_id: str | None = None,
    ) -> dict:
        """
        Deleta (arquiva) um bloco do Notion.

        Args:
            block_id: ID do bloco

        Returns:
            Dict com {deleted, block_id}
        """
        return await _notion_delete_block_logic(client_id=client_id, block_id=block_id)

    @mcp.tool
    @mcp_inject_client_id
    async def notion_query_database(
        ctx: Context,
        database_id: str,
        client_id: str | None = None,
        filter_dict: dict | None = None,
        sorts: list | None = None,
        page_size: int = 20,
    ) -> dict:
        """
        Consulta linhas de uma database no Notion.

        Args:
            database_id: ID da database Notion
            filter_dict: Filtro no schema da API do Notion
            sorts: Lista de ordenações no schema da API do Notion
            page_size: Quantidade máxima de resultados

        Returns:
            Dict com {database_id, total, rows: [{id, title, url, last_edited, properties_summary}]}
        """
        return await _notion_query_database_logic(
            client_id=client_id,
            database_id=database_id,
            filter_dict=filter_dict,
            sorts=sorts,
            page_size=page_size,
        )

    @mcp.tool
    @mcp_inject_client_id
    async def notion_list_databases(
        ctx: Context,
        client_id: str | None = None,
        query: str = "",
        limit: int = 10,
    ) -> dict:
        """
        Lista databases do Notion.

        Args:
            query: Filtro de busca (opcional)
            limit: Máximo de databases a retornar (padrão 10)

        Returns:
            Dict com {total, databases: [{id, title, url, last_edited}]}
        """
        return await _notion_list_databases_logic(
            client_id=client_id,
            query=query,
            limit=limit,
        )

    return [
        "notion_list_pages",
        "notion_read_page",
        "notion_search",
        "notion_create_page",
        "notion_update_page",
        "notion_append_blocks",
        "notion_delete_block",
        "notion_query_database",
        "notion_list_databases",
    ]
