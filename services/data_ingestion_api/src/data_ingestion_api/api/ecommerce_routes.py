"""
Rotas da API para integração com plataformas de e-commerce.

Suporta:
- Shopify
- VTEX
- Loja Integrada
"""

from fastapi import APIRouter, HTTPException, status, Depends
from typing import Union
import logging

from data_ingestion_api.schemas.schemas import (
    ShopifyCredentialCreate,
    VTEXCredentialCreate,
    LojaIntegradaCredentialCreate,
    CredencialResponse,
    ExtractionRequest,
    ExtractionResponse,
    ConnectionTestResponse,
)
from data_ingestion_api.connectors import (
    ShopifyConnector,
    VTEXConnector,
    LojaIntegradaConnector,
    EcommerceConnectorError,
    AuthenticationError,
    RateLimitError,
)
from data_ingestion_api.services.credential_service import credential_service

logger = logging.getLogger(__name__)

# Router para endpoints de e-commerce
router = APIRouter(
    prefix="/ecommerce",
    tags=["Ingestion - E-commerce Connectors"]
)

# Union Type para validação do FastAPI (Agnosticismo de plataforma)
EcommerceCredentialPayload = Union[
    ShopifyCredentialCreate,
    VTEXCredentialCreate,
    LojaIntegradaCredentialCreate
]


def _get_connector_class(tipo_servico: str):
    """Retorna a classe de conector baseada no tipo de serviço."""
    connectors = {
        "SHOPIFY": ShopifyConnector,
        "VTEX": VTEXConnector,
        "LOJA_INTEGRADA": LojaIntegradaConnector,
    }
    connector_class = connectors.get(tipo_servico.upper())
    if not connector_class:
        raise ValueError(f"Tipo de serviço não suportado: {tipo_servico}")
    return connector_class


# ----------------------------------------------------------------------
# Endpoints de Credenciais
# ----------------------------------------------------------------------

@router.post(
    "/credentials",
    response_model=CredencialResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Cadastra credenciais de plataforma e-commerce"
)
async def create_ecommerce_credential(
    payload: EcommerceCredentialPayload
):
    """
    Cadastra as credenciais de uma plataforma de e-commerce.
    
    Plataformas suportadas:
    - **Shopify**: Requer shop_name e access_token
    - **VTEX**: Requer account_name, app_key e app_token
    - **Loja Integrada**: Requer api_key
    
    O segredo é armazenado de forma segura no Secret Manager.
    """
    try:
        response = await credential_service.create_credential(payload)
        return response
    except Exception as e:
        logger.error(f"Erro ao criar credencial e-commerce: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Falha ao processar credencial: {str(e)}"
        )


@router.post(
    "/test-connection",
    response_model=ConnectionTestResponse,
    summary="Testa a conexão com uma plataforma e-commerce"
)
async def test_ecommerce_connection(
    payload: EcommerceCredentialPayload
):
    """
    Testa a conexão com a plataforma de e-commerce antes de salvar as credenciais.
    
    Útil para validar se as credenciais estão corretas antes do cadastro.
    """
    try:
        connector_class = _get_connector_class(payload.tipo_servico)
        
        # Converte o payload para dicionário de credenciais
        credentials = payload.model_dump(exclude={"cliente_vizu_id", "nome_conexao", "tipo_servico"})
        
        async with connector_class(credentials) as connector:
            is_valid = await connector.validate_connection()
            
            if is_valid:
                return ConnectionTestResponse(
                    success=True,
                    message="Conexão estabelecida com sucesso!",
                    platform=payload.tipo_servico,
                    connection_string=connector.get_connection_string()
                )
            else:
                return ConnectionTestResponse(
                    success=False,
                    message="Falha ao validar conexão. Verifique as credenciais.",
                    platform=payload.tipo_servico,
                    connection_string=None
                )
                
    except AuthenticationError as e:
        logger.warning(f"Erro de autenticação: {e}")
        return ConnectionTestResponse(
            success=False,
            message=f"Erro de autenticação: {str(e)}",
            platform=payload.tipo_servico,
            connection_string=None
        )
    except Exception as e:
        logger.error(f"Erro no teste de conexão: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao testar conexão: {str(e)}"
        )


# ----------------------------------------------------------------------
# Endpoints de Extração de Dados
# ----------------------------------------------------------------------

@router.post(
    "/extract",
    response_model=ExtractionResponse,
    summary="Extrai dados de uma plataforma e-commerce"
)
async def extract_ecommerce_data(
    request: ExtractionRequest
):
    """
    Extrai dados de uma plataforma de e-commerce.
    
    Recursos disponíveis:
    - **products**: Lista de produtos
    - **orders**: Lista de pedidos
    - **customers**: Lista de clientes
    - **inventory**: Dados de estoque
    
    A extração é feita com paginação automática.
    """
    try:
        # TODO: Buscar credenciais do banco/secret manager pelo credential_id
        # credentials = await credential_service.get_credentials(request.credential_id)
        
        # Por enquanto, retorna erro indicando que precisa implementar
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Extração via credential_id ainda não implementada. Use extract-direct."
        )
        
    except Exception as e:
        logger.error(f"Erro na extração: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro na extração de dados: {str(e)}"
        )


@router.post(
    "/extract-direct/{platform}",
    response_model=ExtractionResponse,
    summary="Extrai dados diretamente com credenciais fornecidas"
)
async def extract_direct(
    platform: str,
    credentials: EcommerceCredentialPayload,
    resource: str,
    limit: int = 100,
    page: int = 1
):
    """
    Extrai dados diretamente de uma plataforma e-commerce.
    
    **ATENÇÃO**: Este endpoint recebe as credenciais diretamente. 
    Em produção, prefira usar o endpoint /extract com credential_id.
    
    Parâmetros:
    - **platform**: shopify, vtex ou loja_integrada
    - **resource**: products, orders, customers ou inventory
    - **limit**: Número máximo de registros (padrão: 100)
    - **page**: Número da página (padrão: 1)
    """
    try:
        connector_class = _get_connector_class(platform)
        creds = credentials.model_dump(exclude={"cliente_vizu_id", "nome_conexao", "tipo_servico"})
        
        async with connector_class(creds) as connector:
            # Valida a conexão primeiro
            if not await connector.validate_connection():
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Falha na autenticação. Verifique as credenciais."
                )
            
            # Extrai os dados baseado no recurso
            resource_lower = resource.lower()
            data = []
            
            if resource_lower == "products":
                data = await connector.get_products(limit=limit, page=page)
            elif resource_lower == "orders":
                data = await connector.get_orders(limit=limit, page=page)
            elif resource_lower == "customers":
                data = await connector.get_customers(limit=limit, page=page)
            elif resource_lower == "inventory":
                data = await connector.get_inventory(limit=limit, page=page)
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Recurso '{resource}' não suportado. Use: products, orders, customers, inventory"
                )
            
            return ExtractionResponse(
                success=True,
                resource=resource_lower,
                total_records=len(data),
                page=page,
                has_more=len(data) >= limit,
                data=data
            )
            
    except AuthenticationError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Erro de autenticação: {str(e)}"
        )
    except RateLimitError as e:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit atingido: {str(e)}"
        )
    except EcommerceConnectorError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Erro na comunicação com a plataforma: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Erro na extração direta: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro na extração: {str(e)}"
        )


# ----------------------------------------------------------------------
# Endpoints de Informações
# ----------------------------------------------------------------------

@router.get(
    "/platforms",
    summary="Lista plataformas de e-commerce suportadas"
)
async def list_platforms():
    """
    Retorna a lista de plataformas de e-commerce suportadas
    com informações sobre os recursos disponíveis.
    """
    return {
        "platforms": [
            {
                "id": "shopify",
                "name": "Shopify",
                "description": "Plataforma de e-commerce líder mundial",
                "resources": ["products", "orders", "customers", "inventory", "collections"],
                "auth_type": "access_token",
                "required_fields": ["shop_name", "access_token"],
                "optional_fields": ["api_version", "api_key", "api_secret"],
                "docs_url": "https://shopify.dev/docs/api/admin-rest"
            },
            {
                "id": "vtex",
                "name": "VTEX",
                "description": "Plataforma de e-commerce enterprise da América Latina",
                "resources": ["products", "orders", "customers", "inventory", "categories", "brands"],
                "auth_type": "app_key_token",
                "required_fields": ["account_name", "app_key", "app_token"],
                "optional_fields": ["environment"],
                "docs_url": "https://developers.vtex.com/docs/api-reference"
            },
            {
                "id": "loja_integrada",
                "name": "Loja Integrada",
                "description": "Plataforma de e-commerce brasileira",
                "resources": ["products", "orders", "customers", "inventory", "categories", "brands"],
                "auth_type": "api_key",
                "required_fields": ["api_key"],
                "optional_fields": ["application_key"],
                "docs_url": "https://lojaintegrada.docs.apiary.io/"
            }
        ],
        "common_resources": [
            {
                "name": "products",
                "description": "Catálogo de produtos da loja"
            },
            {
                "name": "orders",
                "description": "Pedidos realizados na loja"
            },
            {
                "name": "customers",
                "description": "Base de clientes cadastrados"
            },
            {
                "name": "inventory",
                "description": "Níveis de estoque dos produtos"
            }
        ]
    }


@router.get(
    "/platforms/{platform}/resources",
    summary="Lista recursos disponíveis para uma plataforma"
)
async def list_platform_resources(platform: str):
    """
    Retorna os recursos disponíveis para extração em uma plataforma específica.
    """
    resources_map = {
        "shopify": [
            {"name": "products", "description": "Produtos e variantes", "supports_pagination": True},
            {"name": "orders", "description": "Pedidos da loja", "supports_pagination": True},
            {"name": "customers", "description": "Clientes cadastrados", "supports_pagination": True},
            {"name": "inventory", "description": "Níveis de estoque", "supports_pagination": True},
            {"name": "collections", "description": "Coleções de produtos", "supports_pagination": True},
        ],
        "vtex": [
            {"name": "products", "description": "Produtos do catálogo", "supports_pagination": True},
            {"name": "orders", "description": "Pedidos (OMS)", "supports_pagination": True},
            {"name": "customers", "description": "Clientes (Master Data)", "supports_pagination": True},
            {"name": "inventory", "description": "Estoque (Logistics)", "supports_pagination": True},
            {"name": "categories", "description": "Árvore de categorias", "supports_pagination": False},
            {"name": "brands", "description": "Marcas cadastradas", "supports_pagination": False},
        ],
        "loja_integrada": [
            {"name": "products", "description": "Produtos da loja", "supports_pagination": True},
            {"name": "orders", "description": "Pedidos realizados", "supports_pagination": True},
            {"name": "customers", "description": "Clientes cadastrados", "supports_pagination": True},
            {"name": "inventory", "description": "Estoque de variações", "supports_pagination": True},
            {"name": "categories", "description": "Categorias", "supports_pagination": True},
            {"name": "brands", "description": "Marcas", "supports_pagination": True},
        ],
    }
    
    platform_lower = platform.lower()
    if platform_lower not in resources_map:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Plataforma '{platform}' não encontrada. Use: shopify, vtex, loja_integrada"
        )
    
    return {
        "platform": platform_lower,
        "resources": resources_map[platform_lower]
    }
