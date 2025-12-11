"""
Cliente Supabase para o serviço de Data Ingestion.
Gerencia conexões e operações com o banco de dados Supabase.
"""

import logging
import os
from typing import Any, Optional

from supabase import Client, create_client

logger = logging.getLogger(__name__)


class SupabaseClient:
    """
    Cliente singleton para operações com Supabase.
    Usa as credenciais do ambiente para se conectar.
    """

    _instance: Optional["SupabaseClient"] = None
    _client: Client | None = None

    def __new__(cls) -> "SupabaseClient":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if self._client is None:
            self._initialize_client()

    def _initialize_client(self):
        """Inicializa o cliente Supabase com credenciais do ambiente."""
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_KEY")

        if not url or not key:
            logger.warning("SUPABASE_URL ou SUPABASE_KEY não configurados. Cliente não inicializado.")
            return

        try:
            self._client = create_client(url, key)
            logger.info(f"Cliente Supabase inicializado: {url}")
        except Exception as e:
            logger.error(f"Erro ao inicializar cliente Supabase: {e}")
            raise

    @property
    def client(self) -> Client | None:
        """Retorna o cliente Supabase."""
        return self._client

    def is_connected(self) -> bool:
        """Verifica se o cliente está conectado."""
        return self._client is not None

    # --- Operações CRUD genéricas ---

    async def insert(self, table: str, data: dict[str, Any]) -> dict[str, Any]:
        """
        Insere um registro em uma tabela.
        
        Args:
            table: Nome da tabela
            data: Dados a serem inseridos
            
        Returns:
            Registro inserido
        """
        if not self._client:
            raise RuntimeError("Cliente Supabase não inicializado")

        result = self._client.table(table).insert(data).execute()
        return result.data[0] if result.data else {}

    async def upsert(self, table: str, data: dict[str, Any], on_conflict: str = "id") -> dict[str, Any]:
        """
        Insere ou atualiza um registro (upsert).
        
        Args:
            table: Nome da tabela
            data: Dados a serem inseridos/atualizados
            on_conflict: Coluna(s) para verificar conflito
            
        Returns:
            Registro inserido/atualizado
        """
        if not self._client:
            raise RuntimeError("Cliente Supabase não inicializado")

        result = self._client.table(table).upsert(data, on_conflict=on_conflict).execute()
        return result.data[0] if result.data else {}

    async def select(
        self,
        table: str,
        columns: str = "*",
        filters: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        """
        Busca registros de uma tabela.
        
        Args:
            table: Nome da tabela
            columns: Colunas a retornar (padrão: todas)
            filters: Filtros de busca {coluna: valor}
            
        Returns:
            Lista de registros
        """
        if not self._client:
            raise RuntimeError("Cliente Supabase não inicializado")

        query = self._client.table(table).select(columns)

        if filters:
            for col, val in filters.items():
                query = query.eq(col, val)

        result = query.execute()
        return result.data or []

    async def select_one(
        self,
        table: str,
        columns: str = "*",
        filters: dict[str, Any] | None = None
    ) -> dict[str, Any] | None:
        """
        Busca um único registro.
        
        Args:
            table: Nome da tabela
            columns: Colunas a retornar
            filters: Filtros de busca
            
        Returns:
            Registro encontrado ou None
        """
        results = await self.select(table, columns, filters)
        return results[0] if results else None

    async def update(
        self,
        table: str,
        data: dict[str, Any],
        filters: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """
        Atualiza registros em uma tabela.
        
        Args:
            table: Nome da tabela
            data: Dados a serem atualizados
            filters: Filtros para selecionar registros
            
        Returns:
            Registros atualizados
        """
        if not self._client:
            raise RuntimeError("Cliente Supabase não inicializado")

        query = self._client.table(table).update(data)

        for col, val in filters.items():
            query = query.eq(col, val)

        result = query.execute()
        return result.data or []

    async def delete(self, table: str, filters: dict[str, Any]) -> list[dict[str, Any]]:
        """
        Deleta registros de uma tabela.
        
        Args:
            table: Nome da tabela
            filters: Filtros para selecionar registros a deletar
            
        Returns:
            Registros deletados
        """
        if not self._client:
            raise RuntimeError("Cliente Supabase não inicializado")

        query = self._client.table(table).delete()

        for col, val in filters.items():
            query = query.eq(col, val)

        result = query.execute()
        return result.data or []


# Instância global (singleton)
supabase_client = SupabaseClient()
