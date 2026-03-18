"""API routes for agent catalog, sessions, and chat."""

import json
import logging
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from standalone_agent_api.api.auth import AuthResult, get_auth_result
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


# ============================================================================
# CATALOG ROUTES
# ============================================================================


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
        return {"updated": field_name, "value": body.value, "context": collected_context}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating config: {e}")
        raise HTTPException(status_code=500, detail=str(e))
