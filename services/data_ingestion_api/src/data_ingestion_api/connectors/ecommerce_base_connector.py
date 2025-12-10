"""
Base connector para plataformas de e-commerce.
Define a interface comum para extração de dados de lojas virtuais.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, AsyncGenerator
from datetime import datetime
import logging
import httpx
import pandas as pd

from data_ingestion_api.connectors.abstract_connector import AbstractDataConnector, ExecutionError

logger = logging.getLogger(__name__)


class EcommerceConnectorError(Exception):
    """Exceção base para erros de conectores de e-commerce."""
    pass


class RateLimitError(EcommerceConnectorError):
    """Exceção para erros de rate limit da API."""
    pass


class AuthenticationError(EcommerceConnectorError):
    """Exceção para erros de autenticação."""
    pass


class EcommerceBaseConnector(AbstractDataConnector):
    """
    Classe base abstrata para conectores de e-commerce.
    Define métodos comuns para extração de dados de lojas virtuais.
    
    Suporta:
    - Produtos
    - Pedidos
    - Clientes
    - Estoque
    - Categorias
    """
    
    # Recursos padrão suportados por plataformas de e-commerce
    SUPPORTED_RESOURCES = [
        "products",
        "orders", 
        "customers",
        "inventory",
        "categories",
        "collections",
    ]
    
    def __init__(self, credentials: Dict[str, Any]):
        """
        Inicializa o conector de e-commerce.
        
        Args:
            credentials: Dicionário com credenciais específicas da plataforma
        """
        super().__init__(credentials)
        self.base_url: str = ""
        self.headers: Dict[str, str] = {}
        self._client: Optional[httpx.AsyncClient] = None
        
    async def _get_client(self) -> httpx.AsyncClient:
        """Retorna um cliente HTTP assíncrono reutilizável."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=30.0,
                headers=self.headers
            )
        return self._client
    
    async def _close_client(self):
        """Fecha o cliente HTTP."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None
    
    async def _make_request(
        self, 
        method: str,
        endpoint: str, 
        params: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Faz uma requisição HTTP para a API da plataforma.
        
        Args:
            method: Método HTTP (GET, POST, etc.)
            endpoint: Endpoint da API
            params: Parâmetros de query string
            json_data: Corpo da requisição em JSON
            
        Returns:
            Resposta da API em formato de dicionário
        """
        client = await self._get_client()
        url = f"{self.base_url}{endpoint}"
        
        try:
            response = await client.request(
                method=method,
                url=url,
                params=params,
                json=json_data
            )
            
            # Tratamento de rate limit
            if response.status_code == 429:
                retry_after = response.headers.get("Retry-After", "60")
                raise RateLimitError(f"Rate limit atingido. Retry after: {retry_after}s")
            
            # Tratamento de autenticação
            if response.status_code in [401, 403]:
                raise AuthenticationError(f"Erro de autenticação: {response.status_code}")
            
            response.raise_for_status()
            return response.json()
            
        except httpx.HTTPStatusError as e:
            logger.error(f"Erro HTTP: {e.response.status_code} - {e.response.text}")
            raise ExecutionError(f"Erro na requisição: {e}")
        except httpx.RequestError as e:
            logger.error(f"Erro de conexão: {e}")
            raise ExecutionError(f"Erro de conexão: {e}")
    
    # --- Métodos abstratos específicos de e-commerce ---
    
    @abstractmethod
    async def get_products(
        self, 
        limit: int = 100,
        page: Optional[int] = None,
        updated_since: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """
        Busca produtos da loja.
        
        Args:
            limit: Número máximo de produtos por página
            page: Número da página (para paginação)
            updated_since: Filtra produtos atualizados após esta data
            
        Returns:
            Lista de produtos
        """
        raise NotImplementedError
    
    @abstractmethod
    async def get_orders(
        self,
        limit: int = 100,
        page: Optional[int] = None,
        status: Optional[str] = None,
        created_since: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """
        Busca pedidos da loja.
        
        Args:
            limit: Número máximo de pedidos por página
            page: Número da página
            status: Filtro de status do pedido
            created_since: Filtra pedidos criados após esta data
            
        Returns:
            Lista de pedidos
        """
        raise NotImplementedError
    
    @abstractmethod
    async def get_customers(
        self,
        limit: int = 100,
        page: Optional[int] = None,
        updated_since: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """
        Busca clientes da loja.
        
        Args:
            limit: Número máximo de clientes por página
            page: Número da página
            updated_since: Filtra clientes atualizados após esta data
            
        Returns:
            Lista de clientes
        """
        raise NotImplementedError
    
    @abstractmethod
    async def get_inventory(
        self,
        limit: int = 100,
        page: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Busca dados de estoque.
        
        Args:
            limit: Número máximo de itens por página
            page: Número da página
            
        Returns:
            Lista de itens de estoque
        """
        raise NotImplementedError
    
    # --- Implementação dos métodos abstratos do AbstractDataConnector ---
    
    async def fetch_schema(self) -> List[Dict[str, Any]]:
        """
        Retorna o schema dos recursos disponíveis na plataforma.
        """
        return [
            {"resource": resource, "type": "ecommerce_entity"}
            for resource in self.SUPPORTED_RESOURCES
        ]
    
    async def extract_data(
        self, 
        query: str,  # No contexto de e-commerce, query = nome do recurso (products, orders, etc.)
        client_id: str = "",
        chunk_size: int = 100
    ) -> AsyncGenerator[pd.DataFrame, None]:
        """
        Extrai dados do recurso especificado.
        
        Args:
            query: Nome do recurso a ser extraído (products, orders, customers, inventory)
            client_id: ID do cliente Vizu
            chunk_size: Tamanho do chunk para paginação
            
        Yields:
            DataFrame com os dados extraídos
        """
        resource = query.lower().strip()
        
        if resource not in self.SUPPORTED_RESOURCES:
            raise ExecutionError(f"Recurso '{resource}' não suportado. Use: {self.SUPPORTED_RESOURCES}")
        
        page = 1
        has_more = True
        
        while has_more:
            try:
                if resource == "products":
                    data = await self.get_products(limit=chunk_size, page=page)
                elif resource == "orders":
                    data = await self.get_orders(limit=chunk_size, page=page)
                elif resource == "customers":
                    data = await self.get_customers(limit=chunk_size, page=page)
                elif resource == "inventory":
                    data = await self.get_inventory(limit=chunk_size, page=page)
                else:
                    raise ExecutionError(f"Extração para '{resource}' não implementada")
                
                if not data:
                    has_more = False
                    continue
                
                df = pd.DataFrame(data)
                logger.info(f"Extraídos {len(df)} registros de {resource} (página {page})")
                yield df
                
                # Se retornou menos que o chunk_size, não há mais páginas
                if len(data) < chunk_size:
                    has_more = False
                else:
                    page += 1
                    
            except Exception as e:
                logger.error(f"Erro na extração de {resource}: {e}")
                raise ExecutionError(f"Falha na extração de {resource}: {e}")
    
    def get_connection_string(self) -> str:
        """
        Retorna uma string de conexão segura (sem credenciais sensíveis).
        """
        return f"ecommerce://{self.base_url}"
    
    async def __aenter__(self):
        """Context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - fecha o cliente HTTP."""
        await self._close_client()
