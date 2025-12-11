# services/data_ingestion_api/connectors/abstract_connector.py

from abc import ABC, abstractmethod
from typing import Any

# O conector abstrato deve usar a CredencialBase do vizu_models (ou do schemas.py da API)
# Vamos assumir que ele recebe um dicionário de credenciais que ele DEVE obter do Secret Manager.

# --- CLASSE DE EXCEÇÃO (FUNDAMENTAL PARA MODULARIZAÇÃO/TESTABILIDADE) ---
class ExecutionError(Exception):
    """Exceção personalizada para erros de execução em conectores de dados (Padrão Vizu)."""
    pass

class AbstractDataConnector(ABC):
    """
    Classe Abstrata Base para todos os conectores de dados Enterprise.
    Garante o princípio de Agnósticismo e Testabilidade, definindo um contrato
    comum para todas as fontes de dados.
    """

    def __init__(self, credentials: dict[str, Any]):
        """Inicializa o conector com as credenciais (que vieram do Secret Manager)."""
        self.credentials = credentials

    @abstractmethod
    async def validate_connection(self) -> bool:
        """
        Tenta estabelecer uma conexão rápida com a fonte de dados.
        CRÍTICO: Deve ser a primeira ação assíncrona após receber as credenciais.
        """
        raise NotImplementedError

    @abstractmethod
    async def fetch_schema(self) -> list[dict[str, Any]]:
        """
        Busca e retorna o schema (tabelas, colunas, tipos) da fonte de dados.
        """
        raise NotImplementedError

    @abstractmethod
    async def extract_data(self, query: str, client_id: str) -> list[dict[str, Any]]:
        """
        Executa a query e extrai a massa de dados (passo do pipeline de ETL).
        """
        raise NotImplementedError

    @abstractmethod
    def get_connection_string(self) -> str:
        """
        Gera a string de conexão segura (sem expor credenciais em logs).
        """
        raise NotImplementedError
