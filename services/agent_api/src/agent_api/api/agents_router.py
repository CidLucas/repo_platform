"""
Standalone agent endpoints — catalog, sessions, chat, CSV upload, admin.

User-facing routes  → GET/POST /v1/catalog/agents, /v1/sessions/...
Admin routes        → /v1/catalog/agents (CRUD), /v1/catalog/prompts, /v1/catalog/validate-tools
"""

import asyncio
import io
import json
import logging
import pathlib
import re
import unicodedata
from typing import Any
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import StreamingResponse

from agent_api.api.auth import AuthResult, get_admin_auth_result, get_auth_result
from agent_api.api.schemas import (
    AgentChatRequest,
    AgentDetailsResponse,
    AgentInfo,
    CatalogAgentCreateRequest,
    CatalogAgentResponse,
    CatalogAgentUpdateRequest,
    ConfigFieldUpdate,
    CreateSessionRequest,
    CsvUploadResponse,
    DocumentUploadResponse,
    LinkDocumentRequest,
    PromptDetailResponse,
    PromptInfo,
    PromptUpdateRequest,
    PromptVersionInfo,
    PromptVersionsResponse,
    ValidateToolsRequest,
    ValidateToolsResponse,
)
from agent_api.core.factory import get_context_service, get_factory
from agent_api.core.service import get_agent_service, get_chat_service
from blu_supabase_client import get_supabase_client

logger = logging.getLogger(__name__)
router = APIRouter()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _slugify(name: str) -> str:
    value = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("ascii")
    value = value.lower().strip()
    value = re.sub(r"[^\w\s-]", "", value)
    value = re.sub(r"[-\s]+", "-", value)
    return value.strip("-")


def _extract_variables(content: str) -> list[str]:
    return sorted(set(re.findall(r"\{\{(\w+)\}\}", content)))


_ALL_CATALOG_COLUMNS = (
    "id,name,slug,description,category,icon,"
    "agent_config,prompt_name,required_context,required_files,"
    "requires_google,tier_required,is_active,workflow_graph,created_at,updated_at"
)


# ---------------------------------------------------------------------------
# Catalog — user-facing
# ---------------------------------------------------------------------------


@router.get("/catalog/nodes")
async def list_catalog_nodes(auth_result: AuthResult = Depends(get_admin_auth_result)):
    """List available node types from NodeRegistry."""
    from blu_agent_framework.nodes import NodeRegistry
    return NodeRegistry.list_nodes_with_metadata()


@router.get("/catalog/agents", response_model=list[AgentInfo])
async def list_agents(client_tier: str = Query("BASIC")):
    """List active catalog agents accessible at *client_tier*."""
    db = get_supabase_client()
    result = db.table("agent_catalog").select(
        "id,name,slug,description,category,icon,tier_required"
    ).eq("is_active", True).execute()

    tier_order = {"BASIC": 0, "PRO": 1, "SME": 2, "ENTERPRISE": 3}
    client_level = tier_order.get(client_tier, 0)

    return [
        AgentInfo(**{k: a.get(k) for k in AgentInfo.model_fields})
        for a in result.data
        if tier_order.get(a.get("tier_required", "BASIC"), 0) <= client_level
    ]


@router.get("/catalog/agents/{agent_id}", response_model=AgentDetailsResponse)
async def get_agent(agent_id: UUID):
    """Get public agent details."""
    db = get_supabase_client()
    result = db.table("agent_catalog").select(
        "id,name,slug,description,agent_config,prompt_name,required_context,required_files,requires_google"
    ).eq("id", str(agent_id)).eq("is_active", True).execute()

    if not result.data:
        raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")
    return AgentDetailsResponse(**result.data[0])


# ---------------------------------------------------------------------------
# Sessions
# ---------------------------------------------------------------------------


@router.post("/sessions")
async def create_session(
    body: CreateSessionRequest,
    auth_result: AuthResult = Depends(get_auth_result),
):
    """Create a new standalone agent session."""
    db = get_supabase_client()
    session_id = str(uuid4())

    try:
        result = db.table("agent_sessions").insert({
            "id": session_id,
            "client_id": str(auth_result.client_id),
            "agent_catalog_id": str(body.agent_catalog_id),
            "status": "pending",
            "collected_context": {},
        }).execute()

        if not result.data:
            raise HTTPException(status_code=500, detail="Failed to create session")

        return result.data[0]
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Error creating session: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/sessions")
async def list_sessions(
    auth_result: AuthResult = Depends(get_auth_result),
    status: str = Query(None),
):
    """List user sessions."""
    db = get_supabase_client()
    query = db.table("agent_sessions").select(
        "id,status,agent_catalog_id,created_at,collected_context"
    ).eq("client_id", str(auth_result.client_id))

    if status:
        query = query.eq("status", status)

    result = query.order("created_at", desc=True).execute()
    return result.data or []


@router.get("/sessions/{session_id}")
async def get_session(
    session_id: str,
    auth_result: AuthResult = Depends(get_auth_result),
):
    """Get session details."""
    db = get_supabase_client()
    result = db.table("agent_sessions").select("*").eq(
        "id", session_id
    ).eq("client_id", str(auth_result.client_id)).execute()

    if not result.data:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
    return result.data[0]


@router.post("/sessions/{session_id}/activate")
async def activate_session(
    session_id: str,
    auth_result: AuthResult = Depends(get_auth_result),
):
    """Activate a session (pending → active)."""
    db = get_supabase_client()
    result = db.table("agent_sessions").update({"status": "active"}).eq(
        "id", session_id
    ).eq("client_id", str(auth_result.client_id)).execute()

    if not result.data:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
    return result.data[0]


# ---------------------------------------------------------------------------
# CSV upload
# ---------------------------------------------------------------------------


@router.post("/sessions/{session_id}/csv", response_model=CsvUploadResponse)
async def upload_csv(
    session_id: str,
    auth_result: AuthResult = Depends(get_auth_result),
    file: UploadFile = File(...),
):
    """Upload a CSV or XLSX file to the session."""
    if not file.filename.endswith((".csv", ".xlsx")):
        raise HTTPException(status_code=400, detail="Only CSV and XLSX files allowed")

    content = await file.read()
    file_stream = io.BytesIO(content)

    try:
        from blu_parsers.csv_ingestion import ingest_csv
        metadata = await ingest_csv(
            session_id=session_id,
            client_id=str(auth_result.client_id),
            file_stream=file_stream,
            file_name=file.filename,
        )
        get_factory().clear_session_cache(session_id)

        return CsvUploadResponse(
            file_id=str(metadata.get("file_id", "")),
            file_name=metadata.get("file_name", file.filename),
            columns=metadata.get("columns", []),
            row_count=metadata.get("row_count", 0),
            sample_rows=metadata.get("sample_rows"),
        )
    except Exception as exc:
        logger.error("Error uploading CSV: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/sessions/{session_id}/csvs")
async def list_session_csvs(session_id: str):
    """List CSV files uploaded to the session."""
    try:
        from blu_parsers.csv_ingestion import list_session_csvs as _list
        return await _list(session_id=session_id)
    except Exception as exc:
        logger.error("Error listing CSVs: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


# ---------------------------------------------------------------------------
# Document upload (PDF, TXT, DOCX, …)
# ---------------------------------------------------------------------------

_KNOWLEDGE_BASE_BUCKET = "knowledge-base"
_MAX_EMBEDDING_WAIT = 30
_EMBEDDING_POLL_INTERVAL = 0.5


@router.post("/sessions/{session_id}/documents", response_model=DocumentUploadResponse)
async def upload_document(
    session_id: str,
    auth_result: AuthResult = Depends(get_auth_result),
    file: UploadFile = File(...),
):
    """Upload a document file (PDF, TXT, DOCX, …) to a session's knowledge base."""
    allowed = (".txt", ".md", ".pdf", ".docx", ".doc")
    if not any(file.filename.endswith(ext) for ext in allowed):
        raise HTTPException(status_code=400, detail=f"Only {', '.join(allowed)} files allowed")

    content = await file.read()
    document_id = str(uuid4())
    file_type = pathlib.Path(file.filename).suffix.lstrip(".").lower()
    client_id_str = str(auth_result.client_id)

    try:
        from blu_supabase_client import get_storage
        storage = get_storage(bucket=_KNOWLEDGE_BASE_BUCKET)
        storage_path = f"{client_id_str}/{document_id}-{file.filename}"
        await asyncio.to_thread(storage.upload_file, content, storage_path)
    except Exception as exc:
        logger.error("Storage upload failed: %s", exc)
        raise HTTPException(status_code=500, detail=f"Storage upload failed: {exc}")

    db = get_supabase_client()
    try:
        db.schema("vector_db").table("documents").insert({
            "id": document_id,
            "client_id": client_id_str,
            "file_name": file.filename,
            "file_type": file_type,
            "storage_path": storage_path,
            "source": "upload",
            "processing_mode": "simple",
            "status": "processing",
            "scope": "client",
        }).execute()
    except Exception as exc:
        logger.error("DB insert failed: %s", exc)
        raise HTTPException(status_code=500, detail=f"Database error: {exc}")

    try:
        db.functions.invoke("process-document", invoke_options={"body": {
            "document_id": document_id,
            "storage_path": storage_path,
            "client_id": client_id_str,
            "file_name": file.filename,
            "file_type": file_type,
        }})
    except Exception as exc:
        logger.warning("process-document Edge Function failed: %s", exc)

    # Poll for embedding completion
    elapsed = 0.0
    final_status = "processing"
    while elapsed < _MAX_EMBEDDING_WAIT:
        r = db.schema("vector_db").table("documents").select("status").eq("id", document_id).execute()
        if r.data:
            final_status = r.data[0].get("status", "processing")
            if final_status in ("completed", "failed"):
                break
        await asyncio.sleep(_EMBEDDING_POLL_INTERVAL)
        elapsed += _EMBEDDING_POLL_INTERVAL

    # Link document to session
    sess = db.table("agent_sessions").select("uploaded_document_ids").eq("id", session_id).execute()
    if sess.data:
        ids: list = sess.data[0].get("uploaded_document_ids") or []
        if document_id not in ids:
            ids.append(document_id)
            db.table("agent_sessions").update({"uploaded_document_ids": ids}).eq("id", session_id).execute()

    get_factory().clear_session_cache(session_id)
    return DocumentUploadResponse(
        document_id=document_id,
        file_name=file.filename,
        status=final_status,
        size_bytes=len(content),
    )


@router.get("/sessions/{session_id}/documents")
async def list_session_documents(
    session_id: str,
    auth_result: AuthResult = Depends(get_auth_result),
):
    """List documents uploaded to the session."""
    db = get_supabase_client()
    sess = db.table("agent_sessions").select("uploaded_document_ids").eq(
        "id", session_id
    ).eq("client_id", str(auth_result.client_id)).execute()

    if not sess.data:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")

    ids: list = sess.data[0].get("uploaded_document_ids") or []
    if not ids:
        return []

    result = db.schema("vector_db").table("documents").select(
        "id,file_name,file_type,storage_path,status,created_at,updated_at"
    ).in_("id", ids).execute()
    return result.data or []


@router.post("/sessions/{session_id}/documents/link")
async def link_document(
    session_id: str,
    body: LinkDocumentRequest,
    auth_result: AuthResult = Depends(get_auth_result),
):
    """Link an existing document (uploaded via another flow) to this session."""
    db = get_supabase_client()
    sess = db.table("agent_sessions").select("uploaded_document_ids").eq(
        "id", session_id
    ).eq("client_id", str(auth_result.client_id)).execute()

    if not sess.data:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")

    ids: list = sess.data[0].get("uploaded_document_ids") or []
    if body.document_id not in ids:
        ids.append(body.document_id)
        db.table("agent_sessions").update({"uploaded_document_ids": ids}).eq("id", session_id).execute()

    get_factory().clear_session_cache(session_id)
    return {"session_id": session_id, "document_id": body.document_id, "linked": True}


# ---------------------------------------------------------------------------
# Google integration
# ---------------------------------------------------------------------------


@router.patch("/sessions/{session_id}/google")
async def link_google_account(
    session_id: str,
    email: str = Query(...),
    auth_result: AuthResult = Depends(get_auth_result),
):
    """Link a Google account to the session."""
    db = get_supabase_client()
    result = db.table("agent_sessions").update({
        "collected_context": {"google_email": email}
    }).eq("id", session_id).eq("client_id", str(auth_result.client_id)).execute()

    if not result.data:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")

    get_factory().clear_session_cache(session_id)
    return result.data[0]


# ---------------------------------------------------------------------------
# Chat — standalone agent
# ---------------------------------------------------------------------------


@router.post("/sessions/{session_id}/chat")
async def chat_agent(
    session_id: str,
    request: AgentChatRequest,
    auth_result: AuthResult = Depends(get_auth_result),
):
    """
    Chat with the configured standalone agent (streaming SSE).

    The agent type is resolved from the session's ``agent_catalog_id``.
    """
    db = get_supabase_client()
    sess_result = db.table("agent_sessions").select("agent_catalog_id").eq(
        "id", session_id
    ).eq("client_id", str(auth_result.client_id)).execute()

    if not sess_result.data:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")

    agent_catalog_id = UUID(sess_result.data[0]["agent_catalog_id"])
    service = get_agent_service()

    async def stream_events():
        try:
            async for event in service.stream_agent_response(
                session_id=session_id,
                client_id=auth_result.client_id,
                agent_catalog_id=agent_catalog_id,
                user_message=request.message,
            ):
                yield f"data: {json.dumps(event, default=str)}\n\n"
        except Exception as exc:
            logger.exception("Error streaming agent")
            yield f"data: {json.dumps({'event': 'error', 'message': str(exc)})}\n\n"

    return StreamingResponse(stream_events(), media_type="text/event-stream")


@router.post("/sessions/{session_id}/chat/agent")
async def chat_agent_run(
    session_id: str,
    request: AgentChatRequest,
    auth_result: AuthResult = Depends(get_auth_result),
):
    """Chat with the configured standalone agent (streaming SSE). Alias for /chat."""
    db = get_supabase_client()
    sess_result = db.table("agent_sessions").select("agent_catalog_id").eq(
        "id", session_id
    ).eq("client_id", str(auth_result.client_id)).execute()

    if not sess_result.data:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")

    agent_catalog_id = UUID(sess_result.data[0]["agent_catalog_id"])
    service = get_agent_service()

    async def stream_events():
        try:
            async for event in service.stream_agent_response(
                session_id=session_id,
                client_id=auth_result.client_id,
                agent_catalog_id=agent_catalog_id,
                user_message=request.message,
            ):
                yield f"data: {json.dumps(event, default=str)}\n\n"
        except Exception as exc:
            logger.exception("Error streaming agent")
            yield f"data: {json.dumps({'event': 'error', 'data': {'message': str(exc)}})}\n\n"

    return StreamingResponse(
        stream_events(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/sessions/{session_id}/chat/config")
async def chat_config_helper(
    session_id: str,
    request: AgentChatRequest,
    auth_result: AuthResult = Depends(get_auth_result),
):
    """Config helper chat — supervisor agent guides the user through session setup."""
    ctx_service = get_context_service()
    service = get_chat_service()

    async def event_generator():
        try:
            async for chunk in service.process_message_stream(
                session_id=f"config:{session_id}",
                message=request.message,
                client_id=auth_result.client_id,
                context_service=ctx_service,
            ):
                yield chunk
        except Exception as exc:
            logger.exception("Error in config helper")
            yield f"data: {json.dumps({'event': 'error', 'data': {'message': str(exc)}})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ---------------------------------------------------------------------------
# Session config
# ---------------------------------------------------------------------------


@router.post("/sessions/{session_id}/config/finalize")
async def finalize_config(
    session_id: str,
    auth_result: AuthResult = Depends(get_auth_result),
):
    """Finalize configuration and mark the session ready."""
    db = get_supabase_client()
    result = db.table("agent_sessions").update({"status": "active"}).eq(
        "id", session_id
    ).eq("client_id", str(auth_result.client_id)).execute()

    if not result.data:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")

    get_factory().clear_session_cache(session_id)
    return result.data[0]


@router.post("/sessions/{session_id}/config/{field_name}")
async def update_session_config(
    session_id: str,
    field_name: str,
    body: ConfigFieldUpdate,
    auth_result: AuthResult = Depends(get_auth_result),
):
    """Update a session config field."""
    db = get_supabase_client()

    # Read current context first, then merge
    current = db.table("agent_sessions").select("collected_context").eq(
        "id", session_id
    ).execute()
    if not current.data:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")

    ctx = dict(current.data[0].get("collected_context") or {})
    ctx[field_name] = body.value

    db.table("agent_sessions").update({"collected_context": ctx}).eq("id", session_id).execute()
    get_factory().clear_session_cache(session_id)

    return {"updated": field_name, "value": body.value, "context": ctx}


# ---------------------------------------------------------------------------
# Admin — catalog CRUD
# ---------------------------------------------------------------------------


@router.get("/catalog/agents/admin", response_model=list[CatalogAgentResponse])
async def list_agents_admin(auth_result: AuthResult = Depends(get_admin_auth_result)):
    db = get_supabase_client()
    result = db.table("agent_catalog").select(_ALL_CATALOG_COLUMNS).order(
        "created_at", desc=False
    ).execute()
    return [CatalogAgentResponse(**a) for a in (result.data or [])]


@router.get("/catalog/agents/admin/{agent_id}", response_model=CatalogAgentResponse)
async def get_agent_admin(
    agent_id: UUID,
    auth_result: AuthResult = Depends(get_admin_auth_result),
):
    db = get_supabase_client()
    result = db.table("agent_catalog").select(_ALL_CATALOG_COLUMNS).eq(
        "id", str(agent_id)
    ).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")
    return CatalogAgentResponse(**result.data[0])


@router.post("/catalog/agents", response_model=CatalogAgentResponse, status_code=201)
async def create_catalog_agent(
    body: CatalogAgentCreateRequest,
    auth_result: AuthResult = Depends(get_admin_auth_result),
):
    db = get_supabase_client()
    slug = _slugify(body.name)

    # Ensure slug uniqueness
    suffix = 1
    candidate = slug
    while True:
        r = db.table("agent_catalog").select("id").eq("slug", candidate).execute()
        if not r.data:
            slug = candidate
            break
        candidate = f"{slug}-{suffix}"
        suffix += 1

    row = {**body.model_dump(), "slug": slug}
    result = db.table("agent_catalog").insert(row).execute()
    if not result.data:
        raise HTTPException(status_code=500, detail="Failed to create agent")
    return CatalogAgentResponse(**result.data[0])


@router.put("/catalog/agents/{agent_id}", response_model=CatalogAgentResponse)
async def update_catalog_agent(
    agent_id: UUID,
    body: CatalogAgentUpdateRequest,
    auth_result: AuthResult = Depends(get_admin_auth_result),
):
    db = get_supabase_client()
    update_data = body.model_dump(exclude_none=True)
    if not update_data:
        raise HTTPException(status_code=400, detail="No fields to update")

    result = db.table("agent_catalog").update(update_data).eq(
        "id", str(agent_id)
    ).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")
    return CatalogAgentResponse(**result.data[0])


@router.delete("/catalog/agents/{agent_id}", response_model=CatalogAgentResponse)
async def delete_catalog_agent(
    agent_id: UUID,
    auth_result: AuthResult = Depends(get_admin_auth_result),
):
    """Soft-delete (set is_active=False)."""
    db = get_supabase_client()
    result = db.table("agent_catalog").update({"is_active": False}).eq(
        "id", str(agent_id)
    ).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")
    return CatalogAgentResponse(**result.data[0])


@router.post("/catalog/agents/{agent_id}/duplicate", response_model=CatalogAgentResponse, status_code=201)
async def duplicate_catalog_agent(
    agent_id: UUID,
    auth_result: AuthResult = Depends(get_admin_auth_result),
):
    """Clone an agent; copy starts as inactive."""
    db = get_supabase_client()
    original = db.table("agent_catalog").select(_ALL_CATALOG_COLUMNS).eq(
        "id", str(agent_id)
    ).execute()
    if not original.data:
        raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")

    data: dict = {k: v for k, v in original.data[0].items() if k not in ("id", "created_at", "updated_at")}
    data["is_active"] = False
    base_slug = data.get("slug", "agent")
    data["slug"] = f"{base_slug}-copy"
    data["name"] = f"{data.get('name', 'Agent')} (copy)"

    result = db.table("agent_catalog").insert(data).execute()
    if not result.data:
        raise HTTPException(status_code=500, detail="Failed to duplicate agent")
    return CatalogAgentResponse(**result.data[0])


# ---------------------------------------------------------------------------
# Admin — tool validation
# ---------------------------------------------------------------------------


@router.post("/catalog/validate-tools", response_model=ValidateToolsResponse)
async def validate_tools(
    body: ValidateToolsRequest,
    auth_result: AuthResult = Depends(get_admin_auth_result),
):
    from blu_tool_registry import ToolRegistry

    is_valid, errors = ToolRegistry.validate_client_tools(
        enabled_tools=body.enabled_tools, tier=body.tier
    )
    warnings = []
    for name in body.enabled_tools:
        t = ToolRegistry.get_tool(name)
        if t and t.requires_confirmation:
            warnings.append(f"{name} requires user confirmation before execution")

    return ValidateToolsResponse(valid=is_valid, errors=errors, warnings=warnings)


# ---------------------------------------------------------------------------
# Admin — prompt management
# ---------------------------------------------------------------------------


@router.get("/catalog/prompts", response_model=list[PromptInfo])
async def list_prompts(auth_result: AuthResult = Depends(get_admin_auth_result)):
    from blu_prompt_management.templates import BUILTIN_TEMPLATES

    prompts: list[PromptInfo] = [
        PromptInfo(
            name=name,
            source="builtin",
            category=getattr(cfg.category, "value", None) if hasattr(cfg, "category") else None,
            description=getattr(cfg, "description", None),
        )
        for name, cfg in BUILTIN_TEMPLATES.items()
    ]

    try:
        from langfuse import Langfuse
        lf = Langfuse()
        lf_prompts = lf.client.prompts.list()
        existing = {p.name for p in prompts}
        for p in lf_prompts.data:
            if p.name not in existing:
                prompts.append(PromptInfo(name=p.name, source="langfuse"))
    except Exception as exc:
        logger.warning("Could not list Langfuse prompts: %s", exc)

    return prompts


@router.get("/catalog/prompts/{prompt_name:path}", response_model=PromptDetailResponse)
async def get_prompt_detail(
    prompt_name: str,
    auth_result: AuthResult = Depends(get_admin_auth_result),
):
    from blu_prompt_management.templates import BUILTIN_TEMPLATES

    if prompt_name in BUILTIN_TEMPLATES:
        tpl = BUILTIN_TEMPLATES[prompt_name]
        content = tpl.template if hasattr(tpl, "template") else str(tpl)
        return PromptDetailResponse(
            name=prompt_name, content=content, version=1,
            variables=_extract_variables(content), source="builtin",
        )

    try:
        from langfuse import Langfuse
        lf = Langfuse()
        prompt = lf.get_prompt(prompt_name, label="production", type="text")
        return PromptDetailResponse(
            name=prompt_name, content=prompt.prompt, version=prompt.version,
            variables=_extract_variables(prompt.prompt), source="langfuse",
        )
    except Exception as exc:
        logger.error("Failed to fetch prompt '%s': %s", prompt_name, exc)
        raise HTTPException(status_code=404, detail=f"Prompt '{prompt_name}' not found")


@router.put("/catalog/prompts/{prompt_name:path}", response_model=PromptDetailResponse)
async def update_prompt(
    prompt_name: str,
    body: PromptUpdateRequest,
    auth_result: AuthResult = Depends(get_admin_auth_result),
):
    from blu_prompt_management.templates import BUILTIN_TEMPLATES

    if prompt_name in BUILTIN_TEMPLATES:
        raise HTTPException(status_code=400, detail="Cannot edit builtin prompts.")

    try:
        from langfuse import Langfuse
        lf = Langfuse()
        new_prompt = lf.create_prompt(
            name=prompt_name, prompt=body.content, type="text", labels=["production"]
        )
        return PromptDetailResponse(
            name=prompt_name, content=new_prompt.prompt, version=new_prompt.version,
            variables=_extract_variables(new_prompt.prompt), source="langfuse",
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to update prompt: {exc}")


@router.get("/catalog/prompts/{prompt_name:path}/versions", response_model=PromptVersionsResponse)
async def list_prompt_versions(
    prompt_name: str,
    auth_result: AuthResult = Depends(get_admin_auth_result),
):
    from blu_prompt_management.templates import BUILTIN_TEMPLATES

    if prompt_name in BUILTIN_TEMPLATES:
        return PromptVersionsResponse(
            name=prompt_name,
            versions=[PromptVersionInfo(version=1, labels=["production"])],
        )

    try:
        from langfuse import Langfuse
        lf = Langfuse()
        response = lf.client.prompts.list(name=prompt_name)
        versions = sorted(
            [
                PromptVersionInfo(
                    version=p.version,
                    created_at=p.created_at.isoformat() if getattr(p, "created_at", None) else None,
                    labels=getattr(p, "labels", []) or [],
                )
                for p in response.data
            ],
            key=lambda v: v.version,
            reverse=True,
        )
        return PromptVersionsResponse(name=prompt_name, versions=versions)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to list prompt versions: {exc}")
