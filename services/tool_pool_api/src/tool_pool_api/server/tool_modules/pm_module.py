# tool_pool_api/server/tool_modules/pm_module.py
"""
Módulo de Gestão de Projetos — Asana, ClickUp, Linear

Integração com as APIs REST/GraphQL de Asana, ClickUp e Linear para listagem
de projetos, tarefas, issues e comentários.
"""

import logging
from datetime import datetime
from uuid import UUID

import httpx
from fastmcp import Context, FastMCP
from fastmcp.exceptions import ToolError

from blu_auth.mcp.auth_middleware import mcp_inject_client_id
from tool_pool_api.server.dependencies import get_context_service
from tool_pool_api.server.tool_modules import register_module

logger = logging.getLogger(__name__)

ASANA_API_URL = "https://app.asana.com/api/1.0"
CLICKUP_API_URL = "https://api.clickup.com/api/v2"
LINEAR_API_URL = "https://api.linear.app/graphql"


# =============================================================================
# HELPERS — Token fetching
# =============================================================================


async def _get_asana_token(client_id: str | None) -> str:
    if not client_id:
        raise ToolError("Missing client_id")
    ctx_service = get_context_service()
    token_wrapper = await ctx_service.get_integration_tokens(
        UUID(client_id), "asana", auto_refresh=False
    )
    if not token_wrapper or not token_wrapper.is_valid():
        raise ToolError("Asana não conectado. Vá em Admin > Integrações para conectar.")
    token = token_wrapper.get_decrypted_tokens().get("access_token")
    if not token:
        raise ToolError("Asana não conectado. Vá em Admin > Integrações para conectar.")
    return token


async def _get_clickup_token(client_id: str | None) -> str:
    if not client_id:
        raise ToolError("Missing client_id")
    ctx_service = get_context_service()
    token_wrapper = await ctx_service.get_integration_tokens(
        UUID(client_id), "clickup", auto_refresh=False
    )
    if not token_wrapper or not token_wrapper.is_valid():
        raise ToolError("ClickUp não conectado. Vá em Admin > Integrações para conectar.")
    token = token_wrapper.get_decrypted_tokens().get("access_token")
    if not token:
        raise ToolError("ClickUp não conectado. Vá em Admin > Integrações para conectar.")
    return token


async def _get_linear_token(client_id: str | None) -> str:
    if not client_id:
        raise ToolError("Missing client_id")
    ctx_service = get_context_service()
    token_wrapper = await ctx_service.get_integration_tokens(
        UUID(client_id), "linear", auto_refresh=False
    )
    if not token_wrapper or not token_wrapper.is_valid():
        raise ToolError("Linear não conectado. Vá em Admin > Integrações para conectar.")
    token = token_wrapper.get_decrypted_tokens().get("access_token")
    if not token:
        raise ToolError("Linear não conectado. Vá em Admin > Integrações para conectar.")
    return token


def _ms_to_iso(ms_str: str | None) -> str | None:
    """Convert unix milliseconds string to ISO date string."""
    if not ms_str:
        return None
    try:
        return datetime.utcfromtimestamp(int(ms_str) / 1000).strftime("%Y-%m-%d")
    except Exception:
        return ms_str


# =============================================================================
# LÓGICA DE NEGÓCIO
# =============================================================================


async def _asana_list_projects_logic(
    workspace_id: str | None = None,
    ctx: Context = None,
    client_id: str | None = None,
) -> dict:
    """
    Lista projetos do Asana do cliente.

    Args:
        workspace_id: ID do workspace Asana (opcional — usa o primeiro disponível)

    Returns:
        Dict com {projects: [{id, name, status, due_on, owner, notes_preview}]}
    """
    try:
        token = await _get_asana_token(client_id)
        headers = {"Authorization": f"Bearer {token}"}

        async with httpx.AsyncClient(timeout=30) as client:
            if not workspace_id:
                resp = await client.get(f"{ASANA_API_URL}/workspaces", headers=headers)
                resp.raise_for_status()
                workspaces = resp.json().get("data", [])
                if not workspaces:
                    raise ToolError("Nenhum workspace encontrado no Asana.")
                workspace_id = workspaces[0]["gid"]

            params = {
                "workspace": workspace_id,
                "opt_fields": "name,current_status.text,due_on,owner.name,notes",
            }
            resp = await client.get(f"{ASANA_API_URL}/projects", headers=headers, params=params)
            resp.raise_for_status()
            raw = resp.json().get("data", [])

        projects = [
            {
                "id": p.get("gid"),
                "name": p.get("name"),
                "status": (p.get("current_status") or {}).get("text"),
                "due_on": p.get("due_on"),
                "owner": (p.get("owner") or {}).get("name"),
                "notes_preview": (p.get("notes") or "")[:100],
            }
            for p in raw
        ]
        logger.info(f"[Asana] Listed {len(projects)} projects for client_id={client_id}")
        return {"projects": projects}
    except ToolError:
        raise
    except Exception as e:
        logger.exception(f"[Asana] Error listing projects: {e}")
        raise ToolError(f"Erro ao listar projetos do Asana: {e}")


async def _asana_get_project_tasks_logic(
    project_id: str,
    completed: bool = False,
    ctx: Context = None,
    client_id: str | None = None,
) -> dict:
    """
    Lista tarefas de um projeto Asana.

    Args:
        project_id: ID do projeto
        completed: Incluir tarefas concluídas (padrão False)

    Returns:
        Dict com {project_id, total, tasks: [{id, name, assignee, due_on, completed, notes_preview}]}
    """
    if not project_id or not project_id.strip():
        raise ToolError("project_id é obrigatório.")
    try:
        token = await _get_asana_token(client_id)
        headers = {"Authorization": f"Bearer {token}"}
        params = {
            "project": project_id,
            "completed": str(completed).lower(),
            "opt_fields": "name,assignee.name,due_on,completed,notes",
        }
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(f"{ASANA_API_URL}/tasks", headers=headers, params=params)
            resp.raise_for_status()
            raw = resp.json().get("data", [])

        tasks = [
            {
                "id": t.get("gid"),
                "name": t.get("name"),
                "assignee": (t.get("assignee") or {}).get("name"),
                "due_on": t.get("due_on"),
                "completed": t.get("completed"),
                "notes_preview": (t.get("notes") or "")[:100],
            }
            for t in raw
        ]
        logger.info(
            f"[Asana] Listed {len(tasks)} tasks for project {project_id}, client_id={client_id}"
        )
        return {"project_id": project_id, "total": len(tasks), "tasks": tasks}
    except ToolError:
        raise
    except Exception as e:
        logger.exception(f"[Asana] Error listing tasks: {e}")
        raise ToolError(f"Erro ao listar tarefas do projeto {project_id}: {e}")


async def _clickup_list_tasks_logic(
    list_id: str,
    status: str | None = None,
    ctx: Context = None,
    client_id: str | None = None,
) -> dict:
    """
    Lista tarefas de uma lista do ClickUp.

    Args:
        list_id: ID da lista ClickUp
        status: Filtrar por status (opcional)

    Returns:
        Dict com {list_id, total, tasks: [{id, name, status, assignee, due_date, desc_preview}]}
    """
    if not list_id or not list_id.strip():
        raise ToolError("list_id é obrigatório.")
    try:
        token = await _get_clickup_token(client_id)
        headers = {"Authorization": token}
        url = f"{CLICKUP_API_URL}/list/{list_id}/task"
        params = {}
        if status:
            params["statuses[]"] = status

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(url, headers=headers, params=params)
            resp.raise_for_status()
            raw = resp.json().get("tasks", [])

        tasks = [
            {
                "id": t.get("id"),
                "name": t.get("name"),
                "status": (t.get("status") or {}).get("status"),
                "assignee": (t.get("assignees") or [{}])[0].get("username")
                if t.get("assignees")
                else None,
                "due_date": _ms_to_iso(t.get("due_date")),
                "desc_preview": (t.get("description") or "")[:100],
            }
            for t in raw
        ]
        logger.info(
            f"[ClickUp] Listed {len(tasks)} tasks for list {list_id}, client_id={client_id}"
        )
        return {"list_id": list_id, "total": len(tasks), "tasks": tasks}
    except ToolError:
        raise
    except Exception as e:
        logger.exception(f"[ClickUp] Error listing tasks: {e}")
        raise ToolError(f"Erro ao listar tarefas da lista {list_id}: {e}")


async def _clickup_get_task_comments_logic(
    task_id: str,
    ctx: Context = None,
    client_id: str | None = None,
) -> dict:
    """
    Lista comentários de uma tarefa do ClickUp.

    Args:
        task_id: ID da tarefa

    Returns:
        Dict com {task_id, comments: [{id, text, user, date}]}
    """
    if not task_id or not task_id.strip():
        raise ToolError("task_id é obrigatório.")
    try:
        token = await _get_clickup_token(client_id)
        headers = {"Authorization": token}
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                f"{CLICKUP_API_URL}/task/{task_id}/comment", headers=headers
            )
            resp.raise_for_status()
            raw = resp.json().get("comments", [])

        comments = [
            {
                "id": c.get("id"),
                "text": c.get("comment_text"),
                "user": (c.get("user") or {}).get("username"),
                "date": c.get("date"),
            }
            for c in raw
        ]
        logger.info(
            f"[ClickUp] Listed {len(comments)} comments for task {task_id}, client_id={client_id}"
        )
        return {"task_id": task_id, "comments": comments}
    except ToolError:
        raise
    except Exception as e:
        logger.exception(f"[ClickUp] Error getting comments: {e}")
        raise ToolError(f"Erro ao listar comentários da tarefa {task_id}: {e}")


async def _linear_list_issues_logic(
    team_id: str | None = None,
    status: str | None = None,
    limit: int = 30,
    ctx: Context = None,
    client_id: str | None = None,
) -> dict:
    """
    Lista issues do Linear.

    Args:
        team_id: Filtrar por team ID (opcional)
        status: Filtrar por nome de status (opcional — filtragem client-side)
        limit: Máximo de issues a retornar (padrão 30)

    Returns:
        Dict com {total, issues: [{id, title, priority, state, assignee, project, due_date}]}
    """
    try:
        token = await _get_linear_token(client_id)
        headers = {"Authorization": token, "Content-Type": "application/json"}

        filter_part = ""
        if team_id:
            filter_part = f'(filter: {{team: {{id: {{eq: "{team_id}"}}}}}}, first: {limit})'
        else:
            filter_part = f"(first: {limit})"

        query = f"""
        {{
            issues{filter_part} {{
                nodes {{
                    id
                    title
                    priority
                    state {{ name }}
                    assignee {{ name }}
                    project {{ name }}
                    dueDate
                    updatedAt
                }}
            }}
        }}
        """
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                LINEAR_API_URL, headers=headers, json={"query": query}
            )
            resp.raise_for_status()
            data = resp.json()

        if "errors" in data:
            msg = data["errors"][0].get("message", "GraphQL error")
            raise ToolError(f"Linear API error: {msg}")

        nodes = data.get("data", {}).get("issues", {}).get("nodes", [])

        issues = [
            {
                "id": n.get("id"),
                "title": n.get("title"),
                "priority": n.get("priority"),
                "state": (n.get("state") or {}).get("name"),
                "assignee": (n.get("assignee") or {}).get("name"),
                "project": (n.get("project") or {}).get("name"),
                "due_date": n.get("dueDate"),
            }
            for n in nodes
        ]

        if status:
            issues = [i for i in issues if (i["state"] or "").lower() == status.lower()]

        logger.info(f"[Linear] Listed {len(issues)} issues for client_id={client_id}")
        return {"total": len(issues), "issues": issues}
    except ToolError:
        raise
    except Exception as e:
        logger.exception(f"[Linear] Error listing issues: {e}")
        raise ToolError(f"Erro ao listar issues do Linear: {e}")


async def _linear_get_project_summary_logic(
    project_id: str,
    ctx: Context = None,
    client_id: str | None = None,
) -> dict:
    """
    Retorna resumo de um projeto do Linear com progresso, membros e issues.

    Args:
        project_id: ID do projeto

    Returns:
        Dict com {name, description, progress_percent, state, members, issues_by_state, overdue_count, issues}
    """
    if not project_id or not project_id.strip():
        raise ToolError("project_id é obrigatório.")
    try:
        token = await _get_linear_token(client_id)
        headers = {"Authorization": token, "Content-Type": "application/json"}
        query = f"""
        {{
            project(id: "{project_id}") {{
                name
                description
                state
                progress
                members {{ nodes {{ name }} }}
                issues {{
                    nodes {{
                        id
                        title
                        state {{ name }}
                        priority
                        assignee {{ name }}
                        dueDate
                    }}
                }}
            }}
        }}
        """
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                LINEAR_API_URL, headers=headers, json={"query": query}
            )
            resp.raise_for_status()
            data = resp.json()

        if "errors" in data:
            msg = data["errors"][0].get("message", "GraphQL error")
            raise ToolError(f"Linear API error: {msg}")

        project = data.get("data", {}).get("project")
        if not project:
            raise ToolError(f"Projeto não encontrado: {project_id}")

        members = [m.get("name") for m in project.get("members", {}).get("nodes", [])]
        raw_issues = project.get("issues", {}).get("nodes", [])

        issues_by_state: dict[str, int] = {}
        overdue_count = 0
        today = datetime.utcnow().strftime("%Y-%m-%d")
        issues = []
        for n in raw_issues:
            state_name = (n.get("state") or {}).get("name", "Unknown")
            issues_by_state[state_name] = issues_by_state.get(state_name, 0) + 1
            due = n.get("dueDate")
            if due and due < today and state_name.lower() not in ("done", "cancelled", "canceled"):
                overdue_count += 1
            issues.append(
                {
                    "id": n.get("id"),
                    "title": n.get("title"),
                    "state": state_name,
                    "priority": n.get("priority"),
                    "assignee": (n.get("assignee") or {}).get("name"),
                    "due_date": due,
                }
            )

        progress = project.get("progress", 0) or 0
        logger.info(f"[Linear] Got project summary for {project_id}, client_id={client_id}")
        return {
            "name": project.get("name"),
            "description": project.get("description"),
            "progress_percent": round(progress * 100),
            "state": project.get("state"),
            "members": members,
            "issues_by_state": issues_by_state,
            "overdue_count": overdue_count,
            "issues": issues,
        }
    except ToolError:
        raise
    except Exception as e:
        logger.exception(f"[Linear] Error getting project summary: {e}")
        raise ToolError(f"Erro ao obter resumo do projeto {project_id}: {e}")


# =============================================================================
# ASANA — new capabilities
# =============================================================================


async def _asana_create_task_logic(
    workspace_gid: str,
    name: str,
    notes: str = "",
    assignee_gid: str | None = None,
    due_on: str | None = None,
    project_gid: str | None = None,
    parent_gid: str | None = None,
    resource_subtype: str = "default_task",
    ctx: Context = None,
    client_id: str | None = None,
) -> dict:
    """
    Cria uma tarefa no Asana.

    Args:
        workspace_gid: GID do workspace
        name: Nome da tarefa
        notes: Descrição da tarefa (opcional)
        assignee_gid: GID do responsável (opcional)
        due_on: Data de entrega no formato YYYY-MM-DD (opcional)
        project_gid: GID do projeto (opcional)
        parent_gid: GID da tarefa pai (opcional)
        resource_subtype: Subtipo da tarefa (padrão: default_task)

    Returns:
        Dict com {gid, name, permalink_url}
    """
    if not workspace_gid or not name:
        raise ToolError("workspace_gid e name são obrigatórios.")
    try:
        token = await _get_asana_token(client_id)
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

        body_data: dict = {
            "workspace": workspace_gid,
            "name": name,
            "notes": notes,
            "resource_subtype": resource_subtype,
        }
        if assignee_gid is not None:
            body_data["assignee"] = assignee_gid
        if due_on is not None:
            body_data["due_on"] = due_on
        if project_gid is not None:
            body_data["projects"] = [project_gid]
        if parent_gid is not None:
            body_data["parent"] = parent_gid

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{ASANA_API_URL}/tasks",
                headers=headers,
                json={"data": body_data},
                params={"opt_fields": "gid,name,permalink_url"},
            )
            resp.raise_for_status()
            result = resp.json().get("data", {})

        logger.info(f"[Asana] Created task '{name}' for client_id={client_id}")
        return {
            "gid": result.get("gid"),
            "name": result.get("name"),
            "permalink_url": result.get("permalink_url"),
        }
    except ToolError:
        raise
    except Exception as e:
        logger.exception(f"[Asana] Error creating task: {e}")
        raise ToolError(f"Erro ao criar tarefa no Asana: {e}")


async def _asana_update_task_logic(
    task_gid: str,
    name: str | None = None,
    notes: str | None = None,
    completed: bool | None = None,
    assignee_gid: str | None = None,
    due_on: str | None = None,
    ctx: Context = None,
    client_id: str | None = None,
) -> dict:
    """
    Atualiza uma tarefa no Asana.

    Args:
        task_gid: GID da tarefa
        name: Novo nome (opcional)
        notes: Nova descrição (opcional)
        completed: Status de conclusão (opcional)
        assignee_gid: Novo responsável (opcional)
        due_on: Nova data de entrega (opcional)

    Returns:
        Dict com {gid, name, completed, permalink_url}
    """
    if not task_gid:
        raise ToolError("task_gid é obrigatório.")
    try:
        token = await _get_asana_token(client_id)
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

        body_data: dict = {}
        if name is not None:
            body_data["name"] = name
        if notes is not None:
            body_data["notes"] = notes
        if completed is not None:
            body_data["completed"] = completed
        if assignee_gid is not None:
            body_data["assignee"] = assignee_gid
        if due_on is not None:
            body_data["due_on"] = due_on

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.put(
                f"{ASANA_API_URL}/tasks/{task_gid}",
                headers=headers,
                json={"data": body_data},
                params={"opt_fields": "gid,name,completed,permalink_url"},
            )
            resp.raise_for_status()
            result = resp.json().get("data", {})

        logger.info(f"[Asana] Updated task {task_gid} for client_id={client_id}")
        return {
            "gid": result.get("gid"),
            "name": result.get("name"),
            "completed": result.get("completed"),
            "permalink_url": result.get("permalink_url"),
        }
    except ToolError:
        raise
    except Exception as e:
        logger.exception(f"[Asana] Error updating task: {e}")
        raise ToolError(f"Erro ao atualizar tarefa {task_gid}: {e}")


async def _asana_get_task_stories_logic(
    task_gid: str,
    limit: int = 30,
    ctx: Context = None,
    client_id: str | None = None,
) -> dict:
    """
    Lista comentários (stories) de uma tarefa do Asana.

    Args:
        task_gid: GID da tarefa
        limit: Número máximo de stories a retornar (padrão 30)

    Returns:
        Dict com {task_gid, total, comments: [{text, author, created_at}]}
    """
    if not task_gid:
        raise ToolError("task_gid é obrigatório.")
    try:
        token = await _get_asana_token(client_id)
        headers = {"Authorization": f"Bearer {token}"}
        params = {
            "opt_fields": "type,text,created_at,created_by.name",
            "limit": limit,
        }

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                f"{ASANA_API_URL}/tasks/{task_gid}/stories",
                headers=headers,
                params=params,
            )
            resp.raise_for_status()
            raw = resp.json().get("data", [])

        comments = [
            {
                "text": s.get("text"),
                "author": (s.get("created_by") or {}).get("name"),
                "created_at": s.get("created_at"),
            }
            for s in raw
            if s.get("type") == "comment"
        ]
        logger.info(f"[Asana] Got {len(comments)} comments for task {task_gid}, client_id={client_id}")
        return {"task_gid": task_gid, "total": len(comments), "comments": comments}
    except ToolError:
        raise
    except Exception as e:
        logger.exception(f"[Asana] Error getting task stories: {e}")
        raise ToolError(f"Erro ao listar comentários da tarefa {task_gid}: {e}")


async def _asana_add_task_comment_logic(
    task_gid: str,
    text: str,
    ctx: Context = None,
    client_id: str | None = None,
) -> dict:
    """
    Adiciona um comentário a uma tarefa do Asana.

    Args:
        task_gid: GID da tarefa
        text: Texto do comentário

    Returns:
        Dict com {story_gid, text, created_at}
    """
    if not task_gid or not text:
        raise ToolError("task_gid e text são obrigatórios.")
    try:
        token = await _get_asana_token(client_id)
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{ASANA_API_URL}/tasks/{task_gid}/stories",
                headers=headers,
                json={"data": {"text": text}},
            )
            resp.raise_for_status()
            result = resp.json().get("data", {})

        logger.info(f"[Asana] Added comment to task {task_gid}, client_id={client_id}")
        return {
            "story_gid": result.get("gid"),
            "text": text,
            "created_at": result.get("created_at"),
        }
    except ToolError:
        raise
    except Exception as e:
        logger.exception(f"[Asana] Error adding comment: {e}")
        raise ToolError(f"Erro ao adicionar comentário na tarefa {task_gid}: {e}")


async def _asana_search_tasks_logic(
    workspace_gid: str,
    text: str = "",
    assignee_gid: str | None = None,
    project_gid: str | None = None,
    completed: bool = False,
    limit: int = 20,
    ctx: Context = None,
    client_id: str | None = None,
) -> dict:
    """
    Busca tarefas em um workspace do Asana.

    Args:
        workspace_gid: GID do workspace
        text: Texto para busca (opcional)
        assignee_gid: Filtrar por responsável (opcional)
        project_gid: Filtrar por projeto (opcional)
        completed: Incluir apenas tarefas concluídas (padrão False)
        limit: Máximo de resultados (padrão 20)

    Returns:
        Dict com {total, tasks: [{gid, name, due_on, completed, assignee_name, permalink_url}]}
    """
    if not workspace_gid:
        raise ToolError("workspace_gid é obrigatório.")
    try:
        token = await _get_asana_token(client_id)
        headers = {"Authorization": f"Bearer {token}"}
        params: dict = {
            "opt_fields": "gid,name,due_on,completed,assignee.name,permalink_url",
            "completed": str(completed).lower(),
            "limit": limit,
        }
        if text:
            params["text"] = text
        if assignee_gid:
            params["assignee"] = assignee_gid
        if project_gid:
            params["projects.any"] = project_gid

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                f"{ASANA_API_URL}/workspaces/{workspace_gid}/tasks/search",
                headers=headers,
                params=params,
            )
            resp.raise_for_status()
            raw = resp.json().get("data", [])

        tasks = [
            {
                "gid": t.get("gid"),
                "name": t.get("name"),
                "due_on": t.get("due_on"),
                "completed": t.get("completed"),
                "assignee_name": (t.get("assignee") or {}).get("name"),
                "permalink_url": t.get("permalink_url"),
            }
            for t in raw
        ]
        logger.info(f"[Asana] Search returned {len(tasks)} tasks for client_id={client_id}")
        return {"total": len(tasks), "tasks": tasks}
    except ToolError:
        raise
    except Exception as e:
        logger.exception(f"[Asana] Error searching tasks: {e}")
        raise ToolError(f"Erro ao buscar tarefas no Asana: {e}")


# =============================================================================
# LINEAR — new capabilities
# =============================================================================


async def _linear_list_teams_logic(
    ctx: Context = None,
    client_id: str | None = None,
) -> dict:
    """
    Lista os times do Linear.

    Returns:
        Dict com {teams: [{id, name, key, description, member_count}]}
    """
    try:
        token = await _get_linear_token(client_id)
        headers = {"Authorization": token, "Content-Type": "application/json"}
        query = """
        {
            teams {
                nodes {
                    id
                    name
                    key
                    description
                    members { nodes { id name email } }
                }
            }
        }
        """
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(LINEAR_API_URL, headers=headers, json={"query": query})
            resp.raise_for_status()
            data = resp.json()

        if "errors" in data:
            msg = data["errors"][0].get("message", "GraphQL error")
            raise ToolError(f"Linear API error: {msg}")

        nodes = data.get("data", {}).get("teams", {}).get("nodes", [])
        teams = [
            {
                "id": t.get("id"),
                "name": t.get("name"),
                "key": t.get("key"),
                "description": t.get("description"),
                "member_count": len((t.get("members") or {}).get("nodes", [])),
            }
            for t in nodes
        ]
        logger.info(f"[Linear] Listed {len(teams)} teams for client_id={client_id}")
        return {"teams": teams}
    except ToolError:
        raise
    except Exception as e:
        logger.exception(f"[Linear] Error listing teams: {e}")
        raise ToolError(f"Erro ao listar times do Linear: {e}")


async def _linear_create_issue_logic(
    team_id: str,
    title: str,
    description: str = "",
    priority: int = 0,
    assignee_id: str | None = None,
    label_ids: list | None = None,
    ctx: Context = None,
    client_id: str | None = None,
) -> dict:
    """
    Cria uma issue no Linear.

    Args:
        team_id: ID do time
        title: Título da issue
        description: Descrição (opcional)
        priority: Prioridade 0-4 (padrão 0 = sem prioridade)
        assignee_id: ID do responsável (opcional)
        label_ids: Lista de IDs de labels (opcional)

    Returns:
        Dict com {success, issue_id, title, url, state}
    """
    if not team_id or not title:
        raise ToolError("team_id e title são obrigatórios.")
    try:
        token = await _get_linear_token(client_id)
        headers = {"Authorization": token, "Content-Type": "application/json"}
        mutation = """
        mutation CreateIssue($input: IssueCreateInput!) {
            issueCreate(input: $input) {
                success
                issue { id title url state { name } }
            }
        }
        """
        input_vars: dict = {
            "teamId": team_id,
            "title": title,
            "description": description,
            "priority": priority,
        }
        if assignee_id is not None:
            input_vars["assigneeId"] = assignee_id
        if label_ids is not None:
            input_vars["labelIds"] = label_ids

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                LINEAR_API_URL,
                headers=headers,
                json={"query": mutation, "variables": {"input": input_vars}},
            )
            resp.raise_for_status()
            data = resp.json()

        if "errors" in data:
            msg = data["errors"][0].get("message", "GraphQL error")
            raise ToolError(f"Linear API error: {msg}")

        result = data.get("data", {}).get("issueCreate", {})
        issue = result.get("issue") or {}
        logger.info(f"[Linear] Created issue '{title}' for client_id={client_id}")
        return {
            "success": result.get("success"),
            "issue_id": issue.get("id"),
            "title": issue.get("title"),
            "url": issue.get("url"),
            "state": (issue.get("state") or {}).get("name"),
        }
    except ToolError:
        raise
    except Exception as e:
        logger.exception(f"[Linear] Error creating issue: {e}")
        raise ToolError(f"Erro ao criar issue no Linear: {e}")


async def _linear_update_issue_logic(
    issue_id: str,
    title: str | None = None,
    description: str | None = None,
    priority: int | None = None,
    state_id: str | None = None,
    assignee_id: str | None = None,
    ctx: Context = None,
    client_id: str | None = None,
) -> dict:
    """
    Atualiza uma issue no Linear.

    Args:
        issue_id: ID da issue
        title: Novo título (opcional)
        description: Nova descrição (opcional)
        priority: Nova prioridade (opcional)
        state_id: ID do novo estado (opcional)
        assignee_id: ID do novo responsável (opcional)

    Returns:
        Dict com {success, issue_id, title, url, state}
    """
    if not issue_id:
        raise ToolError("issue_id é obrigatório.")
    try:
        token = await _get_linear_token(client_id)
        headers = {"Authorization": token, "Content-Type": "application/json"}
        mutation = """
        mutation UpdateIssue($id: String!, $input: IssueUpdateInput!) {
            issueUpdate(id: $id, input: $input) {
                success
                issue { id title url state { name } }
            }
        }
        """
        input_vars: dict = {}
        if title is not None:
            input_vars["title"] = title
        if description is not None:
            input_vars["description"] = description
        if priority is not None:
            input_vars["priority"] = priority
        if state_id is not None:
            input_vars["stateId"] = state_id
        if assignee_id is not None:
            input_vars["assigneeId"] = assignee_id

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                LINEAR_API_URL,
                headers=headers,
                json={"query": mutation, "variables": {"id": issue_id, "input": input_vars}},
            )
            resp.raise_for_status()
            data = resp.json()

        if "errors" in data:
            msg = data["errors"][0].get("message", "GraphQL error")
            raise ToolError(f"Linear API error: {msg}")

        result = data.get("data", {}).get("issueUpdate", {})
        issue = result.get("issue") or {}
        logger.info(f"[Linear] Updated issue {issue_id} for client_id={client_id}")
        return {
            "success": result.get("success"),
            "issue_id": issue.get("id"),
            "title": issue.get("title"),
            "url": issue.get("url"),
            "state": (issue.get("state") or {}).get("name"),
        }
    except ToolError:
        raise
    except Exception as e:
        logger.exception(f"[Linear] Error updating issue: {e}")
        raise ToolError(f"Erro ao atualizar issue {issue_id}: {e}")


async def _linear_add_comment_logic(
    issue_id: str,
    body: str,
    ctx: Context = None,
    client_id: str | None = None,
) -> dict:
    """
    Adiciona um comentário a uma issue do Linear.

    Args:
        issue_id: ID da issue
        body: Texto do comentário

    Returns:
        Dict com {success, comment_id, body, created_at}
    """
    if not issue_id or not body:
        raise ToolError("issue_id e body são obrigatórios.")
    try:
        token = await _get_linear_token(client_id)
        headers = {"Authorization": token, "Content-Type": "application/json"}
        mutation = """
        mutation CreateComment($input: CommentCreateInput!) {
            commentCreate(input: $input) {
                success
                comment { id body createdAt }
            }
        }
        """
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                LINEAR_API_URL,
                headers=headers,
                json={"query": mutation, "variables": {"input": {"issueId": issue_id, "body": body}}},
            )
            resp.raise_for_status()
            data = resp.json()

        if "errors" in data:
            msg = data["errors"][0].get("message", "GraphQL error")
            raise ToolError(f"Linear API error: {msg}")

        result = data.get("data", {}).get("commentCreate", {})
        comment = result.get("comment") or {}
        logger.info(f"[Linear] Added comment to issue {issue_id}, client_id={client_id}")
        return {
            "success": result.get("success"),
            "comment_id": comment.get("id"),
            "body": comment.get("body"),
            "created_at": comment.get("createdAt"),
        }
    except ToolError:
        raise
    except Exception as e:
        logger.exception(f"[Linear] Error adding comment: {e}")
        raise ToolError(f"Erro ao adicionar comentário na issue {issue_id}: {e}")


async def _linear_list_cycles_logic(
    team_id: str,
    ctx: Context = None,
    client_id: str | None = None,
) -> dict:
    """
    Lista cycles (sprints) de um time do Linear.

    Args:
        team_id: ID do time

    Returns:
        Dict com {cycles: [{id, name, number, starts_at, ends_at, progress, issue_count, issues}]}
    """
    if not team_id:
        raise ToolError("team_id é obrigatório.")
    try:
        token = await _get_linear_token(client_id)
        headers = {"Authorization": token, "Content-Type": "application/json"}
        query = f"""
        {{
            cycles(filter: {{ team: {{ id: {{ eq: "{team_id}" }} }} }}) {{
                nodes {{
                    id
                    name
                    number
                    startsAt
                    endsAt
                    completedAt
                    progress
                    issues {{
                        nodes {{
                            id
                            title
                            state {{ name }}
                        }}
                    }}
                }}
            }}
        }}
        """
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(LINEAR_API_URL, headers=headers, json={"query": query})
            resp.raise_for_status()
            data = resp.json()

        if "errors" in data:
            msg = data["errors"][0].get("message", "GraphQL error")
            raise ToolError(f"Linear API error: {msg}")

        nodes = data.get("data", {}).get("cycles", {}).get("nodes", [])
        cycles = []
        for c in nodes:
            issue_nodes = (c.get("issues") or {}).get("nodes", [])
            cycles.append({
                "id": c.get("id"),
                "name": c.get("name"),
                "number": c.get("number"),
                "starts_at": c.get("startsAt"),
                "ends_at": c.get("endsAt"),
                "progress": c.get("progress"),
                "issue_count": len(issue_nodes),
                "issues": [
                    {
                        "id": i.get("id"),
                        "title": i.get("title"),
                        "state": (i.get("state") or {}).get("name"),
                    }
                    for i in issue_nodes
                ],
            })

        logger.info(f"[Linear] Listed {len(cycles)} cycles for team {team_id}, client_id={client_id}")
        return {"cycles": cycles}
    except ToolError:
        raise
    except Exception as e:
        logger.exception(f"[Linear] Error listing cycles: {e}")
        raise ToolError(f"Erro ao listar cycles do time {team_id}: {e}")


# =============================================================================
# REGISTRO DO MÓDULO
# =============================================================================


@register_module
def register_tools(mcp: FastMCP) -> list[str]:
    """Registra as tools do módulo de Gestão de Projetos (Asana, ClickUp, Linear)."""

    mcp.tool(
        name="asana_list_projects",
        description=(
            "Lista projetos do Asana do cliente. "
            "Parâmetros: workspace_id (string, opcional — usa o primeiro workspace disponível). "
            "Retorna id, nome, status, due_on, owner e prévia das notas de cada projeto."
        ),
    )(mcp_inject_client_id(get_context_service)(_asana_list_projects_logic))

    mcp.tool(
        name="asana_get_project_tasks",
        description=(
            "Lista tarefas de um projeto do Asana. "
            "Parâmetros: project_id (string, obrigatório), completed (bool, padrão False). "
            "Retorna total e lista de tarefas com assignee, prazo e prévia das notas."
        ),
    )(mcp_inject_client_id(get_context_service)(_asana_get_project_tasks_logic))

    mcp.tool(
        name="clickup_list_tasks",
        description=(
            "Lista tarefas de uma lista do ClickUp. "
            "Parâmetros: list_id (string, obrigatório), status (string, opcional). "
            "Retorna total e lista de tarefas com status, assignee, data e descrição."
        ),
    )(mcp_inject_client_id(get_context_service)(_clickup_list_tasks_logic))

    mcp.tool(
        name="clickup_get_task_comments",
        description=(
            "Lista comentários de uma tarefa do ClickUp. "
            "Parâmetros: task_id (string, obrigatório). "
            "Retorna lista de comentários com texto, usuário e data."
        ),
    )(mcp_inject_client_id(get_context_service)(_clickup_get_task_comments_logic))

    mcp.tool(
        name="linear_list_issues",
        description=(
            "Lista issues do Linear. "
            "Parâmetros: team_id (string, opcional), status (string, opcional), limit (int, padrão 30). "
            "Retorna total e lista de issues com prioridade, estado, assignee e projeto."
        ),
    )(mcp_inject_client_id(get_context_service)(_linear_list_issues_logic))

    mcp.tool(
        name="linear_get_project_summary",
        description=(
            "Retorna resumo completo de um projeto do Linear com progresso, membros e issues. "
            "Parâmetros: project_id (string, obrigatório). "
            "Retorna progresso (%), estado, membros, contagem por estado e issues em atraso."
        ),
    )(mcp_inject_client_id(get_context_service)(_linear_get_project_summary_logic))

    mcp.tool(
        name="asana_create_task",
        description=(
            "Cria uma tarefa no Asana. "
            "Parâmetros: workspace_gid (string, obrigatório), name (string, obrigatório), "
            "notes (string, opcional), assignee_gid (string, opcional), due_on (YYYY-MM-DD, opcional), "
            "project_gid (string, opcional), parent_gid (string, opcional), "
            "resource_subtype (string, padrão default_task). "
            "Retorna gid, name e permalink_url da tarefa criada."
        ),
    )(mcp_inject_client_id(get_context_service)(_asana_create_task_logic))

    mcp.tool(
        name="asana_update_task",
        description=(
            "Atualiza uma tarefa existente no Asana. "
            "Parâmetros: task_gid (string, obrigatório), name (string, opcional), "
            "notes (string, opcional), completed (bool, opcional), "
            "assignee_gid (string, opcional), due_on (YYYY-MM-DD, opcional). "
            "Retorna gid, name, completed e permalink_url."
        ),
    )(mcp_inject_client_id(get_context_service)(_asana_update_task_logic))

    mcp.tool(
        name="asana_get_task_stories",
        description=(
            "Lista comentários de uma tarefa do Asana. "
            "Parâmetros: task_gid (string, obrigatório), limit (int, padrão 30). "
            "Retorna total e lista de comentários com texto, autor e data."
        ),
    )(mcp_inject_client_id(get_context_service)(_asana_get_task_stories_logic))

    mcp.tool(
        name="asana_add_task_comment",
        description=(
            "Adiciona um comentário a uma tarefa do Asana. "
            "Parâmetros: task_gid (string, obrigatório), text (string, obrigatório). "
            "Retorna story_gid, text e created_at."
        ),
    )(mcp_inject_client_id(get_context_service)(_asana_add_task_comment_logic))

    mcp.tool(
        name="asana_search_tasks",
        description=(
            "Busca tarefas em um workspace do Asana com filtros. "
            "Parâmetros: workspace_gid (string, obrigatório), text (string, opcional), "
            "assignee_gid (string, opcional), project_gid (string, opcional), "
            "completed (bool, padrão False), limit (int, padrão 20). "
            "Retorna total e lista de tarefas com assignee, prazo e URL."
        ),
    )(mcp_inject_client_id(get_context_service)(_asana_search_tasks_logic))

    mcp.tool(
        name="linear_list_teams",
        description=(
            "Lista todos os times do Linear. "
            "Sem parâmetros obrigatórios. "
            "Retorna lista de times com id, name, key, description e member_count."
        ),
    )(mcp_inject_client_id(get_context_service)(_linear_list_teams_logic))

    mcp.tool(
        name="linear_create_issue",
        description=(
            "Cria uma issue no Linear. "
            "Parâmetros: team_id (string, obrigatório), title (string, obrigatório), "
            "description (string, opcional), priority (int 0-4, padrão 0), "
            "assignee_id (string, opcional), label_ids (list, opcional). "
            "Retorna success, issue_id, title, url e state."
        ),
    )(mcp_inject_client_id(get_context_service)(_linear_create_issue_logic))

    mcp.tool(
        name="linear_update_issue",
        description=(
            "Atualiza uma issue existente no Linear. "
            "Parâmetros: issue_id (string, obrigatório), title (string, opcional), "
            "description (string, opcional), priority (int, opcional), "
            "state_id (string, opcional), assignee_id (string, opcional). "
            "Retorna success, issue_id, title, url e state."
        ),
    )(mcp_inject_client_id(get_context_service)(_linear_update_issue_logic))

    mcp.tool(
        name="linear_add_comment",
        description=(
            "Adiciona um comentário a uma issue do Linear. "
            "Parâmetros: issue_id (string, obrigatório), body (string, obrigatório). "
            "Retorna success, comment_id, body e created_at."
        ),
    )(mcp_inject_client_id(get_context_service)(_linear_add_comment_logic))

    mcp.tool(
        name="linear_list_cycles",
        description=(
            "Lista cycles (sprints) de um time do Linear. "
            "Parâmetros: team_id (string, obrigatório). "
            "Retorna lista de cycles com datas, progresso e issues associadas."
        ),
    )(mcp_inject_client_id(get_context_service)(_linear_list_cycles_logic))

    registered = [
        "asana_list_projects",
        "asana_get_project_tasks",
        "asana_create_task",
        "asana_update_task",
        "asana_get_task_stories",
        "asana_add_task_comment",
        "asana_search_tasks",
        "clickup_list_tasks",
        "clickup_get_task_comments",
        "linear_list_issues",
        "linear_get_project_summary",
        "linear_list_teams",
        "linear_create_issue",
        "linear_update_issue",
        "linear_add_comment",
        "linear_list_cycles",
    ]
    logger.info(f"[PM Module] Tools registered: {registered}")
    return registered
