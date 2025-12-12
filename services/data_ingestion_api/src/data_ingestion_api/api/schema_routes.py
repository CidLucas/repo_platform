"""
API Routes para Schema Discovery e Mapping.

Endpoints para:
- Descobrir schema de fontes de dados
- Sugerir mapeamentos automáticos com difflib
- CRUD de mapeamentos confirmados
"""

import logging
from typing import Any, Dict, List, Optional

from data_ingestion_api.services.schema_discovery_service import DiscoveredSchema, schema_discovery
from data_ingestion_api.services.schema_matcher_service import SchemaMatchResult, schema_matcher
from data_ingestion_api.services.schema_registry_service import (
    MappingStatus,
    SchemaMapping,
    schema_registry,
)
from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/schema",
    tags=["Schema Discovery & Mapping"]
)


# --- Pydantic Models para Request/Response ---

class DiscoverSchemaRequest(BaseModel):
    """Request para descoberta de schema."""
    credential_id: str = Field(..., description="ID da credencial/fonte de dados")
    resource_type: str = Field(..., description="Tipo do recurso (products, orders, etc.)")
    connector_type: str = Field(default="ecommerce", description="Tipo do conector")
    
    class Config:
        json_schema_extra = {
            "example": {
                "credential_id": "uuid-da-credencial",
                "resource_type": "products",
                "connector_type": "shopify"
            }
        }


class DiscoverSchemaResponse(BaseModel):
    """Response da descoberta de schema."""
    resource_type: str
    columns: list[str]
    column_count: int
    sample_data: dict[str, Any] | None = None
    column_types: dict[str, str] = {}
    

class AutoMatchRequest(BaseModel):
    """Request para matching automático."""
    source_columns: list[str] = Field(..., description="Colunas da fonte de dados")
    schema_type: str = Field(..., description="Tipo do schema canônico (products, orders, etc.)")
    high_threshold: float = Field(default=0.75, description="Threshold para match automático")
    medium_threshold: float = Field(default=0.50, description="Threshold para revisão")
    
    class Config:
        json_schema_extra = {
            "example": {
                "source_columns": ["TotalPrice_Product", "createdat_product", "productName"],
                "schema_type": "products",
                "high_threshold": 0.75,
                "medium_threshold": 0.50
            }
        }


class AutoMatchResponse(BaseModel):
    """Response do matching automático."""
    matched: dict[str, str]  # {source_column: canonical_column}
    unmatched: list[str]
    needs_review: list[str]
    confidence_scores: dict[str, float]
    details: list[dict[str, Any]]


class SaveMappingRequest(BaseModel):
    """Request para salvar mapeamento."""
    credential_id: str = Field(..., description="ID da credencial")
    resource_type: str = Field(..., description="Tipo do recurso")
    source_columns: list[str] = Field(..., description="Colunas originais da fonte")
    mapping: dict[str, str] = Field(..., description="Mapeamento confirmado {origem: destino}")
    unmapped_columns: list[str] = Field(default=[], description="Colunas não mapeadas")
    confidence_scores: dict[str, float] = Field(default={}, description="Scores de confiança")
    status: str | None = Field(default=None, description="Status do mapeamento")
    metadata: dict[str, Any] = Field(default={}, description="Metadados adicionais")
    
    class Config:
        json_schema_extra = {
            "example": {
                "credential_id": "uuid-da-credencial",
                "resource_type": "products",
                "source_columns": ["productName", "price", "sku"],
                "mapping": {
                    "productName": "product_name",
                    "price": "price",
                    "sku": "sku"
                },
                "unmapped_columns": [],
                "confidence_scores": {
                    "productName": 0.92,
                    "price": 1.0,
                    "sku": 1.0
                }
            }
        }


class MappingResponse(BaseModel):
    """Response de mapeamento."""
    id: str | None
    credential_id: str
    resource_type: str
    source_columns: list[str]
    mapping: dict[str, str]
    unmapped_columns: list[str]
    confidence_scores: dict[str, float]
    status: str
    created_at: str | None = None
    updated_at: str | None = None


class UpdateMappingRequest(BaseModel):
    """Request para atualizar mapeamento."""
    mapping: dict[str, str] = Field(..., description="Novo mapeamento confirmado")
    unmapped_columns: list[str] = Field(default=[], description="Colunas não mapeadas")


class CanonicalSchemaResponse(BaseModel):
    """Response do schema canônico."""
    schema_type: str
    columns: list[str]
    column_count: int


# --- Endpoints ---

@router.get(
    "/canonical/{schema_type}",
    response_model=CanonicalSchemaResponse,
    summary="Retorna o schema canônico Vizu para um tipo de recurso"
)
async def get_canonical_schema(schema_type: str):
    """
    Retorna as colunas do schema canônico Vizu para um tipo de recurso.
    
    Tipos suportados: products, orders, customers, inventory, categories
    """
    try:
        columns = schema_matcher.get_canonical_schema(schema_type)
        return CanonicalSchemaResponse(
            schema_type=schema_type,
            columns=columns,
            column_count=len(columns)
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get(
    "/canonical",
    summary="Lista todos os tipos de schema suportados"
)
async def list_canonical_schemas():
    """
    Retorna todos os tipos de schema canônico suportados.
    """
    types = schema_matcher.get_supported_types()
    return {
        "supported_types": types,
        "count": len(types)
    }


@router.post(
    "/auto-match",
    response_model=AutoMatchResponse,
    summary="Sugere mapeamento automático usando difflib"
)
async def auto_match_columns(request: AutoMatchRequest):
    """
    Faz matching automático de colunas de origem para o schema canônico Vizu.
    
    Usa difflib para calcular similaridade entre nomes de colunas.
    
    Retorna:
    - matched: Colunas mapeadas automaticamente (score >= high_threshold)
    - needs_review: Colunas que precisam revisão manual (medium <= score < high)
    - unmatched: Colunas sem match aceitável (score < medium)
    - confidence_scores: Score de confiança para cada coluna
    """
    try:
        result: SchemaMatchResult = schema_matcher.auto_match(
            source_columns=request.source_columns,
            schema_type=request.schema_type,
            high_threshold=request.high_threshold,
            medium_threshold=request.medium_threshold
        )
        
        return AutoMatchResponse(
            matched=result.matched,
            unmatched=result.unmatched,
            needs_review=result.needs_review,
            confidence_scores=result.confidence_scores,
            details=[d.to_dict() for d in result.details]
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Erro no auto-match: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro interno: {str(e)}"
        )


@router.post(
    "/mappings",
    response_model=MappingResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Salva um mapeamento de schema"
)
async def save_mapping(request: SaveMappingRequest):
    """
    Salva ou atualiza um mapeamento de schema no banco de dados.
    
    Usa upsert baseado em (credential_id, resource_type).
    """
    try:
        # Converte status string para enum se fornecido
        status_enum = None
        if request.status:
            status_enum = MappingStatus(request.status)
        
        mapping = await schema_registry.save_mapping(
            credential_id=request.credential_id,
            resource_type=request.resource_type,
            source_columns=request.source_columns,
            mapping=request.mapping,
            unmapped_columns=request.unmapped_columns,
            confidence_scores=request.confidence_scores,
            status=status_enum,
            metadata=request.metadata
        )
        
        return MappingResponse(
            id=mapping.id,
            credential_id=mapping.credential_id,
            resource_type=mapping.resource_type,
            source_columns=mapping.source_columns,
            mapping=mapping.mapping,
            unmapped_columns=mapping.unmapped_columns,
            confidence_scores=mapping.confidence_scores,
            status=mapping.status.value if isinstance(mapping.status, MappingStatus) else mapping.status,
            created_at=str(mapping.created_at) if mapping.created_at else None,
            updated_at=str(mapping.updated_at) if mapping.updated_at else None
        )
        
    except Exception as e:
        logger.error(f"Erro ao salvar mapeamento: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao salvar mapeamento: {str(e)}"
        )


@router.get(
    "/mappings/{credential_id}/{resource_type}",
    response_model=MappingResponse,
    summary="Busca um mapeamento específico"
)
async def get_mapping(credential_id: str, resource_type: str):
    """
    Busca um mapeamento de schema por credential_id e resource_type.
    """
    mapping = await schema_registry.get_mapping(credential_id, resource_type)
    
    if not mapping:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Mapeamento não encontrado para {credential_id}/{resource_type}"
        )
    
    return MappingResponse(
        id=mapping.id,
        credential_id=mapping.credential_id,
        resource_type=mapping.resource_type,
        source_columns=mapping.source_columns,
        mapping=mapping.mapping,
        unmapped_columns=mapping.unmapped_columns,
        confidence_scores=mapping.confidence_scores,
        status=mapping.status.value if isinstance(mapping.status, MappingStatus) else mapping.status,
        created_at=str(mapping.created_at) if mapping.created_at else None,
        updated_at=str(mapping.updated_at) if mapping.updated_at else None
    )


@router.get(
    "/mappings",
    response_model=list[MappingResponse],
    summary="Lista mapeamentos"
)
async def list_mappings(
    credential_id: str | None = Query(None, description="Filtrar por credential_id"),
    status: str | None = Query(None, description="Filtrar por status")
):
    """
    Lista mapeamentos de schema.
    
    Pode filtrar por credential_id ou status.
    """
    mappings = []
    
    if credential_id:
        mappings = await schema_registry.get_mappings_by_credential(credential_id)
    elif status:
        try:
            status_enum = MappingStatus(status)
            mappings = await schema_registry.get_mappings_by_status(status_enum)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Status inválido. Use: {[s.value for s in MappingStatus]}"
            )
    else:
        # Sem filtros - retorna mapeamentos pendentes de revisão por padrão
        mappings = await schema_registry.get_mappings_by_status(MappingStatus.NEEDS_REVIEW)
    
    return [
        MappingResponse(
            id=m.id,
            credential_id=m.credential_id,
            resource_type=m.resource_type,
            source_columns=m.source_columns,
            mapping=m.mapping,
            unmapped_columns=m.unmapped_columns,
            confidence_scores=m.confidence_scores,
            status=m.status.value if isinstance(m.status, MappingStatus) else m.status,
            created_at=str(m.created_at) if m.created_at else None,
            updated_at=str(m.updated_at) if m.updated_at else None
        )
        for m in mappings
    ]


@router.put(
    "/mappings/{credential_id}/{resource_type}",
    response_model=MappingResponse,
    summary="Atualiza um mapeamento após revisão manual"
)
async def update_mapping(
    credential_id: str,
    resource_type: str,
    request: UpdateMappingRequest
):
    """
    Atualiza um mapeamento de schema após revisão manual.
    
    Automaticamente define status como 'ready'.
    """
    mapping = await schema_registry.update_mapping(
        credential_id=credential_id,
        resource_type=resource_type,
        mapping=request.mapping,
        unmapped_columns=request.unmapped_columns
    )
    
    if not mapping:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Mapeamento não encontrado para {credential_id}/{resource_type}"
        )
    
    return MappingResponse(
        id=mapping.id,
        credential_id=mapping.credential_id,
        resource_type=mapping.resource_type,
        source_columns=mapping.source_columns,
        mapping=mapping.mapping,
        unmapped_columns=mapping.unmapped_columns,
        confidence_scores=mapping.confidence_scores,
        status=mapping.status.value if isinstance(mapping.status, MappingStatus) else mapping.status,
        created_at=str(mapping.created_at) if mapping.created_at else None,
        updated_at=str(mapping.updated_at) if mapping.updated_at else None
    )


@router.patch(
    "/mappings/{credential_id}/{resource_type}/status",
    summary="Atualiza apenas o status de um mapeamento"
)
async def update_mapping_status(
    credential_id: str,
    resource_type: str,
    new_status: str = Query(..., description="Novo status")
):
    """
    Atualiza apenas o status de um mapeamento.
    
    Status válidos: pending, needs_review, ready, error
    """
    try:
        status_enum = MappingStatus(new_status)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Status inválido. Use: {[s.value for s in MappingStatus]}"
        )
    
    success = await schema_registry.update_status(credential_id, resource_type, status_enum)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Mapeamento não encontrado para {credential_id}/{resource_type}"
        )
    
    return {"message": f"Status atualizado para '{new_status}'"}


@router.delete(
    "/mappings/{credential_id}/{resource_type}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Deleta um mapeamento"
)
async def delete_mapping(credential_id: str, resource_type: str):
    """
    Deleta um mapeamento de schema.
    """
    success = await schema_registry.delete_mapping(credential_id, resource_type)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Mapeamento não encontrado para {credential_id}/{resource_type}"
        )
    
    return None


@router.delete(
    "/mappings/{credential_id}",
    summary="Deleta todos os mapeamentos de uma credencial"
)
async def delete_all_mappings(credential_id: str):
    """
    Deleta todos os mapeamentos associados a uma credencial.
    """
    count = await schema_registry.delete_all_by_credential(credential_id)
    
    return {
        "message": "Mapeamentos deletados",
        "count": count
    }


# --- Endpoint de Fluxo Completo ---

class FullMappingFlowRequest(BaseModel):
    """Request para fluxo completo de mapeamento."""
    credential_id: str
    resource_type: str
    source_columns: list[str]
    auto_save: bool = Field(default=True, description="Salvar automaticamente se todos tiverem alta confiança")


class FullMappingFlowResponse(BaseModel):
    """Response do fluxo completo."""
    status: str  # "auto_saved", "needs_review", "error"
    mapping_result: AutoMatchResponse
    saved_mapping: MappingResponse | None = None
    message: str


@router.post(
    "/discover-and-match",
    response_model=FullMappingFlowResponse,
    summary="Fluxo completo: recebe colunas, faz match e salva automaticamente"
)
async def discover_and_match(request: FullMappingFlowRequest):
    """
    Fluxo completo de mapeamento:
    
    1. Recebe lista de colunas da fonte
    2. Faz matching automático com difflib
    3. Se auto_save=True e todos os matches tiverem alta confiança, salva automaticamente
    4. Caso contrário, retorna sugestões para revisão manual
    
    Este endpoint é usado pelo frontend para o fluxo de configuração de conectores.
    """
    try:
        # 1. Faz o match automático
        match_result = schema_matcher.auto_match(
            source_columns=request.source_columns,
            schema_type=request.resource_type
        )
        
        match_response = AutoMatchResponse(
            matched=match_result.matched,
            unmatched=match_result.unmatched,
            needs_review=match_result.needs_review,
            confidence_scores=match_result.confidence_scores,
            details=[d.to_dict() for d in match_result.details]
        )
        
        # 2. Determina se pode salvar automaticamente
        can_auto_save = (
            request.auto_save and
            len(match_result.needs_review) == 0 and
            len(match_result.unmatched) == 0
        )
        
        if can_auto_save:
            # 3a. Salva automaticamente
            mapping = await schema_registry.save_mapping(
                credential_id=request.credential_id,
                resource_type=request.resource_type,
                source_columns=request.source_columns,
                mapping=match_result.matched,
                unmapped_columns=match_result.unmatched,
                confidence_scores=match_result.confidence_scores,
                status=MappingStatus.READY
            )
            
            saved_response = MappingResponse(
                id=mapping.id,
                credential_id=mapping.credential_id,
                resource_type=mapping.resource_type,
                source_columns=mapping.source_columns,
                mapping=mapping.mapping,
                unmapped_columns=mapping.unmapped_columns,
                confidence_scores=mapping.confidence_scores,
                status=mapping.status.value,
                created_at=str(mapping.created_at) if mapping.created_at else None,
                updated_at=str(mapping.updated_at) if mapping.updated_at else None
            )
            
            return FullMappingFlowResponse(
                status="auto_saved",
                mapping_result=match_response,
                saved_mapping=saved_response,
                message="Todas as colunas foram mapeadas automaticamente com alta confiança."
            )
        
        else:
            # 3b. Precisa revisão - salva com status needs_review se tiver matches
            if match_result.matched:
                mapping = await schema_registry.save_mapping(
                    credential_id=request.credential_id,
                    resource_type=request.resource_type,
                    source_columns=request.source_columns,
                    mapping=match_result.matched,
                    unmapped_columns=match_result.unmatched,
                    confidence_scores=match_result.confidence_scores,
                    status=MappingStatus.NEEDS_REVIEW
                )
                
                saved_response = MappingResponse(
                    id=mapping.id,
                    credential_id=mapping.credential_id,
                    resource_type=mapping.resource_type,
                    source_columns=mapping.source_columns,
                    mapping=mapping.mapping,
                    unmapped_columns=mapping.unmapped_columns,
                    confidence_scores=mapping.confidence_scores,
                    status=mapping.status.value,
                    created_at=str(mapping.created_at) if mapping.created_at else None,
                    updated_at=str(mapping.updated_at) if mapping.updated_at else None
                )
            else:
                saved_response = None
            
            review_count = len(match_result.needs_review)
            unmatched_count = len(match_result.unmatched)
            
            return FullMappingFlowResponse(
                status="needs_review",
                mapping_result=match_response,
                saved_mapping=saved_response,
                message=f"{review_count} colunas precisam de revisão, {unmatched_count} não foram mapeadas."
            )
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Erro no fluxo de mapeamento: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro interno: {str(e)}"
        )
