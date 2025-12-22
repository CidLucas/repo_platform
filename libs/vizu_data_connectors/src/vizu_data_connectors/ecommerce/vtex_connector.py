"""
Conector para integração com VTEX.
Utiliza a API REST da VTEX para extração de dados.

Documentação da API: https://developers.vtex.com/docs/api-reference
"""

import logging
from datetime import datetime
from typing import Any

from vizu_data_connectors.base.ecommerce_base_connector import (
    AuthenticationError,
    EcommerceBaseConnector,
)

logger = logging.getLogger(__name__)


class VTEXConnector(EcommerceBaseConnector):
    """
    Conector para VTEX usando a API REST.

    Credenciais necessárias:
    - account_name: Nome da conta VTEX (ex: "minhaloja")
    - environment: Ambiente (vtexcommercestable ou vtexcommercebeta)
    - app_key: Chave da aplicação (X-VTEX-API-AppKey)
    - app_token: Token da aplicação (X-VTEX-API-AppToken)
    """

    def __init__(self, credentials: dict[str, Any]):
        """
        Inicializa o conector VTEX.

        Args:
            credentials: Dicionário com as credenciais da VTEX
        """
        super().__init__(credentials)

        self.account_name = credentials.get("account_name")
        self.environment = credentials.get("environment", "vtexcommercestable")
        self.app_key = credentials.get("app_key")
        self.app_token = credentials.get("app_token")

        if not all([self.account_name, self.app_key, self.app_token]):
            raise AuthenticationError("account_name, app_key e app_token são obrigatórios")

        # VTEX usa diferentes URLs para diferentes APIs
        self.base_url = f"https://{self.account_name}.{self.environment}.com.br"

        # Headers de autenticação VTEX
        self.headers = {
            "X-VTEX-API-AppKey": self.app_key,
            "X-VTEX-API-AppToken": self.app_token,
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

        logger.info(f"VTEXConnector inicializado para conta: {self.account_name}")

    async def validate_connection(self) -> bool:
        """
        Valida a conexão com a API da VTEX.
        """
        try:
            # Tenta buscar informações do catálogo
            response = await self._make_request(
                "GET",
                "/api/catalog_system/pvt/category/tree/1"
            )
            logger.info("Conexão VTEX validada com sucesso")
            return True
        except Exception as e:
            logger.error(f"Falha na validação de conexão VTEX: {e}")
            return False

    async def get_products(
        self,
        limit: int = 100,
        page: int | None = None,
        updated_since: datetime | None = None
    ) -> list[dict[str, Any]]:
        """
        Busca produtos do catálogo VTEX.

        VTEX usa um sistema de SKUs e Produtos. Um produto pode ter múltiplos SKUs.
        """
        params: dict[str, Any] = {
            "_from": ((page or 1) - 1) * limit,
            "_to": ((page or 1) - 1) * limit + limit - 1
        }

        # Busca lista de produtos
        response = await self._make_request(
            "GET",
            "/api/catalog_system/pvt/products/GetProductAndSkuIds",
            params=params
        )

        product_ids = response.get("data", {}).keys() if isinstance(response.get("data"), dict) else []

        products = []
        for product_id in list(product_ids)[:limit]:
            try:
                product_detail = await self._make_request(
                    "GET",
                    f"/api/catalog_system/pvt/products/ProductGet/{product_id}"
                )
                products.append(product_detail)
            except Exception as e:
                logger.warning(f"Erro ao buscar produto {product_id}: {e}")

        return products

    async def get_orders(
        self,
        limit: int = 100,
        page: int | None = None,
        status: str | None = None,
        created_since: datetime | None = None
    ) -> list[dict[str, Any]]:
        """
        Busca pedidos da VTEX usando a API OMS (Order Management System).
        """
        params: dict[str, Any] = {
            "page": page or 1,
            "per_page": min(limit, 100)  # VTEX max = 100
        }

        if status:
            params["f_status"] = status

        if created_since:
            params["f_creationDate"] = f"creationDate:[{created_since.isoformat()} TO *]"

        response = await self._make_request(
            "GET",
            "/api/oms/pvt/orders",
            params=params
        )

        orders = response.get("list", [])

        # Busca detalhes completos de cada pedido
        detailed_orders = []
        for order_summary in orders:
            order_id = order_summary.get("orderId")
            if order_id:
                try:
                    order_detail = await self._make_request(
                        "GET",
                        f"/api/oms/pvt/orders/{order_id}"
                    )
                    detailed_orders.append(order_detail)
                except Exception as e:
                    logger.warning(f"Erro ao buscar detalhes do pedido {order_id}: {e}")
                    detailed_orders.append(order_summary)

        return detailed_orders

    async def get_customers(
        self,
        limit: int = 100,
        page: int | None = None,
        updated_since: datetime | None = None
    ) -> list[dict[str, Any]]:
        """
        Busca clientes da VTEX usando a API Master Data.

        VTEX armazena dados de clientes no Master Data (entidade CL).
        """
        params: dict[str, Any] = {
            "_fields": "_all",
            "_sort": "createdIn DESC"
        }

        # Paginação via scroll
        scroll_id = None
        if page and page > 1:
            params["_from"] = (page - 1) * limit
            params["_to"] = page * limit - 1
        else:
            params["_from"] = 0
            params["_to"] = limit - 1

        if updated_since:
            params["_where"] = f"updatedIn>{updated_since.isoformat()}"

        response = await self._make_request(
            "GET",
            "/api/dataentities/CL/search",
            params=params
        )

        # Response é uma lista direta
        return response if isinstance(response, list) else []

    async def get_inventory(
        self,
        limit: int = 100,
        page: int | None = None
    ) -> list[dict[str, Any]]:
        """
        Busca dados de estoque da VTEX usando a API Logistics.
        """
        # Primeiro, busca os SKUs
        products = await self.get_products(limit=limit, page=page)

        inventory_data = []
        for product in products:
            sku_ids = product.get("skuIds", [])
            for sku_id in sku_ids:
                try:
                    response = await self._make_request(
                        "GET",
                        f"/api/logistics/pvt/inventory/skus/{sku_id}"
                    )

                    # Processa os warehouses
                    for balance in response.get("balance", []):
                        inventory_data.append({
                            "sku_id": sku_id,
                            "product_id": product.get("Id"),
                            "product_name": product.get("Name"),
                            "warehouse_id": balance.get("warehouseId"),
                            "warehouse_name": balance.get("warehouseName"),
                            "total_quantity": balance.get("totalQuantity"),
                            "reserved_quantity": balance.get("reservedQuantity"),
                            "available_quantity": balance.get("availableQuantity"),
                            "is_unlimited": balance.get("isUnlimitedQuantity", False)
                        })
                except Exception as e:
                    logger.warning(f"Erro ao buscar estoque do SKU {sku_id}: {e}")

        return inventory_data

    async def get_categories(
        self,
        depth: int = 10
    ) -> list[dict[str, Any]]:
        """
        Busca a árvore de categorias da VTEX.

        Args:
            depth: Profundidade máxima da árvore (1-10)
        """
        response = await self._make_request(
            "GET",
            f"/api/catalog_system/pub/category/tree/{min(depth, 10)}"
        )
        return response if isinstance(response, list) else []

    async def get_brands(self) -> list[dict[str, Any]]:
        """
        Busca todas as marcas cadastradas na VTEX.
        """
        response = await self._make_request(
            "GET",
            "/api/catalog_system/pvt/brand/list"
        )
        return response if isinstance(response, list) else []

    async def get_sku_details(self, sku_id: int) -> dict[str, Any]:
        """
        Busca detalhes completos de um SKU.
        """
        response = await self._make_request(
            "GET",
            f"/api/catalog_system/pvt/sku/stockkeepingunitbyid/{sku_id}"
        )
        return response

    async def get_price(self, sku_id: int) -> dict[str, Any]:
        """
        Busca informações de preço de um SKU.
        """
        response = await self._make_request(
            "GET",
            f"/api/pricing/prices/{sku_id}"
        )
        return response

    async def search_products(
        self,
        query: str,
        limit: int = 50
    ) -> list[dict[str, Any]]:
        """
        Busca produtos por texto usando a API de busca.
        """
        params = {
            "ft": query,
            "_from": 0,
            "_to": limit - 1
        }

        response = await self._make_request(
            "GET",
            "/api/catalog_system/pub/products/search",
            params=params
        )
        return response if isinstance(response, list) else []

    def get_connection_string(self) -> str:
        """Retorna string de conexão segura."""
        return f"vtex://{self.account_name}.{self.environment}.com.br"
