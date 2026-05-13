"""
Conector para integração com Conta Azul API v2.
Utiliza OAuth2 ROPC grant para autenticação.

Credenciais do app (variáveis de ambiente):
  CONTA_AZUL_CLIENT_ID / CONTA_AZUL_CLIENT_SECRET

O usuário fornece apenas username (e-mail) e password da conta Conta Azul.

Documentação: https://api-v2.contaazul.com
"""

import logging
import os
from datetime import date, datetime, timedelta
from typing import Any

import httpx

from blu_data_connectors.base.abstract_connector import AbstractDataConnector, ExecutionError

logger = logging.getLogger(__name__)

TOKEN_URL = "https://auth.contaazul.com/oauth2/token"
BASE_URL = "https://api-v2.contaazul.com"

# NFS-e endpoint enforces a max 15-day window per request
NFSE_MAX_WINDOW_DAYS = 15
# Default lookback when extract_data is called without explicit dates
DEFAULT_LOOKBACK_DAYS = 365
# Page size (API supports 10, 20, 50, 100)
PAGE_SIZE = 100


class AuthenticationError(Exception):
    pass


def _to_date(value: Any) -> date:
    if isinstance(value, date):
        return value
    return datetime.strptime(str(value), "%Y-%m-%d").date()


def _date_chunks(start: date, end: date, chunk_days: int):
    """Yield (chunk_start, chunk_end) pairs covering [start, end]."""
    cursor = start
    while cursor <= end:
        yield cursor, min(cursor + timedelta(days=chunk_days - 1), end)
        cursor += timedelta(days=chunk_days)


class ContaAzulConnector(AbstractDataConnector):
    """
    Conector para Conta Azul usando a API v2 REST com OAuth2 ROPC grant.

    Credenciais necessárias (fornecidas pelo usuário):
    - username: E-mail de login no Conta Azul
    - password: Senha do Conta Azul

    Credenciais do app (via variáveis de ambiente):
    - CONTA_AZUL_CLIENT_ID
    - CONTA_AZUL_CLIENT_SECRET
    """

    def __init__(self, credentials: dict[str, Any]):
        super().__init__(credentials)

        self.username = credentials.get("username")
        self.password = credentials.get("password")

        if not self.username or not self.password:
            raise AuthenticationError("username e password são obrigatórios")

        self._client_id = os.environ.get("CONTA_AZUL_CLIENT_ID")
        self._client_secret = os.environ.get("CONTA_AZUL_CLIENT_SECRET")

        if not self._client_id or not self._client_secret:
            raise AuthenticationError(
                "CONTA_AZUL_CLIENT_ID e CONTA_AZUL_CLIENT_SECRET devem estar configurados"
            )

        self._access_token: str | None = None
        logger.info("ContaAzulConnector inicializado para usuário: %s", self.username)

    async def _get_token(self) -> str:
        """Troca username/password por access_token via ROPC grant."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                TOKEN_URL,
                data={
                    "grant_type": "password",
                    "username": self.username,
                    "password": self.password,
                    "client_id": self._client_id,
                    "client_secret": self._client_secret,
                },
            )
            response.raise_for_status()
            return response.json()["access_token"]

    async def _ensure_token(self) -> str:
        if not self._access_token:
            self._access_token = await self._get_token()
        return self._access_token

    async def _get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        token = await self._ensure_token()
        url = f"{BASE_URL}{path}"
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
        }
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.get(url, headers=headers, params=params)
            response.raise_for_status()
            return response.json()

    async def _paginate(self, path: str, params: dict[str, Any]) -> list[dict[str, Any]]:
        """Fetch all pages for a paginated endpoint, returning the full `itens` list."""
        all_items: list[dict[str, Any]] = []
        page = 1
        while True:
            data = await self._get(path, {**params, "pagina": page, "tamanho": PAGE_SIZE})
            items = data.get("itens", [])
            all_items.extend(items)
            paginacao = data.get("paginacao", {})
            total_pages = paginacao.get("total_paginas", 1)
            if page >= total_pages:
                break
            page += 1
        return all_items

    async def validate_connection(self) -> bool:
        """Valida a conexão tentando autenticar e fazendo uma chamada mínima."""
        try:
            today = date.today().isoformat()
            await self._get(
                "/v1/notas-fiscais",
                {"data_inicial": today, "data_final": today, "pagina": 1, "tamanho": 10},
            )
            logger.info("Conexão Conta Azul validada com sucesso")
            return True
        except Exception as e:
            logger.error("Falha na validação de conexão Conta Azul: %s", e)
            return False

    async def get_notas_fiscais(
        self,
        data_inicial: date | str,
        data_final: date | str,
    ) -> list[dict[str, Any]]:
        """
        Extrai NF-e do período [data_inicial, data_final].
        Pagina automaticamente; sem limite de janela no NF-e endpoint.
        """
        start = _to_date(data_inicial)
        end = _to_date(data_final)
        return await self._paginate(
            "/v1/notas-fiscais",
            {"data_inicial": start.isoformat(), "data_final": end.isoformat()},
        )

    async def get_notas_fiscais_servico(
        self,
        data_inicial: date | str,
        data_final: date | str,
    ) -> list[dict[str, Any]]:
        """
        Extrai NFS-e do período [data_inicial, data_final].
        A API limita a janela de competência a 15 dias por requisição;
        este método divide o intervalo em chunks automaticamente.
        """
        start = _to_date(data_inicial)
        end = _to_date(data_final)
        all_items: list[dict[str, Any]] = []

        for chunk_start, chunk_end in _date_chunks(start, end, NFSE_MAX_WINDOW_DAYS):
            chunk_items = await self._paginate(
                "/v1/notas-fiscais-servico",
                {
                    "data_competencia_de": chunk_start.isoformat(),
                    "data_competencia_ate": chunk_end.isoformat(),
                },
            )
            all_items.extend(chunk_items)
            logger.debug(
                "NFS-e chunk %s–%s: %d registros",
                chunk_start,
                chunk_end,
                len(chunk_items),
            )

        return all_items

    async def fetch_schema(self) -> list[dict[str, Any]]:
        return [
            {
                "resource": "notas_fiscais",
                "fields": [
                    "id", "numero", "serie", "chave_acesso", "data_emissao",
                    "valor_total", "status", "natureza_operacao", "cfop",
                    "cnpj_emitente", "nome_emitente",
                    "cnpj_destinatario", "nome_destinatario",
                ],
            },
            {
                "resource": "notas_fiscais_servico",
                "fields": [
                    "id", "numero", "data_emissao", "data_competencia",
                    "valor_servico", "valor_total_nfse", "status",
                    "discriminacao_servico", "codigo_servico",
                    "documento_tomador", "nome_tomador",
                    "cnpj_prestador", "nome_prestador",
                ],
            },
        ]

    async def extract_data(self, query: str, client_id: str) -> list[dict[str, Any]]:
        """
        Extrai dados de notas fiscais.

        query pode ser:
        - "notas_fiscais"         → NF-e do último ano
        - "notas_fiscais_servico" → NFS-e do último ano (com chunking automático)
        - "all"                   → NF-e + NFS-e do último ano, combinados
        """
        end = date.today()
        start = end - timedelta(days=DEFAULT_LOOKBACK_DAYS)

        if query == "notas_fiscais":
            return await self.get_notas_fiscais(start, end)

        if query == "notas_fiscais_servico":
            return await self.get_notas_fiscais_servico(start, end)

        if query == "all":
            nfe = await self.get_notas_fiscais(start, end)
            nfse = await self.get_notas_fiscais_servico(start, end)
            return nfe + nfse

        raise ExecutionError(f"Query não suportada: {query}. Use 'notas_fiscais', 'notas_fiscais_servico' ou 'all'.")

    def get_connection_string(self) -> str:
        return f"conta_azul://{self.username}@api-v2.contaazul.com/v1"
