"""API routes for agent catalog, sessions, and chat."""

import json
import logging
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from standalone_agent_api.api.auth import AuthResult, get_admin_auth_result, get_auth_result
from standalone_agent_api.core.factory import get_factory
from standalone_agent_api.core.service import (
    CatalogService,
    CsvUploadService,
    SessionService,
    StandaloneAgentService,
    get_agent_service,
    get_catalog_service,
    get_csv_upload_service,
    get_session_service,
)

logger = logging.getLogger(__name__)
router = APIRouter()


# ============================================================================
# PYDANTIC MODELS
# ============================================================================


class AgentInfo(BaseModel):
    """Agent catalog entry."""

    id: str
    name: str
    slug: str
    description: str | None = None
    category: str | None = None
    icon: str | None = None
    tier_required: str = "BASIC"


class AgentDetailsResponse(BaseModel):
    """Full agent details with config."""

    id: str
    name: str
    slug: str
    description: str | None = None
    agent_config: dict
    prompt_name: str
    required_context: list | None = None
    required_files: dict | None = None
    requires_google: bool = False


class SessionResponse(BaseModel):
    """Session response."""

    id: str
    session_id: str
    config_status: str


class ChatRequest(BaseModel):
    """User message for agent chat."""

    message: str
    stream: bool = True


class CsvUploadResponse(BaseModel):
    """Response from CSV upload."""

    file_id: str
    file_name: str
    columns: list[dict]
    row_count: int
    sample_rows: list[dict] | None = None


class CreateSessionRequest(BaseModel):
    """Request body for session creation."""

    agent_catalog_id: UUID


# --- Admin / Builder Models ---


class CatalogAgentCreateRequest(BaseModel):
    """Request body for creating an agent catalog entry."""

    name: str
    description: str | None = None
    category: str | None = None
    icon: str | None = None
    agent_config: dict[str, Any] = Field(
        ..., description="AgentConfig-compatible dict: name, role, enabled_tools, max_turns, model, etc."
    )
    prompt_name: str
    required_context: list[dict[str, Any]] = Field(default_factory=list)
    required_files: dict[str, Any] = Field(default_factory=dict)
    requires_google: bool = False
    tier_required: str = "BASIC"
    is_active: bool = True
    workflow_graph: dict[str, Any] | None = None


class CatalogAgentUpdateRequest(BaseModel):
    """Request body for updating an agent catalog entry (partial)."""

    name: str | None = None
    description: str | None = None
    category: str | None = None
    icon: str | None = None
    agent_config: dict[str, Any] | None = None
    prompt_name: str | None = None
    required_context: list[dict[str, Any]] | None = None
    required_files: dict[str, Any] | None = None
    requires_google: bool | None = None
    tier_required: str | None = None
    is_active: bool | None = None
    workflow_graph: dict[str, Any] | None = None


class CatalogAgentResponse(BaseModel):
    """Full agent catalog entry for admin views."""

    id: str
    name: str
    slug: str
    description: str | None = None
    category: str | None = None
    icon: str | None = None
    agent_config: dict[str, Any]
    prompt_name: str
    required_context: list[dict[str, Any]] = []
    required_files: dict[str, Any] = {}
    requires_google: bool = False
    tier_required: str = "BASIC"
    is_active: bool = True
    workflow_graph: dict[str, Any] | None = None
    created_at: str | None = None
    updated_at: str | None = None


class ValidateToolsRequest(BaseModel):
    """Request body for tool validation."""

    enabled_tools: list[str]
    tier: str = "BASIC"


class ValidateToolsResponse(BaseModel):
    """Response from tool validation."""

    valid: bool
    errors: list[str] = []
    warnings: list[str] = []


class PromptInfo(BaseModel):
    """Prompt listing entry."""

    name: str
    source: str  # "langfuse" or "builtin"
    category: str | None = None
    description: str | None = None


class PromptDetailResponse(BaseModel):
    """Full prompt content."""

    name: str
    content: str
    version: int
    variables: list[str] = []
    source: str  # "langfuse" or "builtin"


class PromptUpdateRequest(BaseModel):
    """Request body for updating a prompt (creates new version)."""

    content: str


class PromptVersionInfo(BaseModel):
    """A single prompt version entry."""

    version: int
    created_at: str | None = None
    labels: list[str] = []


class PromptVersionsResponse(BaseModel):
    """List of prompt versions."""

    name: str
    versions: list[PromptVersionInfo] = []


# ============================================================================
# CATALOG ROUTES
# ============================================================================


@router.get("/catalog/nodes")
async def list_catalog_nodes(
    auth_result: AuthResult = Depends(get_admin_auth_result),
):
    """List available node types from NodeRegistry with metadata."""
    from vizu_agent_framework.nodes import NodeRegistry

    nodes = NodeRegistry.list_nodes_with_metadata()
    return nodes


@router.get("/catalog/agents", response_model=list[AgentInfo])
async def list_agents(
    client_tier: str = Query("BASIC"),
):
    """List active agents filtered by client tier."""
    catalog_service = get_catalog_service()

    try:
        agents = await catalog_service.list_agents(client_tier=client_tier)
        return [
            AgentInfo(
                id=a.get("id"),
                name=a.get("name"),
                slug=a.get("slug"),
                description=a.get("description"),
                category=a.get("category"),
                icon=a.get("icon"),
                tier_required=a.get("tier_required", "BASIC"),
            )
            for a in agents
        ]
    except Exception as e:
        logger.error(f"Error listing agents: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/catalog/agents/admin", response_model=list[CatalogAgentResponse])
async def list_agents_admin(
    auth_result: AuthResult = Depends(get_admin_auth_result),
):
    """List all agents (including inactive) for admin views."""
    catalog_service = get_catalog_service()

    try:
        agents = await catalog_service.list_agents_admin()
        return [CatalogAgentResponse(**a) for a in agents]
    except Exception as e:
        logger.error(f"Error listing agents (admin): {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/catalog/agents/admin/{agent_id}", response_model=CatalogAgentResponse)
async def get_agent_admin(
    agent_id: UUID,
    auth_result: AuthResult = Depends(get_admin_auth_result),
):
    """Get full agent details for admin editing (includes workflow_graph)."""
    catalog_service = get_catalog_service()

    try:
        agent = await catalog_service.get_agent_admin(agent_id)
        return CatalogAgentResponse(**agent)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error getting agent (admin): {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/catalog/agents/{agent_id}", response_model=AgentDetailsResponse)
async def get_agent(
    agent_id: UUID,
):
    """Get agent details with full config."""
    logger.info(f"get_agent called with agent_id={agent_id}")
    catalog_service = get_catalog_service()

    try:
        agent = await catalog_service.get_agent(agent_id)
        return AgentDetailsResponse(
            id=agent.get("id"),
            name=agent.get("name"),
            slug=agent.get("slug"),
            description=agent.get("description"),
            agent_config=agent.get("agent_config", {}),
            prompt_name=agent.get("prompt_name"),
            required_context=agent.get("required_context"),
            required_files=agent.get("required_files"),
            requires_google=agent.get("requires_google", False),
        )
    except ValueError as e:
        logger.warning(f"Agent not found: {agent_id} — {e}")
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error getting agent: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# SESSION ROUTES
# ============================================================================


@router.post("/sessions")
async def create_session(
    body: CreateSessionRequest,
    auth_result: AuthResult = Depends(get_auth_result),
    session_service: SessionService = Depends(get_session_service),
):
    """Create new standalone agent session."""

    try:
        session = await session_service.create_session(
            client_id=auth_result.client_id,
            agent_catalog_id=body.agent_catalog_id,
        )
        return session
    except Exception as e:
        logger.error(f"Error creating session: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sessions")
async def list_sessions(
    auth_result: AuthResult = Depends(get_auth_result),
    status: str = Query(None),
    session_service: SessionService = Depends(get_session_service),
):
    """List user sessions, optionally filtered by status."""

    try:
        sessions = await session_service.list_sessions(
            client_id=auth_result.client_id,
            status=status,
        )
        return sessions
    except Exception as e:
        logger.error(f"Error listing sessions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sessions/{session_id}")
async def get_session(
    session_id: str,
    auth_result: AuthResult = Depends(get_auth_result),
    session_service: SessionService = Depends(get_session_service),
):
    """Get session status and config progress."""

    try:
        session = await session_service.get_session(
            client_id=auth_result.client_id,
            session_id=session_id,
        )
        return session
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error getting session: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sessions/{session_id}/activate")
async def activate_session(
    session_id: str,
    auth_result: AuthResult = Depends(get_auth_result),
    session_service: SessionService = Depends(get_session_service),
):
    """Activate session (transition to 'active' status)."""

    try:
        result = await session_service.activate_session(
            client_id=auth_result.client_id,
            session_id=session_id,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error activating session: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# CSV UPLOAD ROUTES
# ============================================================================


@router.post("/sessions/{session_id}/csv", response_model=CsvUploadResponse)
async def upload_csv(
    session_id: str,
    auth_result: AuthResult = Depends(get_auth_result),
    file: UploadFile = File(...),
    csv_service: CsvUploadService = Depends(get_csv_upload_service),
):
    """Upload CSV file to session."""

    try:
        # Validate file type
        if not file.filename.endswith((".csv", ".xlsx")):
            raise HTTPException(status_code=400, detail="Only CSV and XLSX files allowed")

        # Read file into BytesIO for pandas + storage
        import io
        content = await file.read()
        file_stream = io.BytesIO(content)

        # Upload
        metadata = await csv_service.upload_csv(
            session_id=session_id,
            client_id=auth_result.client_id,
            file_stream=file_stream,
            file_name=file.filename,
        )

        return CsvUploadResponse(
            file_id=str(metadata.get("file_id", "")),
            file_name=metadata.get("file_name"),
            columns=metadata.get("columns", []),
            row_count=metadata.get("row_count", 0),
            sample_rows=metadata.get("sample_rows"),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading CSV: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        # Invalidate cached agent so next invocation picks up new CSV
        get_factory().clear_session_cache(session_id)


@router.get("/sessions/{session_id}/csvs")
async def list_session_csvs(
    session_id: str,
    csv_service: CsvUploadService = Depends(get_csv_upload_service),
):
    """List CSV files uploaded to session."""

    try:
        csvs = await csv_service.list_session_csvs(session_id=session_id)
        return csvs
    except Exception as e:
        logger.error(f"Error listing CSVs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# GOOGLE INTEGRATION ROUTES
# ============================================================================
# NOTE: OAuth initiation and account listing are handled by tool_pool_api
# (integrations_router.py). The frontend calls tool_pool_api directly for:
#   - POST /integrations/google/auth/initiate
#   - GET  /integrations/google/accounts
# This router only handles session-level linking.


@router.patch("/sessions/{session_id}/google")
async def link_google_account(
    session_id: str,
    auth_result: AuthResult = Depends(get_auth_result),
    email: str = Query(...),
    session_service: SessionService = Depends(get_session_service),
):
    """Link Google account to session."""

    try:
        result = await session_service.link_google_account(
            client_id=auth_result.client_id,
            session_id=session_id,
            email=email,
        )
        return result
    except Exception as e:
        logger.error(f"Error linking Google account: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# CHAT ROUTES
# ============================================================================


@router.post("/sessions/{session_id}/chat/config")
async def chat_config_helper(
    session_id: str,
    auth_result: AuthResult = Depends(get_auth_result),
    request: ChatRequest = None,
    agent_service: StandaloneAgentService = Depends(get_agent_service),
):
    """
    Chat with config helper agent to guide config collection.

    Streams responses as SSE for real-time UI updates.
    """

    if request is None:
        request = ChatRequest(message="Start", stream=True)

    # Get the session to find its agent_catalog_id
    session_service = get_session_service()
    try:
        session = await session_service.get_session(
            client_id=auth_result.client_id,
            session_id=session_id,
        )
    except ValueError:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")

    agent_catalog_id = UUID(session["agent_catalog_id"])

    async def stream_events():
        """Stream events from config helper agent."""
        try:
            async for event in agent_service.stream_agent_response(
                session_id=session_id,
                client_id=auth_result.client_id,
                agent_catalog_id=agent_catalog_id,
                user_message=request.message,
            ):
                # Yield SSE format
                yield f"data: {json.dumps(event, default=str)}\n\n"

        except Exception as e:
            logger.error(f"Error streaming config helper: {e}", exc_info=True)
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(stream_events(), media_type="text/event-stream")


@router.post("/sessions/{session_id}/chat/agent")
async def chat_agent(
    session_id: str,
    agent_slug: str = Query(...),
    auth_result: AuthResult = Depends(get_auth_result),
    request: ChatRequest = None,
    agent_service: StandaloneAgentService = Depends(get_agent_service),
):
    """
    Chat with the configured standalone agent (data analyst, knowledge assistant, etc).

    Streams responses as SSE.
    """

    if request is None:
        raise HTTPException(status_code=400, detail="Message required")

    # Look up agent by slug
    from vizu_supabase_client import get_supabase_client

    db = get_supabase_client()

    catalog_result = db.table("agent_catalog").select("id").eq(
        "slug", agent_slug
    ).maybe_single().execute()

    if not catalog_result.data:
        raise HTTPException(status_code=404, detail=f"Agent {agent_slug} not found")

    agent_catalog_id = UUID(catalog_result.data["id"])

    async def stream_events():
        """Stream events from agent."""
        try:
            async for event in agent_service.stream_agent_response(
                session_id=session_id,
                client_id=auth_result.client_id,
                agent_catalog_id=agent_catalog_id,
                user_message=request.message,
            ):
                # Yield SSE format
                yield f"data: {json.dumps(event, default=str)}\n\n"

        except Exception as e:
            logger.error(f"Error streaming agent: {e}", exc_info=True)
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(stream_events(), media_type="text/event-stream")


# ============================================================================
# SESSION CONFIG ROUTES
# ============================================================================


class ConfigFieldUpdate(BaseModel):
    """Request body for config field update."""
    value: str | bool


@router.post("/sessions/{session_id}/config/finalize")
async def finalize_config(
    session_id: str,
    auth_result: AuthResult = Depends(get_auth_result),
    session_service: SessionService = Depends(get_session_service),
):
    """Finalize configuration and mark session as ready."""

    try:
        session = await session_service.finalize_session(
            client_id=auth_result.client_id,
            session_id=session_id,
        )
        # Invalidate cached agent so it rebuilds with finalized config
        get_factory().clear_session_cache(session_id)
        return session
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error finalizing config: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sessions/{session_id}/config/{field_name}")
async def update_session_config(
    session_id: str,
    field_name: str,
    body: ConfigFieldUpdate,
    auth_result: AuthResult = Depends(get_auth_result),
    session_service: SessionService = Depends(get_session_service),
):
    """Update a session config field directly."""

    try:
        context_update = {field_name: body.value}
        collected_context = await session_service.update_collected_context(
            client_id=auth_result.client_id,
            session_id=session_id,
            context_update=context_update,
        )
        # Invalidate cached agent so it rebuilds with updated context
        get_factory().clear_session_cache(session_id)
        return {"updated": field_name, "value": body.value, "context": collected_context}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating config: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# ADMIN — CATALOG CRUD ROUTES
# ============================================================================


@router.post("/catalog/agents", response_model=CatalogAgentResponse, status_code=201)
async def create_catalog_agent(
    body: CatalogAgentCreateRequest,
    auth_result: AuthResult = Depends(get_admin_auth_result),
):
    """Create a new agent catalog entry. Validates agent_config against AgentConfig dataclass."""
    catalog_service = get_catalog_service()

    try:
        agent = await catalog_service.create_agent(body.model_dump())
        return CatalogAgentResponse(**agent)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating agent: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/catalog/agents/{agent_id}", response_model=CatalogAgentResponse)
async def update_catalog_agent(
    agent_id: UUID,
    body: CatalogAgentUpdateRequest,
    auth_result: AuthResult = Depends(get_admin_auth_result),
):
    """Update an existing agent catalog entry."""
    catalog_service = get_catalog_service()

    try:
        # Only send non-None fields
        update_data = body.model_dump(exclude_none=True)
        if not update_data:
            raise HTTPException(status_code=400, detail="No fields to update")

        agent = await catalog_service.update_agent(agent_id, update_data)
        return CatalogAgentResponse(**agent)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating agent: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/catalog/agents/{agent_id}", response_model=CatalogAgentResponse)
async def delete_catalog_agent(
    agent_id: UUID,
    auth_result: AuthResult = Depends(get_admin_auth_result),
):
    """Soft-delete an agent (set is_active=false). Preserves session references."""
    catalog_service = get_catalog_service()

    try:
        agent = await catalog_service.soft_delete_agent(agent_id)
        return CatalogAgentResponse(**agent)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error deleting agent: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/catalog/agents/{agent_id}/duplicate", response_model=CatalogAgentResponse, status_code=201)
async def duplicate_catalog_agent(
    agent_id: UUID,
    auth_result: AuthResult = Depends(get_admin_auth_result),
):
    """Clone an agent with a new slug. The copy starts as inactive."""
    catalog_service = get_catalog_service()

    try:
        agent = await catalog_service.duplicate_agent(agent_id)
        return CatalogAgentResponse(**agent)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error duplicating agent: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# ADMIN — TOOL VALIDATION
# ============================================================================


@router.post("/catalog/validate-tools", response_model=ValidateToolsResponse)
async def validate_tools(
    body: ValidateToolsRequest,
    auth_result: AuthResult = Depends(get_admin_auth_result),
):
    """Validate enabled_tools against tier using ToolRegistry."""
    from vizu_tool_registry import ToolRegistry

    is_valid, errors = ToolRegistry.validate_client_tools(
        enabled_tools=body.enabled_tools,
        tier=body.tier,
    )

    # Also generate warnings for tools that require confirmation
    warnings = []
    for tool_name in body.enabled_tools:
        tool = ToolRegistry.get_tool(tool_name)
        if tool and tool.requires_confirmation:
            warnings.append(f"{tool_name} requires user confirmation before execution")

    return ValidateToolsResponse(valid=is_valid, errors=errors, warnings=warnings)


# ============================================================================
# ADMIN — PROMPT LISTING
# ============================================================================


@router.get("/catalog/prompts", response_model=list[PromptInfo])
async def list_prompts(
    auth_result: AuthResult = Depends(get_admin_auth_result),
):
    """List available prompt names from builtin templates + Langfuse."""
    from vizu_prompt_management import PromptLoader
    from vizu_prompt_management.templates import BUILTIN_TEMPLATES

    prompts: list[PromptInfo] = []

    # 1. Builtin templates
    for name, config in BUILTIN_TEMPLATES.items():
        prompts.append(PromptInfo(
            name=name,
            source="builtin",
            category=config.category.value if config.category else None,
            description=config.description,
        ))

    # 2. Langfuse prompts (best-effort — don't fail if Langfuse is down)
    try:
        loader = PromptLoader()
        client = loader._get_langfuse_client()
        if client:
            from langfuse import Langfuse

            lf = Langfuse()
            lf_prompts = lf.client.prompts.list()
            existing_names = {p.name for p in prompts}

            for p in lf_prompts.data:
                if p.name not in existing_names:
                    prompts.append(PromptInfo(
                        name=p.name,
                        source="langfuse",
                        category=None,
                        description=None,
                    ))
    except Exception as e:
        logger.warning(f"Could not list Langfuse prompts: {e}")

    return prompts


# ============================================================================
# ADMIN — PROMPT DETAIL / EDIT / VERSIONS
# ============================================================================


def _extract_variables(content: str) -> list[str]:
    """Extract {{variable}} names from prompt content."""
    import re

    return sorted(set(re.findall(r"\{\{(\w+)\}\}", content)))


@router.get("/catalog/prompts/{prompt_name:path}", response_model=PromptDetailResponse)
async def get_prompt_detail(
    prompt_name: str,
    auth_result: AuthResult = Depends(get_admin_auth_result),
):
    """Fetch full prompt content by name (label=production) from Langfuse or builtin."""
    from vizu_prompt_management.templates import BUILTIN_TEMPLATES

    # Try builtin first
    if prompt_name in BUILTIN_TEMPLATES:
        tpl = BUILTIN_TEMPLATES[prompt_name]
        content = tpl.template if hasattr(tpl, "template") else str(tpl)
        return PromptDetailResponse(
            name=prompt_name,
            content=content,
            version=1,
            variables=_extract_variables(content),
            source="builtin",
        )

    # Try Langfuse
    try:
        from langfuse import Langfuse

        lf = Langfuse()
        prompt = lf.get_prompt(prompt_name, label="production", type="text")
        content = prompt.prompt
        return PromptDetailResponse(
            name=prompt_name,
            content=content,
            version=prompt.version,
            variables=_extract_variables(content),
            source="langfuse",
        )
    except Exception as e:
        logger.error(f"Failed to fetch prompt '{prompt_name}': {e}")
        raise HTTPException(status_code=404, detail=f"Prompt '{prompt_name}' not found")


@router.put("/catalog/prompts/{prompt_name:path}", response_model=PromptDetailResponse)
async def update_prompt(
    prompt_name: str,
    body: PromptUpdateRequest,
    auth_result: AuthResult = Depends(get_admin_auth_result),
):
    """Create a new Langfuse prompt version with updated content. Auto-promotes to production label."""
    from vizu_prompt_management.templates import BUILTIN_TEMPLATES

    if prompt_name in BUILTIN_TEMPLATES:
        raise HTTPException(status_code=400, detail="Cannot edit builtin prompts. Duplicate to Langfuse first.")

    try:
        from langfuse import Langfuse

        lf = Langfuse()
        new_prompt = lf.create_prompt(
            name=prompt_name,
            prompt=body.content,
            type="text",
            labels=["production"],
        )
        content = new_prompt.prompt
        return PromptDetailResponse(
            name=prompt_name,
            content=content,
            version=new_prompt.version,
            variables=_extract_variables(content),
            source="langfuse",
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update prompt '{prompt_name}': {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update prompt: {e}")


@router.get("/catalog/prompts/{prompt_name:path}/versions", response_model=PromptVersionsResponse)
async def list_prompt_versions(
    prompt_name: str,
    auth_result: AuthResult = Depends(get_admin_auth_result),
):
    """List version history for a prompt from Langfuse."""
    from vizu_prompt_management.templates import BUILTIN_TEMPLATES

    if prompt_name in BUILTIN_TEMPLATES:
        return PromptVersionsResponse(
            name=prompt_name,
            versions=[PromptVersionInfo(version=1, created_at=None, labels=["production"])],
        )

    try:
        from langfuse import Langfuse

        lf = Langfuse()
        # Fetch all versions via the Langfuse API
        response = lf.client.prompts.list(name=prompt_name)
        versions: list[PromptVersionInfo] = []
        for p in response.data:
            versions.append(PromptVersionInfo(
                version=p.version,
                created_at=p.created_at.isoformat() if hasattr(p, "created_at") and p.created_at else None,
                labels=p.labels if hasattr(p, "labels") and p.labels else [],
            ))

        # Sort descending by version
        versions.sort(key=lambda v: v.version, reverse=True)

        return PromptVersionsResponse(name=prompt_name, versions=versions)
    except Exception as e:
        logger.error(f"Failed to list versions for prompt '{prompt_name}': {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list prompt versions: {e}")
