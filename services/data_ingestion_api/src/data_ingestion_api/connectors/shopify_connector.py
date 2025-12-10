"""
Conector para integração com Shopify.
Utiliza a API REST do Shopify para extração de dados.

Documentação da API: https://shopify.dev/docs/api/admin-rest
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
import logging

from data_ingestion_api.connectors.ecommerce_base_connector import (
    EcommerceBaseConnector,
    AuthenticationError,
    EcommerceConnectorError
)

logger = logging.getLogger(__name__)


class ShopifyConnector(EcommerceBaseConnector):
    """
    Conector para Shopify usando a API REST Admin.
    
    Credenciais necessárias:
    - shop_name: Nome da loja (ex: "minha-loja" para minha-loja.myshopify.com)
    - api_key: Chave da API (App API Key)
    - api_secret: Segredo da API (App API Secret) - Opcional para algumas operações
    - access_token: Token de acesso OAuth ou Private App Token
    - api_version: Versão da API (ex: "2024-01")
    """
    
    API_VERSION_DEFAULT = "2024-01"
    
    def __init__(self, credentials: Dict[str, Any]):
        """
        Inicializa o conector Shopify.
        
        Args:
            credentials: Dicionário com as credenciais do Shopify
        """
        super().__init__(credentials)
        
        self.shop_name = credentials.get("shop_name")
        self.access_token = credentials.get("access_token")
        self.api_version = credentials.get("api_version", self.API_VERSION_DEFAULT)
        
        if not self.shop_name or not self.access_token:
            raise AuthenticationError("shop_name e access_token são obrigatórios")
        
        # Configura a URL base e headers
        self.base_url = f"https://{self.shop_name}.myshopify.com/admin/api/{self.api_version}"
        self.headers = {
            "X-Shopify-Access-Token": self.access_token,
            "Content-Type": "application/json"
        }
        
        logger.info(f"ShopifyConnector inicializado para loja: {self.shop_name}")
    
    async def validate_connection(self) -> bool:
        """
        Valida a conexão com a API do Shopify.
        Faz uma requisição simples para verificar as credenciais.
        """
        try:
            # Tenta buscar informações da loja
            response = await self._make_request("GET", "/shop.json")
            shop_info = response.get("shop", {})
            logger.info(f"Conexão validada - Loja: {shop_info.get('name')}")
            return True
        except Exception as e:
            logger.error(f"Falha na validação de conexão Shopify: {e}")
            return False
    
    async def get_products(
        self,
        limit: int = 100,
        page: Optional[int] = None,
        updated_since: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """
        Busca produtos do Shopify.
        
        O Shopify usa paginação baseada em cursor (page_info) para grandes volumes,
        mas também suporta limit/page para conjuntos menores.
        """
        params: Dict[str, Any] = {"limit": min(limit, 250)}  # Shopify max = 250
        
        if updated_since:
            params["updated_at_min"] = updated_since.isoformat()
        
        # Para paginação, Shopify usa cursor-based pagination
        # Por simplicidade, usamos o parâmetro since_id para paginação
        if page and page > 1:
            # Em produção, usar cursor pagination com page_info
            params["page"] = page
        
        response = await self._make_request("GET", "/products.json", params=params)
        return response.get("products", [])
    
    async def get_orders(
        self,
        limit: int = 100,
        page: Optional[int] = None,
        status: Optional[str] = None,
        created_since: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """
        Busca pedidos do Shopify.
        
        Status possíveis: open, closed, cancelled, any
        """
        params: Dict[str, Any] = {"limit": min(limit, 250)}
        
        if status:
            params["status"] = status
        else:
            params["status"] = "any"  # Por padrão, busca todos
            
        if created_since:
            params["created_at_min"] = created_since.isoformat()
        
        response = await self._make_request("GET", "/orders.json", params=params)
        return response.get("orders", [])
    
    async def get_customers(
        self,
        limit: int = 100,
        page: Optional[int] = None,
        updated_since: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """
        Busca clientes do Shopify.
        """
        params: Dict[str, Any] = {"limit": min(limit, 250)}
        
        if updated_since:
            params["updated_at_min"] = updated_since.isoformat()
        
        response = await self._make_request("GET", "/customers.json", params=params)
        return response.get("customers", [])
    
    async def get_inventory(
        self,
        limit: int = 100,
        page: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Busca dados de estoque do Shopify.
        
        O Shopify usa um modelo de Inventory Levels e Inventory Items.
        Primeiro precisamos buscar os locations, depois os níveis de estoque.
        """
        # Busca as localizações de estoque
        locations_response = await self._make_request("GET", "/locations.json")
        locations = locations_response.get("locations", [])
        
        if not locations:
            return []
        
        # Busca os níveis de estoque para cada localização
        inventory_data = []
        for location in locations:
            location_id = location.get("id")
            params = {
                "limit": min(limit, 250),
                "location_ids": location_id
            }
            
            response = await self._make_request("GET", "/inventory_levels.json", params=params)
            levels = response.get("inventory_levels", [])
            
            for level in levels:
                level["location_name"] = location.get("name")
                level["location_address"] = location.get("address1")
                inventory_data.append(level)
        
        return inventory_data
    
    async def get_collections(
        self,
        limit: int = 100,
        page: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Busca coleções (categorias) do Shopify.
        Inclui Smart Collections e Custom Collections.
        """
        params: Dict[str, Any] = {"limit": min(limit, 250)}
        
        # Busca Custom Collections
        custom_response = await self._make_request("GET", "/custom_collections.json", params=params)
        custom_collections = custom_response.get("custom_collections", [])
        
        # Busca Smart Collections
        smart_response = await self._make_request("GET", "/smart_collections.json", params=params)
        smart_collections = smart_response.get("smart_collections", [])
        
        # Combina as duas listas, adicionando um campo de tipo
        for c in custom_collections:
            c["collection_type"] = "custom"
        for c in smart_collections:
            c["collection_type"] = "smart"
        
        return custom_collections + smart_collections
    
    async def get_order_details(self, order_id: int) -> Dict[str, Any]:
        """
        Busca detalhes completos de um pedido específico.
        """
        response = await self._make_request("GET", f"/orders/{order_id}.json")
        return response.get("order", {})
    
    async def get_product_variants(self, product_id: int) -> List[Dict[str, Any]]:
        """
        Busca variantes de um produto específico.
        """
        response = await self._make_request("GET", f"/products/{product_id}/variants.json")
        return response.get("variants", [])
    
    async def get_metafields(
        self, 
        resource_type: str, 
        resource_id: int
    ) -> List[Dict[str, Any]]:
        """
        Busca metafields de um recurso (produto, cliente, pedido, etc.).
        
        Args:
            resource_type: Tipo do recurso (products, customers, orders)
            resource_id: ID do recurso
        """
        endpoint = f"/{resource_type}/{resource_id}/metafields.json"
        response = await self._make_request("GET", endpoint)
        return response.get("metafields", [])
    
    def get_connection_string(self) -> str:
        """Retorna string de conexão segura."""
        return f"shopify://{self.shop_name}.myshopify.com/api/{self.api_version}"
