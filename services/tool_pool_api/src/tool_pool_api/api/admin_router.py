"""
Admin API Router for Client Management.

Provides CRUD endpoints for managing cliente_blu records.
Protected by JWT authentication - requires ADMIN tier.
"""

import logging
from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field

from blu_auth.core.exceptions import AuthError, InvalidTokenError, TokenExpiredError
from blu_auth.core.jwt_decoder import decode_jwt
from blu_context_service.context_service import ContextService
from blu_supabase_client import get_supabase_client
from blu_supabase_client.crud import SupabaseCRUD, get_crud
from blu_tool_registry.registry import ToolRegistry
from blu_tool_registry.tool_metadata import TierLevel
from tool_pool_api.server.dependencies import get_context_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin/clients", tags=["Admin - Clients"])

bearer_scheme = HTTPBearer(auto_error=False)


class AdminAuthResult(BaseModel):
    """Result of admin authentication."""

    client_id: UUID
    email: str | None = None
    tier: str


async def verify_admin_access(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    crud: SupabaseCRUD = Depends(get_crud),
) -> AdminAuthResult:
    """
    Verify admin access via JWT with ADMIN tier or is_admin flag.

    Looks up the user by external_user_id (Supabase auth UUID from JWT sub).
    Accepts either tier=ADMIN or is_admin=true.

    Returns:
        AdminAuthResult with client info if authenticated
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Provide Bearer token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        claims = decode_jwt(credentials.credentials)

        try:
            auth_user_id = UUID(claims.sub)
        except (ValueError, TypeError) as e:
            logger.error(f"Invalid UUID in JWT sub claim: {claims.sub}, error: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid user ID format in token.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Fast path: check JWT app_metadata.role
        app_metadata = claims.model_dump(exclude_none=True).get("app_metadata", {})
        is_jwt_admin = isinstance(app_metadata, dict) and app_metadata.get("role") == "admin"

        # Look up client by external_user_id (JWT sub = Supabase auth UUID)
        client_data = crud.get_cliente_blu_by_external_user_id(auth_user_id)
        if not client_data:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Client not found.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        client_id = UUID(client_data["client_id"])
        client_tier = client_data.get("tier", "BASIC")
        is_admin = client_data.get("is_admin", False)

        # Check if client has admin access (JWT claim, tier, or is_admin flag)
        if not is_jwt_admin and not TierLevel.is_admin(client_tier) and not is_admin:
            logger.warning(
                f"Non-admin client {client_id} attempted admin access (tier: {client_tier}, is_admin: {is_admin})"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Admin access required. Your tier: {client_tier}",
            )

        logger.info(f"Admin auth successful for client {client_id}")
        return AdminAuthResult(
            client_id=client_id,
            email=claims.email,
            tier=client_tier,
        )

    except TokenExpiredError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired. Please refresh your authentication.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except InvalidTokenError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )
    except AuthError as e:
        logger.error(f"Auth error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed.",
            headers={"WWW-Authenticate": "Bearer"},
        )


# =============================================================================
# REQUEST/RESPONSE MODELS
# =============================================================================


class ClientCreateRequest(BaseModel):
    """Request model for creating a new client."""

    nome_empresa: str = Field(..., min_length=1, max_length=255)
    tipo_cliente: str | None = Field(default="standard")
    tier: str | None = Field(
        default="BASIC", description="Client tier: FREE, BASIC, SME, PREMIUM, ENTERPRISE"
    )
    external_user_id: str | None = Field(
        default=None, description="External user ID from OAuth provider"
    )
    # Context 2.0 sections (optional)
    available_tools: dict | None = Field(
        default=None,
        description="Tool configuration including rag_collection and default_system_prompt",
    )
    team_structure: dict | None = Field(
        default=None, description="Team info including business_hours"
    )


class ClientUpdateRequest(BaseModel):
    """Request model for updating a client. All fields optional."""

    nome_empresa: str | None = Field(default=None, max_length=255)
    tipo_cliente: str | None = None
    tier: str | None = Field(
        default=None, description="Client tier: FREE, BASIC, SME, PREMIUM, ENTERPRISE"
    )
    external_user_id: str | None = None
    # Context 2.0 sections (optional)
    available_tools: dict | None = None
    team_structure: dict | None = None


class ClientResponse(BaseModel):
    """Response model for client data."""

    id: UUID
    nome_empresa: str
    tipo_cliente: str | None = None
    tier: str | None = None
    external_user_id: str | None = None
    # Context 2.0 sections
    available_tools: dict | None = None
    team_structure: dict | None = None
    created_at: str | None = None
    updated_at: str | None = None

    class Config:
        from_attributes = True


class ClientListResponse(BaseModel):
    """Response model for listing clients."""

    clients: list[ClientResponse]
    total: int
    limit: int
    offset: int


class ToolValidationResult(BaseModel):
    """Result of tool validation."""

    is_valid: bool
    errors: list[str] = []


class AvailableToolsResponse(BaseModel):
    """Response showing available tools for a tier."""

    tier: str
    tools: list[dict]


class ActivationFunnelTenant(BaseModel):
    client_id: str
    nome_empresa: str
    signup_at: str | None
    website_provided: bool
    package_accepted: bool
    first_connector_synced: bool
    first_approval_acted: bool
    pending_approvals: int
    days_since_signup: int


class ActivationFunnelSummary(BaseModel):
    total_tenants: int
    website_provided: int
    package_accepted: int
    first_connector_synced: int
    first_approval_acted_d7: int
    conversion_website: float
    conversion_package: float
    conversion_connector: float
    conversion_first_approval_d7: float


class ActivationFunnelResponse(BaseModel):
    generated_at: str
    summary: ActivationFunnelSummary
    tenants: list[ActivationFunnelTenant]


# =============================================================================
# HELPERS
# =============================================================================


def _dict_to_response(data: dict) -> ClientResponse:
    """Convert database dict to response model."""
    return ClientResponse(
        id=UUID(data["client_id"]) if isinstance(data["client_id"], str) else data["client_id"],
        nome_empresa=data.get("nome_empresa", ""),
        tipo_cliente=data.get("tipo_cliente"),
        tier=data.get("tier"),
        external_user_id=data.get("external_user_id"),
        available_tools=data.get("available_tools"),
        team_structure=data.get("team_structure"),
        created_at=str(data["created_at"]) if data.get("created_at") else None,
        updated_at=str(data["updated_at"]) if data.get("updated_at") else None,
    )


# =============================================================================
# ENDPOINTS
# =============================================================================


@router.post(
    "",
    response_model=ClientResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new client",
)
async def create_client(
    payload: ClientCreateRequest,
    admin: AdminAuthResult = Depends(verify_admin_access),
    crud: SupabaseCRUD = Depends(get_crud),
):
    """
    Create a new cliente_blu in the database.
    """
    # Build data dict (exclude None values)
    data = payload.model_dump(exclude_none=True)

    result = crud.create_cliente_blu(data)

    if not result:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create client",
        )

    logger.info(f"Created client: {result.get('client_id')} - {result.get('nome_empresa')}")
    return _dict_to_response(result)


@router.get(
    "",
    response_model=ClientListResponse,
    summary="List all clients",
)
async def list_clients(
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    admin: AdminAuthResult = Depends(verify_admin_access),
    crud: SupabaseCRUD = Depends(get_crud),
):
    """
    List all clientes_blu with pagination.
    """
    clients = crud.list_clientes_blu(limit=limit, offset=offset)

    return ClientListResponse(
        clients=[_dict_to_response(c) for c in clients],
        total=len(clients),  # Note: Supabase doesn't return total count easily
        limit=limit,
        offset=offset,
    )


@router.get(
    "/activation-funnel",
    response_model=ActivationFunnelResponse,
    summary="Get per-tenant activation funnel metrics",
)
async def get_activation_funnel(
    limit: int = Query(default=100, ge=1, le=500),
    admin: AdminAuthResult = Depends(verify_admin_access),
):
    """Internal-only Phase D funnel: signup -> website -> package -> connector -> first approval."""

    db = get_supabase_client()
    now = datetime.now(UTC)

    tenants_rows = (
        db.table("clientes_blu")
        .select("client_id,nome_empresa,created_at,onboarding_state")
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
        .data
        or []
    )

    tenants: list[ActivationFunnelTenant] = []
    for row in tenants_rows:
        client_id = str(row["client_id"])
        state = row.get("onboarding_state") or {}
        created_at_raw = row.get("created_at")
        created_at = None
        if created_at_raw:
            try:
                created_at = datetime.fromisoformat(str(created_at_raw).replace("Z", "+00:00"))
                if created_at.tzinfo is None:
                    created_at = created_at.replace(tzinfo=UTC)
            except ValueError:
                created_at = None

        agents_rows = (
            db.table("client_enabled_agents")
            .select("agent_slug")
            .eq("client_id", client_id)
            .eq("enabled", True)
            .limit(1)
            .execute()
            .data
            or []
        )
        connectors_rows = (
            db.table("client_data_sources")
            .select("id")
            .eq("client_id", client_id)
            .not_.is_("last_synced_at", "null")
            .limit(1)
            .execute()
            .data
            or []
        )
        approvals_rows = (
            db.table("approval_requests")
            .select("status,decided_at")
            .eq("client_id", client_id)
            .limit(300)
            .execute()
            .data
            or []
        )

        pending_approvals = sum(1 for x in approvals_rows if x.get("status") == "pending")
        has_approval = any(x.get("decided_at") is not None for x in approvals_rows)

        tenants.append(
            ActivationFunnelTenant(
                client_id=client_id,
                nome_empresa=str(row.get("nome_empresa") or "Sem nome"),
                signup_at=str(created_at_raw) if created_at_raw else None,
                website_provided=bool(state.get("website")),
                package_accepted=bool(agents_rows),
                first_connector_synced=bool(connectors_rows),
                first_approval_acted=has_approval,
                pending_approvals=pending_approvals,
                days_since_signup=int((now - created_at).total_seconds() // 86400) if created_at else 0,
            )
        )

    total = len(tenants)
    website = sum(1 for t in tenants if t.website_provided)
    package = sum(1 for t in tenants if t.package_accepted)
    connector = sum(1 for t in tenants if t.first_connector_synced)
    approval_d7 = sum(
        1
        for t in tenants
        if t.first_approval_acted and t.days_since_signup <= 7
    )

    def pct(part: int) -> float:
        return round((part / total * 100.0), 2) if total > 0 else 0.0

    summary = ActivationFunnelSummary(
        total_tenants=total,
        website_provided=website,
        package_accepted=package,
        first_connector_synced=connector,
        first_approval_acted_d7=approval_d7,
        conversion_website=pct(website),
        conversion_package=pct(package),
        conversion_connector=pct(connector),
        conversion_first_approval_d7=pct(approval_d7),
    )

    return ActivationFunnelResponse(
        generated_at=now.isoformat(),
        summary=summary,
        tenants=tenants,
    )


@router.get(
    "/{client_id}",
    response_model=ClientResponse,
    summary="Get a client by ID",
)
async def get_client(
    client_id: UUID,
    admin: AdminAuthResult = Depends(verify_admin_access),
    crud: SupabaseCRUD = Depends(get_crud),
):
    """
    Get a single cliente_blu by ID.
    """
    result = crud.get_cliente_blu_by_id(client_id)

    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Client not found: {client_id}",
        )

    return _dict_to_response(result)


@router.patch(
    "/{client_id}",
    response_model=ClientResponse,
    summary="Update a client",
)
async def update_client(
    client_id: UUID,
    payload: ClientUpdateRequest,
    admin: AdminAuthResult = Depends(verify_admin_access),
    crud: SupabaseCRUD = Depends(get_crud),
    ctx_service: ContextService = Depends(get_context_service),
):
    """
    Update a cliente_blu. Only provided fields will be updated.

    Automatically clears the Redis context cache when tier or available_tools
    change, so the agent picks up the new values immediately.
    """
    # First, check if client exists
    existing = crud.get_cliente_blu_by_id(client_id)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Client not found: {client_id}",
        )

    # Build data dict (exclude None values to only update provided fields)
    data = payload.model_dump(exclude_none=True)

    if not data:
        # Nothing to update
        return _dict_to_response(existing)

    result = crud.update_cliente_blu(client_id, data)

    if not result:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update client",
        )

    # Invalidate context cache whenever tier or available_tools changes so that
    # tool_pool_api picks up the new values on the very next request.
    if "tier" in data or "available_tools" in data:
        await ctx_service.clear_context_cache(client_id)
        logger.info(
            f"Context cache cleared for client {client_id} "
            f"(changed fields: {list(data.keys())})"
        )

    logger.info(f"Updated client: {client_id}")
    return _dict_to_response(result)


@router.post(
    "/{client_id}/clear-cache",
    status_code=status.HTTP_200_OK,
    summary="Clear Redis context cache for a client",
)
async def clear_client_cache(
    client_id: UUID,
    admin: AdminAuthResult = Depends(verify_admin_access),
    ctx_service: ContextService = Depends(get_context_service),
):
    """
    Force-invalidate the Redis context cache for a client.

    Use this when Supabase data was changed outside the API (e.g., direct DB
    edit) and you need the agent to pick up the new values immediately without
    waiting for the 5-minute TTL to expire.
    """
    await ctx_service.clear_context_cache(client_id)
    logger.info(f"Admin manually cleared context cache for client {client_id}")
    return {"client_id": str(client_id), "cache_cleared": True}


@router.delete(
    "/{client_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Soft-delete a client",
)
async def delete_client(
    client_id: UUID,
    hard: bool = Query(
        default=False,
        description="If true, perform immediate hard delete (admin emergency use only).",
    ),
    admin: AdminAuthResult = Depends(verify_admin_access),
    crud: SupabaseCRUD = Depends(get_crud),
):
    """
    Soft-delete a cliente_blu by ID.

    Sets deleted_at = now(). Data is retained for 7 days then purged
    nightly by the pg_cron job offboard_cleanup_nightly.

    Pass ?hard=true for an immediate hard delete (emergency only — irreversible).
    """
    existing = crud.get_cliente_blu_by_id(client_id)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Client not found: {client_id}",
        )

    db = get_supabase_client(use_service_role=True)

    if hard:
        logger.warning(f"HARD DELETE requested for client {client_id} by admin {admin.client_id}")
        success = crud.delete_cliente_blu(client_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to hard delete client",
            )
        logger.info(f"Hard deleted client: {client_id}")
    else:
        # Soft delete via DB function — sets deleted_at, data purged after 7 days
        db.rpc("soft_delete_client", {"p_client_id": str(client_id)}).execute()
        logger.info(f"Soft deleted client: {client_id} (data retained for 7 days)")

    return None


# =============================================================================
# TOOL VALIDATION ENDPOINTS
# =============================================================================


@router.post(
    "/validate-tools",
    response_model=ToolValidationResult,
    summary="Validate tools for a tier",
)
async def validate_tools(
    enabled_tools: list[str],
    tier: str = Query(default="BASIC"),
    admin: AdminAuthResult = Depends(verify_admin_access),
):
    """
    Validate that a list of tools is compatible with a tier.

    Useful for checking before creating/updating an agent configuration.
    """
    is_valid, errors = ToolRegistry.validate_client_tools(enabled_tools, tier)

    return ToolValidationResult(is_valid=is_valid, errors=errors)


@router.get(
    "/available-tools/{tier}",
    response_model=AvailableToolsResponse,
    summary="Get available tools for a tier",
)
async def get_available_tools_for_tier(
    tier: str,
    admin: AdminAuthResult = Depends(verify_admin_access),
):
    """
    Get all tools available at a specific tier level.

    Useful for building UI dropdowns or documentation.
    """
    tools = ToolRegistry.get_tools_for_tier(tier)

    return AvailableToolsResponse(
        tier=tier,
        tools=[
            {
                "name": t.name,
                "description": t.description,
                "category": t.category.value,
                "tier_required": t.tier_required.value,
                "requires_confirmation": t.requires_confirmation,
                "tags": t.tags,
            }
            for t in tools
        ],
    )


@router.get(
    "/all-tools",
    summary="Get all registered tools",
)
async def get_all_tools(
    admin: AdminAuthResult = Depends(verify_admin_access),
):
    """
    Get all registered tools with their metadata.

    Returns builtin, Google, and Docker MCP tools.
    """
    all_tools = ToolRegistry.get_all_tools()

    return {
        "total": len(all_tools),
        "tools": [
            {
                "name": t.name,
                "description": t.description,
                "category": t.category.value,
                "tier_required": t.tier_required.value,
                "requires_confirmation": t.requires_confirmation,
                "tags": t.tags,
                "enabled": t.enabled,
            }
            for t in all_tools.values()
        ],
    }
