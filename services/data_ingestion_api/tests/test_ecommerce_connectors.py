"""
Testes para os conectores de e-commerce: Shopify, VTEX e Loja Integrada.

Utiliza mocks para simular as respostas das APIs externas.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from data_ingestion_api.connectors.ecommerce_base_connector import (
    AuthenticationError,
    RateLimitError,
)
from data_ingestion_api.connectors.loja_integrada_connector import LojaIntegradaConnector
from data_ingestion_api.connectors.shopify_connector import ShopifyConnector
from data_ingestion_api.connectors.vtex_connector import VTEXConnector

# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def shopify_credentials():
    return {
        "shop_name": "loja-teste",
        "access_token": "shpat_test_token_123",
        "api_version": "2024-01"
    }


@pytest.fixture
def vtex_credentials():
    return {
        "account_name": "minhaloja",
        "environment": "vtexcommercestable",
        "app_key": "vtexappkey-test-123",
        "app_token": "VTEX_APP_TOKEN_SECRET"
    }


@pytest.fixture
def loja_integrada_credentials():
    return {
        "api_key": "chave_api_loja_integrada_123",
        "application_key": None
    }


# =============================================================================
# Testes do ShopifyConnector
# =============================================================================

class TestShopifyConnector:
    """Testes para o conector Shopify."""

    def test_initialization(self, shopify_credentials):
        """Testa a inicialização correta do conector."""
        connector = ShopifyConnector(shopify_credentials)

        assert connector.shop_name == "loja-teste"
        assert connector.access_token == "shpat_test_token_123"
        assert connector.api_version == "2024-01"
        assert "loja-teste.myshopify.com" in connector.base_url
        assert connector.headers["X-Shopify-Access-Token"] == "shpat_test_token_123"

    def test_initialization_missing_credentials(self):
        """Testa que erro é levantado com credenciais incompletas."""
        with pytest.raises(AuthenticationError):
            ShopifyConnector({"shop_name": "teste"})

        with pytest.raises(AuthenticationError):
            ShopifyConnector({"access_token": "token"})

    @pytest.mark.asyncio
    async def test_validate_connection_success(self, shopify_credentials):
        """Testa validação de conexão bem sucedida."""
        connector = ShopifyConnector(shopify_credentials)

        mock_response = {"shop": {"name": "Loja Teste", "id": 12345}}

        with patch.object(connector, '_make_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response

            result = await connector.validate_connection()

            assert result is True
            mock_request.assert_called_once_with("GET", "/shop.json")

    @pytest.mark.asyncio
    async def test_validate_connection_failure(self, shopify_credentials):
        """Testa validação de conexão com falha."""
        connector = ShopifyConnector(shopify_credentials)

        with patch.object(connector, '_make_request', new_callable=AsyncMock) as mock_request:
            mock_request.side_effect = Exception("Connection failed")

            result = await connector.validate_connection()

            assert result is False

    @pytest.mark.asyncio
    async def test_get_products(self, shopify_credentials):
        """Testa busca de produtos."""
        connector = ShopifyConnector(shopify_credentials)

        mock_products = {
            "products": [
                {"id": 1, "title": "Produto 1", "price": "99.90"},
                {"id": 2, "title": "Produto 2", "price": "149.90"}
            ]
        }

        with patch.object(connector, '_make_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_products

            products = await connector.get_products(limit=50)

            assert len(products) == 2
            assert products[0]["title"] == "Produto 1"

    @pytest.mark.asyncio
    async def test_get_orders(self, shopify_credentials):
        """Testa busca de pedidos."""
        connector = ShopifyConnector(shopify_credentials)

        mock_orders = {
            "orders": [
                {"id": 1001, "total_price": "199.90", "status": "paid"},
                {"id": 1002, "total_price": "299.90", "status": "pending"}
            ]
        }

        with patch.object(connector, '_make_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_orders

            orders = await connector.get_orders(limit=50, status="any")

            assert len(orders) == 2
            mock_request.assert_called_once()

    def test_get_connection_string(self, shopify_credentials):
        """Testa string de conexão segura."""
        connector = ShopifyConnector(shopify_credentials)
        conn_string = connector.get_connection_string()

        assert "shopify://" in conn_string
        assert "loja-teste.myshopify.com" in conn_string
        assert "token" not in conn_string.lower()


# =============================================================================
# Testes do VTEXConnector
# =============================================================================

class TestVTEXConnector:
    """Testes para o conector VTEX."""

    def test_initialization(self, vtex_credentials):
        """Testa a inicialização correta do conector."""
        connector = VTEXConnector(vtex_credentials)

        assert connector.account_name == "minhaloja"
        assert connector.environment == "vtexcommercestable"
        assert connector.app_key == "vtexappkey-test-123"
        assert "minhaloja.vtexcommercestable.com.br" in connector.base_url
        assert connector.headers["X-VTEX-API-AppKey"] == "vtexappkey-test-123"

    def test_initialization_missing_credentials(self):
        """Testa que erro é levantado com credenciais incompletas."""
        with pytest.raises(AuthenticationError):
            VTEXConnector({"account_name": "teste"})

    @pytest.mark.asyncio
    async def test_validate_connection_success(self, vtex_credentials):
        """Testa validação de conexão bem sucedida."""
        connector = VTEXConnector(vtex_credentials)

        mock_response = [{"id": 1, "name": "Categoria 1"}]

        with patch.object(connector, '_make_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response

            result = await connector.validate_connection()

            assert result is True

    @pytest.mark.asyncio
    async def test_get_orders(self, vtex_credentials):
        """Testa busca de pedidos."""
        connector = VTEXConnector(vtex_credentials)

        mock_orders = {
            "list": [
                {"orderId": "v-001", "value": 19990},
                {"orderId": "v-002", "value": 29990}
            ]
        }

        mock_order_detail = {
            "orderId": "v-001",
            "value": 19990,
            "items": [{"name": "Produto X"}]
        }

        with patch.object(connector, '_make_request', new_callable=AsyncMock) as mock_request:
            mock_request.side_effect = [mock_orders, mock_order_detail, mock_order_detail]

            orders = await connector.get_orders(limit=50)

            assert len(orders) == 2

    def test_get_connection_string(self, vtex_credentials):
        """Testa string de conexão segura."""
        connector = VTEXConnector(vtex_credentials)
        conn_string = connector.get_connection_string()

        assert "vtex://" in conn_string
        assert "minhaloja" in conn_string
        assert "token" not in conn_string.lower()


# =============================================================================
# Testes do LojaIntegradaConnector
# =============================================================================

class TestLojaIntegradaConnector:
    """Testes para o conector Loja Integrada."""

    def test_initialization(self, loja_integrada_credentials):
        """Testa a inicialização correta do conector."""
        connector = LojaIntegradaConnector(loja_integrada_credentials)

        assert connector.api_key == "chave_api_loja_integrada_123"
        assert "api.lojaintegrada.com.br" in connector.base_url
        assert "chave_api" in connector.headers["Authorization"]

    def test_initialization_missing_credentials(self):
        """Testa que erro é levantado com credenciais incompletas."""
        with pytest.raises(AuthenticationError):
            LojaIntegradaConnector({})

    @pytest.mark.asyncio
    async def test_validate_connection_success(self, loja_integrada_credentials):
        """Testa validação de conexão bem sucedida."""
        connector = LojaIntegradaConnector(loja_integrada_credentials)

        mock_response = {"objects": [{"id": 1, "nome": "Categoria 1"}]}

        with patch.object(connector, '_make_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response

            result = await connector.validate_connection()

            assert result is True

    @pytest.mark.asyncio
    async def test_get_products(self, loja_integrada_credentials):
        """Testa busca de produtos."""
        connector = LojaIntegradaConnector(loja_integrada_credentials)

        mock_list = {
            "objects": [
                {"id": 1, "nome": "Produto A"},
                {"id": 2, "nome": "Produto B"}
            ]
        }

        mock_detail = {"id": 1, "nome": "Produto A", "preco": "99.90"}

        with patch.object(connector, '_make_request', new_callable=AsyncMock) as mock_request:
            mock_request.side_effect = [mock_list, mock_detail, mock_detail]

            products = await connector.get_products(limit=50)

            assert len(products) == 2

    @pytest.mark.asyncio
    async def test_get_categories(self, loja_integrada_credentials):
        """Testa busca de categorias."""
        connector = LojaIntegradaConnector(loja_integrada_credentials)

        mock_response = {
            "objects": [
                {"id": 1, "nome": "Roupas"},
                {"id": 2, "nome": "Acessórios"}
            ]
        }

        with patch.object(connector, '_make_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response

            categories = await connector.get_categories(limit=50)

            assert len(categories) == 2
            assert categories[0]["nome"] == "Roupas"

    def test_get_connection_string(self, loja_integrada_credentials):
        """Testa string de conexão segura."""
        connector = LojaIntegradaConnector(loja_integrada_credentials)
        conn_string = connector.get_connection_string()

        assert "lojaintegrada://" in conn_string
        assert "api_key" not in conn_string.lower()


# =============================================================================
# Testes de Tratamento de Erros
# =============================================================================

class TestErrorHandling:
    """Testes para tratamento de erros comum a todos os conectores."""

    @pytest.mark.asyncio
    async def test_rate_limit_handling(self, shopify_credentials):
        """Testa tratamento de rate limit."""
        connector = ShopifyConnector(shopify_credentials)

        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_response.headers = {"Retry-After": "60"}

        with patch.object(connector, '_get_client', new_callable=AsyncMock) as mock_client:
            mock_http_client = AsyncMock()
            mock_http_client.request.return_value = mock_response
            mock_client.return_value = mock_http_client

            with pytest.raises(RateLimitError):
                await connector._make_request("GET", "/products.json")

    @pytest.mark.asyncio
    async def test_authentication_error_handling(self, vtex_credentials):
        """Testa tratamento de erro de autenticação."""
        connector = VTEXConnector(vtex_credentials)

        mock_response = MagicMock()
        mock_response.status_code = 401

        with patch.object(connector, '_get_client', new_callable=AsyncMock) as mock_client:
            mock_http_client = AsyncMock()
            mock_http_client.request.return_value = mock_response
            mock_client.return_value = mock_http_client

            with pytest.raises(AuthenticationError):
                await connector._make_request("GET", "/api/catalog_system/pvt/category/tree/1")
