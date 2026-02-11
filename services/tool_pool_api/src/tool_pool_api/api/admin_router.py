"""
Admin API Router for Client Management.

Provides CRUD endpoints for managing cliente_vizu records.
Protected by JWT authentication - requires ADMIN tier.
"""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field

from vizu_auth.core.exceptions import AuthError, InvalidTokenError, TokenExpiredError
from vizu_auth.core.jwt_decoder import decode_jwt
from vizu_supabase_client.crud import SupabaseCRUD, get_crud
from vizu_tool_registry.registry import ToolRegistry
from vizu_tool_registry.tool_metadata import TierLevel

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
    Verify admin access via JWT with ADMIN tier.

    The user must have tier=ADMIN in their cliente_vizu record.

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
            client_id = UUID(claims.sub)
        except (ValueError, TypeError) as e:
            logger.error(f"Invalid UUID in JWT sub claim: {claims.sub}, error: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid user ID format in token.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Fetch client to check tier
        client_data = crud.get_cliente_vizu_by_id(client_id)
        if not client_data:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Client not found.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        client_tier = client_data.get("tier", "BASIC")

        # Check if client has ADMIN tier
        if not TierLevel.is_admin(client_tier):
            logger.warning(
                f"Non-admin client {client_id} attempted admin access (tier: {client_tier})"
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
    enabled_tools: list[str] | None = Field(default=None, description="List of enabled tool names")
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
    enabled_tools: list[str] | None = None
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
    enabled_tools: list[str] | None = None
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


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================


def _validate_tools_for_tier(
    enabled_tools: list[str] | None, tier: str | None
) -> tuple[bool, list[str]]:
    """Validate that enabled tools are compatible with the tier."""
    if not enabled_tools:
        return True, []

    tier_to_use = tier or "BASIC"
    return ToolRegistry.validate_client_tools(enabled_tools, tier_to_use)


def _dict_to_response(data: dict) -> ClientResponse:
    """Convert database dict to response model."""
    return ClientResponse(
        id=UUID(data["id"]) if isinstance(data["id"], str) else data["id"],
        nome_empresa=data.get("nome_empresa", ""),
        tipo_cliente=data.get("tipo_cliente"),
        tier=data.get("tier"),
        enabled_tools=data.get("enabled_tools"),
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
    Create a new cliente_vizu in the database.

    The enabled_tools list will be validated against the specified tier.
    """
    # Validate tools against tier
    is_valid, errors = _validate_tools_for_tier(payload.enabled_tools, payload.tier)

    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "message": "Tool validation failed",
                "errors": errors,
            },
        )

    # Build data dict (exclude None values)
    data = payload.model_dump(exclude_none=True)

    result = crud.create_cliente_vizu(data)

    if not result:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create client",
        )

    logger.info(f"Created client: {result.get('id')} - {result.get('nome_empresa')}")
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
    List all clientes_vizu with pagination.
    """
    clients = crud.list_clientes_vizu(limit=limit, offset=offset)

    return ClientListResponse(
        clients=[_dict_to_response(c) for c in clients],
        total=len(clients),  # Note: Supabase doesn't return total count easily
        limit=limit,
        offset=offset,
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
    Get a single cliente_vizu by ID.
    """
    result = crud.get_cliente_vizu_by_id(client_id)

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
):
    """
    Update a cliente_vizu. Only provided fields will be updated.

    If enabled_tools is updated, it will be validated against the tier
    (either the new tier if provided, or the existing tier).
    """
    # First, check if client exists
    existing = crud.get_cliente_vizu_by_id(client_id)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Client not found: {client_id}",
        )

    # Determine the tier to validate against
    tier_for_validation = payload.tier or existing.get("tier") or "BASIC"
    tools_to_validate = payload.enabled_tools

    # If tools aren't being updated, skip validation
    if tools_to_validate is not None:
        is_valid, errors = _validate_tools_for_tier(tools_to_validate, tier_for_validation)

        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "message": "Tool validation failed",
                    "errors": errors,
                },
            )

    # Build data dict (exclude None values to only update provided fields)
    data = payload.model_dump(exclude_none=True)

    if not data:
        # Nothing to update
        return _dict_to_response(existing)

    result = crud.update_cliente_vizu(client_id, data)

    if not result:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update client",
        )

    logger.info(f"Updated client: {client_id}")
    return _dict_to_response(result)


@router.delete(
    "/{client_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a client",
)
async def delete_client(
    client_id: UUID,
    admin: AdminAuthResult = Depends(verify_admin_access),
    crud: SupabaseCRUD = Depends(get_crud),
):
    """
    Delete a cliente_vizu by ID.

    WARNING: This is a hard delete. Consider soft delete in production.
    """
    # Check if exists first
    existing = crud.get_cliente_vizu_by_id(client_id)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Client not found: {client_id}",
        )

    success = crud.delete_cliente_vizu(client_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete client",
        )

    logger.info(f"Deleted client: {client_id}")
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

    Useful for checking before creating/updating a client.
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
