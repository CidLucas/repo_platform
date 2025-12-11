"""
Conector para integração com Loja Integrada.
Utiliza a API REST da Loja Integrada para extração de dados.

Documentação da API: https://lojaintegrada.docs.apiary.io/
"""

import logging
from datetime import datetime
from typing import Any

from data_ingestion_api.connectors.ecommerce_base_connector import (
    AuthenticationError,
    EcommerceBaseConnector,
)

logger = logging.getLogger(__name__)


class LojaIntegradaConnector(EcommerceBaseConnector):
    """
    Conector para Loja Integrada usando a API REST.
    
    Credenciais necessárias:
    - api_key: Chave da API (disponível no painel da loja)
    - application_key: Chave da aplicação (para apps parceiros) - opcional
    """

    API_BASE_URL = "https://api.lojaintegrada.com.br/api/v1"

    def __init__(self, credentials: dict[str, Any]):
        """
        Inicializa o conector Loja Integrada.
        
        Args:
            credentials: Dicionário com as credenciais da Loja Integrada
        """
        super().__init__(credentials)

        self.api_key = credentials.get("api_key")
        self.application_key = credentials.get("application_key")

        if not self.api_key:
            raise AuthenticationError("api_key é obrigatório")

        self.base_url = self.API_BASE_URL

        # Headers de autenticação Loja Integrada
        self.headers = {
            "Authorization": f"chave_api {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

        # Adiciona Application Key se fornecida (para apps parceiros)
        if self.application_key:
            self.headers["chave_aplicacao"] = self.application_key

        logger.info("LojaIntegradaConnector inicializado")

    async def validate_connection(self) -> bool:
        """
        Valida a conexão com a API da Loja Integrada.
        """
        try:
            # Tenta buscar informações de categorias como teste
            response = await self._make_request("GET", "/categoria")
            logger.info("Conexão Loja Integrada validada com sucesso")
            return True
        except Exception as e:
            logger.error(f"Falha na validação de conexão Loja Integrada: {e}")
            return False

    async def get_products(
        self,
        limit: int = 100,
        page: int | None = None,
        updated_since: datetime | None = None
    ) -> list[dict[str, Any]]:
        """
        Busca produtos da Loja Integrada.
        
        A API usa paginação baseada em offset.
        """
        params: dict[str, Any] = {
            "limit": min(limit, 50),  # Loja Integrada max = 50
            "offset": ((page or 1) - 1) * limit
        }

        if updated_since:
            params["modificado_apos"] = updated_since.strftime("%Y-%m-%d")

        response = await self._make_request("GET", "/produto", params=params)

        # A resposta contém um campo "objects" com a lista de produtos
        products = response.get("objects", [])

        # Busca detalhes completos de cada produto
        detailed_products = []
        for product_summary in products:
            product_id = product_summary.get("id")
            if product_id:
                try:
                    product_detail = await self._make_request(
                        "GET",
                        f"/produto/{product_id}"
                    )
                    detailed_products.append(product_detail)
                except Exception as e:
                    logger.warning(f"Erro ao buscar detalhes do produto {product_id}: {e}")
                    detailed_products.append(product_summary)

        return detailed_products

    async def get_orders(
        self,
        limit: int = 100,
        page: int | None = None,
        status: str | None = None,
        created_since: datetime | None = None
    ) -> list[dict[str, Any]]:
        """
        Busca pedidos da Loja Integrada.
        
        Status possíveis: 
        - pedido_pago
        - pedido_pendente
        - pedido_cancelado
        - pedido_em_andamento
        - pedido_entregue
        """
        params: dict[str, Any] = {
            "limit": min(limit, 50),
            "offset": ((page or 1) - 1) * limit
        }

        if status:
            params["situacao__codigo"] = status

        if created_since:
            params["data_criacao__gte"] = created_since.strftime("%Y-%m-%d")

        response = await self._make_request("GET", "/pedido", params=params)
        orders = response.get("objects", [])

        # Busca detalhes completos de cada pedido
        detailed_orders = []
        for order_summary in orders:
            order_number = order_summary.get("numero")
            if order_number:
                try:
                    order_detail = await self._make_request(
                        "GET",
                        f"/pedido/{order_number}"
                    )
                    detailed_orders.append(order_detail)
                except Exception as e:
                    logger.warning(f"Erro ao buscar detalhes do pedido {order_number}: {e}")
                    detailed_orders.append(order_summary)

        return detailed_orders

    async def get_customers(
        self,
        limit: int = 100,
        page: int | None = None,
        updated_since: datetime | None = None
    ) -> list[dict[str, Any]]:
        """
        Busca clientes da Loja Integrada.
        """
        params: dict[str, Any] = {
            "limit": min(limit, 50),
            "offset": ((page or 1) - 1) * limit
        }

        if updated_since:
            params["modificado_apos"] = updated_since.strftime("%Y-%m-%d")

        response = await self._make_request("GET", "/cliente", params=params)
        customers = response.get("objects", [])

        # Busca detalhes completos de cada cliente
        detailed_customers = []
        for customer_summary in customers:
            customer_id = customer_summary.get("id")
            if customer_id:
                try:
                    customer_detail = await self._make_request(
                        "GET",
                        f"/cliente/{customer_id}"
                    )
                    detailed_customers.append(customer_detail)
                except Exception as e:
                    logger.warning(f"Erro ao buscar detalhes do cliente {customer_id}: {e}")
                    detailed_customers.append(customer_summary)

        return detailed_customers

    async def get_inventory(
        self,
        limit: int = 100,
        page: int | None = None
    ) -> list[dict[str, Any]]:
        """
        Busca dados de estoque da Loja Integrada.
        
        O estoque na Loja Integrada está associado às variações de produto.
        """
        # Busca produtos com suas variações
        products = await self.get_products(limit=limit, page=page)

        inventory_data = []
        for product in products:
            product_id = product.get("id")
            product_name = product.get("nome")

            # Busca variações do produto
            try:
                variations_response = await self._make_request(
                    "GET",
                    "/produto_variacao",
                    params={"produto": product_id, "limit": 50}
                )
                variations = variations_response.get("objects", [])

                for variation in variations:
                    inventory_data.append({
                        "product_id": product_id,
                        "product_name": product_name,
                        "variation_id": variation.get("id"),
                        "variation_sku": variation.get("sku"),
                        "variation_name": variation.get("nome"),
                        "quantity": variation.get("estoque_quantidade", 0),
                        "min_quantity": variation.get("estoque_minimo", 0),
                        "manage_stock": variation.get("gerenciar_estoque", True),
                        "price": variation.get("preco_cheio"),
                        "promotional_price": variation.get("preco_promocional")
                    })

            except Exception as e:
                logger.warning(f"Erro ao buscar variações do produto {product_id}: {e}")
                # Se não tem variações, usa estoque do produto principal
                inventory_data.append({
                    "product_id": product_id,
                    "product_name": product_name,
                    "variation_id": None,
                    "variation_sku": product.get("sku"),
                    "variation_name": None,
                    "quantity": product.get("estoque_quantidade", 0),
                    "min_quantity": product.get("estoque_minimo", 0),
                    "manage_stock": product.get("gerenciar_estoque", True),
                    "price": product.get("preco_cheio"),
                    "promotional_price": product.get("preco_promocional")
                })

        return inventory_data

    async def get_categories(
        self,
        limit: int = 100,
        page: int | None = None
    ) -> list[dict[str, Any]]:
        """
        Busca categorias da Loja Integrada.
        """
        params: dict[str, Any] = {
            "limit": min(limit, 50),
            "offset": ((page or 1) - 1) * limit
        }

        response = await self._make_request("GET", "/categoria", params=params)
        return response.get("objects", [])

    async def get_brands(
        self,
        limit: int = 100,
        page: int | None = None
    ) -> list[dict[str, Any]]:
        """
        Busca marcas cadastradas na Loja Integrada.
        """
        params: dict[str, Any] = {
            "limit": min(limit, 50),
            "offset": ((page or 1) - 1) * limit
        }

        response = await self._make_request("GET", "/marca", params=params)
        return response.get("objects", [])

    async def get_shipping_methods(self) -> list[dict[str, Any]]:
        """
        Busca métodos de envio configurados na loja.
        """
        response = await self._make_request("GET", "/forma_envio")
        return response.get("objects", [])

    async def get_payment_methods(self) -> list[dict[str, Any]]:
        """
        Busca métodos de pagamento configurados na loja.
        """
        response = await self._make_request("GET", "/forma_pagamento")
        return response.get("objects", [])

    async def get_order_statuses(self) -> list[dict[str, Any]]:
        """
        Busca todos os status de pedido disponíveis.
        """
        response = await self._make_request("GET", "/situacao")
        return response.get("objects", [])

    async def get_product_images(self, product_id: int) -> list[dict[str, Any]]:
        """
        Busca imagens de um produto específico.
        """
        params = {"produto": product_id}
        response = await self._make_request("GET", "/produto_imagem", params=params)
        return response.get("objects", [])

    def get_connection_string(self) -> str:
        """Retorna string de conexão segura."""
        return f"lojaintegrada://{self.API_BASE_URL}"
