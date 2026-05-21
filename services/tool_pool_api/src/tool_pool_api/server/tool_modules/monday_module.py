# tool_pool_api/server/tool_modules/monday_module.py
"""
Módulo Monday.com - Ferramentas de Gestão de Projetos

Integração com a API GraphQL do Monday.com para listagem de boards,
itens, criação e atualização de status.
"""

import json
import logging
from collections import defaultdict
from datetime import date, datetime
from uuid import UUID

import httpx
from fastmcp import Context, FastMCP
from fastmcp.exceptions import ToolError

from blu_auth.mcp.auth_middleware import mcp_inject_client_id
from tool_pool_api.server.dependencies import get_context_service
from tool_pool_api.server.tool_modules import register_module

logger = logging.getLogger(__name__)

MONDAY_API_URL = "https://api.monday.com/v2"


# =============================================================================
# HELPERS
# =============================================================================


async def _get_monday_token(client_id: str | None) -> str:
    """Fetch Monday.com token from integration_tokens for the current client."""
    if not client_id:
        raise ToolError("Missing client_id")

    ctx_service = get_context_service()
    token_wrapper = await ctx_service.get_integration_tokens(
        UUID(client_id),
        "monday",
        auto_refresh=False,
    )

    if not token_wrapper or not token_wrapper.is_valid():
        raise ToolError(
            "Monday.com não conectado. Vá em Admin > Integrações para conectar."
        )

    token = token_wrapper.get_decrypted_tokens().get("access_token")
    if not token:
        raise ToolError(
            "Monday.com não conectado. Vá em Admin > Integrações para conectar."
        )

    return token


async def _graphql(query: str, token: str, variables: dict | None = None) -> dict:
    """Execute a GraphQL request against the Monday.com API."""
    payload: dict = {"query": query}
    if variables:
        payload["variables"] = variables

    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(
            MONDAY_API_URL,
            headers={
                "Authorization": token,
                "Content-Type": "application/json",
            },
            json=payload,
        )
        response.raise_for_status()
        data = response.json()

    if "errors" in data:
        errors = data["errors"]
        msg = errors[0].get("message", str(errors)) if errors else "GraphQL error"
        raise ToolError(f"Monday.com API error: {msg}")

    return data.get("data", {})


# =============================================================================
# LÓGICA DE NEGÓCIO (Testável)
# =============================================================================


async def _monday_list_boards_logic(
    ctx: Context,
    client_id: str | None = None,
) -> dict:
    """
    Lista os quadros (boards) do Monday.com do cliente.

    Returns:
        Dict com lista de boards: {boards: [{id, name, description, state}]}
    """
    try:
        token = await _get_monday_token(client_id)
        query = """
        query {
            boards(limit: 20) {
                id
                name
                description
                state
            }
        }
        """
        data = await _graphql(query, token)
        boards = data.get("boards", [])
        logger.info(f"[Monday] Listed {len(boards)} boards for client_id={client_id}")
        return {"boards": boards, "total": len(boards)}
    except ToolError:
        raise
    except Exception as e:
        logger.exception(f"[Monday] Error listing boards: {e}")
        raise ToolError(f"Erro ao listar boards do Monday.com: {e}")


async def _monday_list_items_logic(
    board_id: str,
    limit: int = 50,
    ctx: Context = None,
    client_id: str | None = None,
) -> dict:
    """
    Lista itens de um quadro do Monday.com, com colunas de status, data e responsável.

    Args:
        board_id: ID do quadro
        limit: Máximo de itens a retornar (padrão 50)

    Returns:
        Dict com {board_id, items: [{id, name, status, date, person, raw_columns}]}
    """
    if not board_id or not board_id.strip():
        raise ToolError("board_id é obrigatório.")

    try:
        token = await _get_monday_token(client_id)
        query = f"""
        query {{
            boards(ids: [{board_id}]) {{
                items_page(limit: {limit}) {{
                    items {{
                        id
                        name
                        state
                        column_values {{
                            id
                            text
                            value
                        }}
                    }}
                }}
            }}
        }}
        """
        data = await _graphql(query, token)
        boards = data.get("boards", [])
        if not boards:
            raise ToolError(f"Board não encontrado: {board_id}")

        raw_items = boards[0].get("items_page", {}).get("items", [])

        items = []
        for item in raw_items:
            columns = item.get("column_values", [])
            status = next(
                (c["text"] for c in columns if "status" in c["id"].lower()), None
            )
            date = next(
                (c["text"] for c in columns if "date" in c["id"].lower()), None
            )
            person = next(
                (c["text"] for c in columns if "person" in c["id"].lower()), None
            )
            items.append(
                {
                    "id": item["id"],
                    "name": item["name"],
                    "status": status,
                    "date": date,
                    "person": person,
                    "raw_columns": columns,
                }
            )

        logger.info(
            f"[Monday] Listed {len(items)} items from board {board_id} for client_id={client_id}"
        )
        return {"board_id": board_id, "items": items, "total": len(items)}
    except ToolError:
        raise
    except Exception as e:
        logger.exception(f"[Monday] Error listing items: {e}")
        raise ToolError(f"Erro ao listar itens do board {board_id}: {e}")


async def _monday_create_item_logic(
    board_id: str,
    item_name: str,
    group_id: str | None = None,
    column_values: dict | None = None,
    ctx: Context = None,
    client_id: str | None = None,
) -> dict:
    """
    Cria um novo item em um quadro do Monday.com.

    Args:
        board_id: ID do quadro
        item_name: Nome do item
        group_id: ID do grupo (opcional)
        column_values: Valores das colunas como dict {column_id: value} (opcional)

    Returns:
        Dict com {status, item_id, item_name}
    """
    if not board_id or not board_id.strip():
        raise ToolError("board_id é obrigatório.")
    if not item_name or not item_name.strip():
        raise ToolError("item_name é obrigatório.")

    try:
        token = await _get_monday_token(client_id)
        group_part = f', group_id: "{group_id}"' if group_id else ""
        col_values_part = ""
        if column_values:
            col_values_part = f", column_values: {json.dumps(json.dumps(column_values))}"

        mutation = f"""
        mutation {{
            create_item(
                board_id: {board_id},
                item_name: {json.dumps(item_name)}
                {group_part}
                {col_values_part}
            ) {{
                id
                name
            }}
        }}
        """
        data = await _graphql(mutation, token)
        created = data.get("create_item", {})
        item_id = created.get("id")
        name = created.get("name", item_name)

        logger.info(
            f"[Monday] Created item '{name}' (id={item_id}) in board {board_id} for client_id={client_id}"
        )
        return {"status": "ok", "item_id": item_id, "item_name": name}
    except ToolError:
        raise
    except Exception as e:
        logger.exception(f"[Monday] Error creating item: {e}")
        raise ToolError(f"Erro ao criar item no board {board_id}: {e}")


async def _monday_update_item_status_logic(
    board_id: str,
    item_id: str,
    status_column_id: str,
    new_status: str,
    ctx: Context = None,
    client_id: str | None = None,
) -> dict:
    """
    Atualiza o status de um item no Monday.com.

    Args:
        board_id: ID do quadro
        item_id: ID do item
        status_column_id: ID da coluna de status (geralmente 'status')
        new_status: Novo valor de status (ex: 'Done', 'Em andamento', 'Bloqueado')

    Returns:
        Dict com {status, item_id, new_status}
    """
    if not board_id or not board_id.strip():
        raise ToolError("board_id é obrigatório.")
    if not item_id or not item_id.strip():
        raise ToolError("item_id é obrigatório.")
    if not status_column_id or not status_column_id.strip():
        raise ToolError("status_column_id é obrigatório.")
    if not new_status or not new_status.strip():
        raise ToolError("new_status é obrigatório.")

    try:
        token = await _get_monday_token(client_id)
        mutation = f"""
        mutation {{
            change_simple_column_value(
                board_id: {board_id},
                item_id: {item_id},
                column_id: {json.dumps(status_column_id)},
                value: {json.dumps(new_status)}
            ) {{
                id
            }}
        }}
        """
        await _graphql(mutation, token)

        logger.info(
            f"[Monday] Updated item {item_id} status to '{new_status}' in board {board_id} for client_id={client_id}"
        )
        return {"status": "ok", "item_id": item_id, "new_status": new_status}
    except ToolError:
        raise
    except Exception as e:
        logger.exception(f"[Monday] Error updating item status: {e}")
        raise ToolError(f"Erro ao atualizar status do item {item_id}: {e}")


# =============================================================================
# NOVAS LÓGICAS DE NEGÓCIO
# =============================================================================


def _parse_date(text: str | None) -> date | None:
    """Try to parse a date string from Monday column text."""
    if not text:
        return None
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y"):
        try:
            return datetime.strptime(text.strip(), fmt).date()
        except ValueError:
            continue
    return None


async def _monday_get_board_summary_logic(
    board_id: str,
    ctx: Context = None,
    client_id: str | None = None,
) -> dict:
    """
    Retorna resumo completo de um board: grupos, contagem por status,
    itens em atraso e próximos prazos.

    Args:
        board_id: ID do board Monday.com

    Returns:
        Dict com board_name, total_items, by_status, overdue_count,
        upcoming_count, groups, overdue_items, upcoming_items.
    """
    if not board_id or not board_id.strip():
        raise ToolError("board_id é obrigatório.")

    try:
        token = await _get_monday_token(client_id)
        query = f"""
        query {{
            boards(ids: [{board_id}]) {{
                name
                description
                groups {{
                    id
                    title
                }}
                items_page(limit: 100) {{
                    items {{
                        id
                        name
                        state
                        column_values {{
                            id
                            text
                            value
                        }}
                    }}
                }}
            }}
        }}
        """
        data = await _graphql(query, token)
        boards = data.get("boards", [])
        if not boards:
            raise ToolError(f"Board não encontrado: {board_id}")

        board = boards[0]
        board_name = board.get("name", board_id)
        groups = [g["title"] for g in board.get("groups", [])]
        raw_items = board.get("items_page", {}).get("items", [])

        today = date.today()
        in_seven = (today.toordinal() + 7)

        by_status: dict[str, int] = defaultdict(int)
        overdue_items = []
        upcoming_items = []

        for item in raw_items:
            columns = item.get("column_values", [])
            status = next(
                (c["text"] for c in columns if "status" in c["id"].lower()), None
            )
            date_text = next(
                (c["text"] for c in columns if "date" in c["id"].lower()), None
            )
            person = next(
                (c["text"] for c in columns if "person" in c["id"].lower()), None
            )

            status_key = status or "Sem status"
            by_status[status_key] += 1

            item_date = _parse_date(date_text)
            if item_date:
                if item_date < today:
                    overdue_items.append(
                        {"name": item["name"], "status": status, "person": person}
                    )
                elif item_date.toordinal() <= in_seven:
                    upcoming_items.append(
                        {"name": item["name"], "date": date_text, "status": status}
                    )

        logger.info(
            f"[Monday] Board summary for {board_id}: {len(raw_items)} items, "
            f"{len(overdue_items)} overdue, {len(upcoming_items)} upcoming"
        )
        return {
            "board_name": board_name,
            "total_items": len(raw_items),
            "by_status": dict(by_status),
            "overdue_count": len(overdue_items),
            "upcoming_count": len(upcoming_items),
            "groups": groups,
            "overdue_items": overdue_items,
            "upcoming_items": upcoming_items,
        }
    except ToolError:
        raise
    except Exception as e:
        logger.exception(f"[Monday] Error getting board summary: {e}")
        raise ToolError(f"Erro ao obter resumo do board {board_id}: {e}")


async def _monday_get_item_updates_logic(
    item_id: str,
    limit: int = 20,
    ctx: Context = None,
    client_id: str | None = None,
) -> dict:
    """
    Lê updates (comentários) de um item do Monday.com.

    Args:
        item_id: ID do item
        limit: Máximo de updates a retornar (padrão 20)

    Returns:
        Dict com item_id, item_name e lista de updates com replies.
    """
    if not item_id or not item_id.strip():
        raise ToolError("item_id é obrigatório.")

    try:
        token = await _get_monday_token(client_id)
        query = f"""
        query {{
            items(ids: [{item_id}]) {{
                id
                name
                updates(limit: {limit}) {{
                    id
                    text_body
                    created_at
                    creator {{
                        name
                        email
                    }}
                    replies {{
                        id
                        text_body
                        created_at
                        creator {{
                            name
                        }}
                    }}
                }}
            }}
        }}
        """
        data = await _graphql(query, token)
        items = data.get("items", [])
        if not items:
            raise ToolError(f"Item não encontrado: {item_id}")

        item = items[0]
        updates = []
        for u in item.get("updates", []):
            creator = u.get("creator") or {}
            replies = [
                {
                    "id": r["id"],
                    "text": r.get("text_body", ""),
                    "created_at": r.get("created_at"),
                    "creator_name": (r.get("creator") or {}).get("name"),
                }
                for r in u.get("replies", [])
            ]
            updates.append(
                {
                    "id": u["id"],
                    "text": u.get("text_body", ""),
                    "created_at": u.get("created_at"),
                    "creator_name": creator.get("name"),
                    "creator_email": creator.get("email"),
                    "replies": replies,
                }
            )

        logger.info(
            f"[Monday] Fetched {len(updates)} updates for item {item_id}"
        )
        return {
            "item_id": item_id,
            "item_name": item.get("name"),
            "updates": updates,
        }
    except ToolError:
        raise
    except Exception as e:
        logger.exception(f"[Monday] Error fetching item updates: {e}")
        raise ToolError(f"Erro ao buscar updates do item {item_id}: {e}")


async def _monday_summarize_board_logic(
    board_id: str,
    include_updates: bool = False,
    ctx: Context = None,
    client_id: str | None = None,
) -> dict:
    """
    Gera briefing narrativo de um board: status geral, bloqueios,
    responsáveis, prazos.

    Args:
        board_id: ID do board Monday.com
        include_updates: Se True, busca o último update de cada item atrasado

    Returns:
        Dict com board_id, summary_text (narrativo com emojis),
        overdue_items e upcoming_items.
    """
    if not board_id or not board_id.strip():
        raise ToolError("board_id é obrigatório.")

    try:
        token = await _get_monday_token(client_id)

        # Reuse board summary data
        summary = await _monday_get_board_summary_logic(
            board_id=board_id, ctx=ctx, client_id=client_id
        )

        board_name = summary["board_name"]
        total = summary["total_items"]
        by_status = summary["by_status"]
        overdue_items = summary["overdue_items"]
        upcoming_items = summary["upcoming_items"]

        # Counts for headline
        done_count = sum(
            v for k, v in by_status.items() if "done" in k.lower() or "conclu" in k.lower()
        )
        in_progress_count = sum(
            v
            for k, v in by_status.items()
            if "andamento" in k.lower() or "progress" in k.lower() or "working" in k.lower()
        )

        # Build person → item count map from board data (re-query not needed; use summary overdue+upcoming as proxy)
        # For a full by-person map, we fetch raw items again via list_items
        raw = await _monday_list_items_logic(
            board_id=board_id, limit=100, ctx=ctx, client_id=client_id
        )
        person_counts: dict[str, int] = defaultdict(int)
        for it in raw.get("items", []):
            person = it.get("person") or "Sem responsável"
            for p in (person.split(",") if person else ["Sem responsável"]):
                person_counts[p.strip()] += 1

        # Optionally fetch last update for each overdue item
        if include_updates and overdue_items:
            for oi in overdue_items:
                # We need item_id — get from raw items by name match
                matched = next(
                    (it for it in raw.get("items", []) if it["name"] == oi["name"]),
                    None,
                )
                if matched:
                    try:
                        upd = await _monday_get_item_updates_logic(
                            item_id=matched["id"], limit=1, ctx=ctx, client_id=client_id
                        )
                        last = upd["updates"][0] if upd["updates"] else None
                        oi["last_update"] = last["text"] if last else None
                        oi["last_update_by"] = last["creator_name"] if last else None
                    except Exception:
                        pass

        # Build summary text
        lines = [
            f"📋 {board_name}",
            f"Total: {total} | Em andamento: {in_progress_count} | Concluídos: {done_count} | Atrasados: {summary['overdue_count']}",
        ]

        if overdue_items:
            lines.append("\n🔴 Atrasados:")
            for oi in overdue_items:
                person_str = f", {oi['person']}" if oi.get("person") else ""
                lines.append(f"  - {oi['name']} ({oi.get('status', '—')}{person_str})")
                if oi.get("last_update"):
                    lines.append(f"    💬 {oi['last_update'][:120]}")
        else:
            lines.append("\n✅ Nenhum item atrasado.")

        if upcoming_items:
            lines.append("\n📅 Próximos 7 dias:")
            for ui in upcoming_items:
                lines.append(
                    f"  - {ui['name']} ({ui.get('date', '—')}, {ui.get('status', '—')})"
                )

        if person_counts:
            lines.append("\n👥 Por responsável:")
            for person, count in sorted(person_counts.items(), key=lambda x: -x[1]):
                lines.append(f"  - {person}: {count} iten{'s' if count != 1 else ''}")

        summary_text = "\n".join(lines)

        logger.info(f"[Monday] Board narrative summary generated for {board_id}")
        return {
            "board_id": board_id,
            "summary_text": summary_text,
            "overdue_items": overdue_items,
            "upcoming_items": upcoming_items,
        }
    except ToolError:
        raise
    except Exception as e:
        logger.exception(f"[Monday] Error summarizing board: {e}")
        raise ToolError(f"Erro ao gerar resumo narrativo do board {board_id}: {e}")


# =============================================================================
# REGISTRO DO MÓDULO
# =============================================================================


@register_module
def register_tools(mcp: FastMCP) -> list[str]:
    """Registra as tools do módulo Monday.com."""

    mcp.tool(
        name="monday_list_boards",
        description=(
            "Lista os quadros (boards) do Monday.com do cliente. "
            "Retorna id, nome, descrição e estado de até 20 boards. "
            "Use para descobrir quais quadros estão disponíveis antes de listar itens."
        ),
    )(mcp_inject_client_id(get_context_service)(_monday_list_boards_logic))

    mcp.tool(
        name="monday_list_items",
        description=(
            "Lista itens de um quadro do Monday.com, com colunas de status, data e responsável. "
            "Parâmetros: board_id (string, obrigatório), limit (int, padrão 50). "
            "Use monday_list_boards primeiro para obter o board_id correto."
        ),
    )(mcp_inject_client_id(get_context_service)(_monday_list_items_logic))

    mcp.tool(
        name="monday_create_item",
        description=(
            "Cria um novo item em um quadro do Monday.com. "
            "Parâmetros: board_id (string, obrigatório), item_name (string, obrigatório), "
            "group_id (string, opcional), column_values (dict {column_id: value}, opcional). "
            "Retorna o id e nome do item criado."
        ),
    )(mcp_inject_client_id(get_context_service)(_monday_create_item_logic))

    mcp.tool(
        name="monday_update_item_status",
        description=(
            "Atualiza o status de um item no Monday.com. "
            "Parâmetros: board_id (string), item_id (string), "
            "status_column_id (string — ID da coluna de status, geralmente 'status'), "
            "new_status (string — ex: 'Done', 'Em andamento', 'Bloqueado'). "
            "Use monday_list_items para obter item_id e status_column_id válidos."
        ),
    )(mcp_inject_client_id(get_context_service)(_monday_update_item_status_logic))

    mcp.tool(
        name="monday_get_board_summary",
        description=(
            "Retorna resumo completo de um board do Monday.com: grupos, contagem por status, "
            "itens em atraso e próximos prazos (7 dias). "
            "Parâmetros: board_id (string, obrigatório). "
            "Retorna board_name, total_items, by_status, overdue_count, upcoming_count, "
            "groups, overdue_items e upcoming_items."
        ),
    )(mcp_inject_client_id(get_context_service)(_monday_get_board_summary_logic))

    mcp.tool(
        name="monday_get_item_updates",
        description=(
            "Lê updates (comentários e replies) de um item do Monday.com. "
            "Parâmetros: item_id (string, obrigatório), limit (int, padrão 20). "
            "Retorna item_id, item_name e lista de updates com texto, data, criador e replies."
        ),
    )(mcp_inject_client_id(get_context_service)(_monday_get_item_updates_logic))

    mcp.tool(
        name="monday_summarize_board",
        description=(
            "Gera briefing narrativo de um board do Monday.com com emojis: status geral, "
            "bloqueios, responsáveis e prazos. "
            "Parâmetros: board_id (string, obrigatório), "
            "include_updates (bool, padrão False — se True inclui último comentário dos itens atrasados). "
            "Retorna board_id, summary_text formatado, overdue_items e upcoming_items."
        ),
    )(mcp_inject_client_id(get_context_service)(_monday_summarize_board_logic))

    registered = [
        "monday_list_boards",
        "monday_list_items",
        "monday_create_item",
        "monday_update_item_status",
        "monday_get_board_summary",
        "monday_get_item_updates",
        "monday_summarize_board",
    ]
    logger.info(f"[Monday Module] Tools registered: {registered}")
    return registered
