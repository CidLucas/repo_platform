"""
Conector para integração com Conta Azul.
Utiliza a API REST OAuth2 da Conta Azul para extração de dados financeiros.

Documentação da API: https://developers.contaazul.com/docs
"""

import logging
from typing import Any

import httpx

from blu_data_connectors.base.abstract_connector import AbstractDataConnector, ExecutionError

logger = logging.getLogger(__name__)


class AuthenticationError(Exception):
    pass


class ContaAzulConnector(AbstractDataConnector):
    """
    Conector para Conta Azul usando a API REST OAuth2.

    Credenciais necessárias:
    - access_token: Token de acesso OAuth2 (obtido via fluxo de autorização)
    - client_id: ID do cliente OAuth2
    - client_secret: Secret do cliente OAuth2
    """

    BASE_URL = "https://api.contaazul.com/v1"

    def __init__(self, credentials: dict[str, Any]):
        super().__init__(credentials)

        self.access_token = credentials.get("access_token")
        self.client_id = credentials.get("client_id")
        self.client_secret = credentials.get("client_secret")

        if not self.access_token:
            raise AuthenticationError("access_token é obrigatório")
        if not all([self.client_id, self.client_secret]):
            raise AuthenticationError("client_id e client_secret são obrigatórios")

        self.headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        logger.info("ContaAzulConnector inicializado")

    async def _make_request(
        self,
        method: str,
        path: str,
        params: dict[str, Any] | None = None,
    ) -> Any:
        url = f"{self.BASE_URL}{path}"
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.request(
                method, url, headers=self.headers, params=params
            )
            response.raise_for_status()
            return response.json()

    async def validate_connection(self) -> bool:
        try:
            await self._make_request("GET", "/company")
            logger.info("Conexão Conta Azul validada com sucesso")
            return True
        except Exception as e:
            logger.error(f"Falha na validação de conexão Conta Azul: {e}")
            return False

    async def get_invoices(self, limit: int = 100, page: int = 1) -> list[dict[str, Any]]:
        response = await self._make_request(
            "GET",
            "/sales",
            params={"page_size": min(limit, 200), "page": page},
        )
        return response if isinstance(response, list) else response.get("data", [])

    async def get_accounts_payable(self, limit: int = 100, page: int = 1) -> list[dict[str, Any]]:
        response = await self._make_request(
            "GET",
            "/bills",
            params={"page_size": min(limit, 200), "page": page},
        )
        return response if isinstance(response, list) else response.get("data", [])

    async def get_accounts_receivable(self, limit: int = 100, page: int = 1) -> list[dict[str, Any]]:
        response = await self._make_request(
            "GET",
            "/receivables",
            params={"page_size": min(limit, 200), "page": page},
        )
        return response if isinstance(response, list) else response.get("data", [])

    async def fetch_schema(self) -> list[dict[str, Any]]:
        return [
            {
                "resource": "invoices",
                "fields": [
                    "number", "emission_date", "total_value", "status",
                    "customer_name", "customer_cnpj",
                ],
            },
            {
                "resource": "accounts_payable",
                "fields": ["number", "due_date", "value", "status", "supplier_name"],
            },
            {
                "resource": "accounts_receivable",
                "fields": ["number", "due_date", "value", "status", "customer_name"],
            },
        ]

    async def extract_data(self, query: str, client_id: str) -> list[dict[str, Any]]:
        if query == "invoices":
            return await self.get_invoices()
        if query == "accounts_payable":
            return await self.get_accounts_payable()
        if query == "accounts_receivable":
            return await self.get_accounts_receivable()
        raise ExecutionError(f"Query não suportada: {query}")

    def get_connection_string(self) -> str:
        return "conta_azul://api.contaazul.com/v1"
