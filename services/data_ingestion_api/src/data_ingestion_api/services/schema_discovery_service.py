"""
Schema Discovery Service - Descobre o schema de fontes de dados externas.

Este serviço extrai a estrutura de colunas/campos de diferentes conectores
(BigQuery, Shopify, VTEX, etc.) para posterior mapeamento.
"""

import logging
from typing import Dict, Any, List, Optional, Type
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class DiscoveredSchema:
    """Schema descoberto de uma fonte de dados."""
    resource_type: str
    columns: List[str]
    sample_data: Optional[Dict[str, Any]] = None
    column_types: Dict[str, str] = field(default_factory=dict)  # {coluna: tipo}
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "resource_type": self.resource_type,
            "columns": self.columns,
            "column_count": len(self.columns),
            "sample_data": self.sample_data,
            "column_types": self.column_types,
            "metadata": self.metadata
        }


class SchemaDiscoveryService:
    """
    Serviço para descoberta de schemas de fontes de dados.
    
    Suporta:
    - Conectores de E-commerce (Shopify, VTEX, Loja Integrada)
    - BigQuery (tabelas e views)
    - Arquivos CSV/Excel
    """
    
    # Recursos padrão para cada tipo de conector
    DEFAULT_RESOURCES = {
        "ecommerce": ["products", "orders", "customers", "inventory"],
        "bigquery": [],  # Descoberto dinamicamente
        "csv": [],  # Baseado no arquivo
    }
    
    def __init__(self):
        pass
    
    async def discover_schema(
        self,
        connector: Any,
        resource_type: str,
        sample_size: int = 1
    ) -> DiscoveredSchema:
        """
        Descobre o schema de um recurso usando o conector.
        
        Args:
            connector: Instância do conector (Shopify, BigQuery, etc.)
            resource_type: Tipo do recurso (products, orders, etc.)
            sample_size: Número de registros de amostra a buscar
            
        Returns:
            DiscoveredSchema com colunas e dados de amostra
        """
        logger.info(f"Descobrindo schema para recurso: {resource_type}")
        
        # Determina o método de extração baseado no tipo de recurso
        sample_data = await self._extract_sample(connector, resource_type, sample_size)
        
        if not sample_data:
            logger.warning(f"Nenhum dado encontrado para {resource_type}")
            return DiscoveredSchema(
                resource_type=resource_type,
                columns=[],
                sample_data=None,
                metadata={"error": "No data found"}
            )
        
        # Extrai colunas do primeiro registro
        first_record = sample_data[0] if isinstance(sample_data, list) else sample_data
        columns = self._extract_columns(first_record)
        column_types = self._infer_column_types(first_record)
        
        logger.info(f"Schema descoberto: {len(columns)} colunas para {resource_type}")
        
        return DiscoveredSchema(
            resource_type=resource_type,
            columns=columns,
            sample_data=first_record,
            column_types=column_types,
            metadata={
                "connector_type": type(connector).__name__,
                "sample_size": sample_size,
                "total_columns": len(columns)
            }
        )
    
    async def _extract_sample(
        self,
        connector: Any,
        resource_type: str,
        sample_size: int
    ) -> List[Dict[str, Any]]:
        """
        Extrai dados de amostra usando o conector apropriado.
        
        Tenta usar métodos padrão dos conectores:
        - get_products(), get_orders(), get_customers(), get_inventory()
        - Para BigQuery: executa query LIMIT
        """
        try:
            # Métodos padrão de e-commerce
            method_map = {
                "products": "get_products",
                "orders": "get_orders", 
                "customers": "get_customers",
                "inventory": "get_inventory",
                "collections": "get_collections",
                "categories": "get_categories",
            }
            
            method_name = method_map.get(resource_type)
            
            if method_name and hasattr(connector, method_name):
                method = getattr(connector, method_name)
                return await method(limit=sample_size)
            
            # Fallback para métodos genéricos
            if hasattr(connector, 'extract_data'):
                # Conector genérico com extract_data
                async for chunk in connector.extract_data(
                    query=resource_type,
                    chunk_size=sample_size
                ):
                    # Converte DataFrame para lista de dicts
                    if hasattr(chunk, 'to_dict'):
                        return chunk.to_dict('records')[:sample_size]
                    return list(chunk)[:sample_size]
            
            if hasattr(connector, 'fetch_data'):
                # BigQuery connector
                query = f"SELECT * FROM `{resource_type}` LIMIT {sample_size}"
                result = await connector.fetch_data(query)
                if hasattr(result, 'to_dict'):
                    return result.to_dict('records')
                return result
            
            logger.warning(f"Método de extração não encontrado para {resource_type}")
            return []
            
        except Exception as e:
            logger.error(f"Erro ao extrair amostra de {resource_type}: {e}")
            return []
    
    def _extract_columns(self, record: Dict[str, Any], prefix: str = "") -> List[str]:
        """
        Extrai nomes de colunas de um registro.
        Suporta estruturas aninhadas com notação de ponto.
        
        Args:
            record: Registro de dados (dict)
            prefix: Prefixo para colunas aninhadas
            
        Returns:
            Lista de nomes de colunas
        """
        columns = []
        
        for key, value in record.items():
            full_key = f"{prefix}.{key}" if prefix else key
            
            if isinstance(value, dict):
                # Recursão para objetos aninhados
                nested_columns = self._extract_columns(value, full_key)
                columns.extend(nested_columns)
            elif isinstance(value, list) and value and isinstance(value[0], dict):
                # Array de objetos - extrai schema do primeiro item
                columns.append(f"{full_key}[]")  # Marca como array
                nested_columns = self._extract_columns(value[0], f"{full_key}[]")
                columns.extend(nested_columns)
            else:
                columns.append(full_key)
        
        return columns
    
    def _infer_column_types(self, record: Dict[str, Any], prefix: str = "") -> Dict[str, str]:
        """
        Infere tipos de dados das colunas baseado em valores de amostra.
        
        Args:
            record: Registro de dados
            prefix: Prefixo para colunas aninhadas
            
        Returns:
            Dict mapeando coluna -> tipo inferido
        """
        types = {}
        
        for key, value in record.items():
            full_key = f"{prefix}.{key}" if prefix else key
            
            if value is None:
                types[full_key] = "null"
            elif isinstance(value, bool):
                types[full_key] = "boolean"
            elif isinstance(value, int):
                types[full_key] = "integer"
            elif isinstance(value, float):
                types[full_key] = "number"
            elif isinstance(value, str):
                # Tenta detectar tipos especiais
                if self._looks_like_datetime(value):
                    types[full_key] = "datetime"
                elif self._looks_like_email(value):
                    types[full_key] = "email"
                elif self._looks_like_url(value):
                    types[full_key] = "url"
                else:
                    types[full_key] = "string"
            elif isinstance(value, list):
                types[full_key] = "array"
                if value and isinstance(value[0], dict):
                    nested_types = self._infer_column_types(value[0], f"{full_key}[]")
                    types.update(nested_types)
            elif isinstance(value, dict):
                types[full_key] = "object"
                nested_types = self._infer_column_types(value, full_key)
                types.update(nested_types)
            else:
                types[full_key] = "unknown"
        
        return types
    
    def _looks_like_datetime(self, value: str) -> bool:
        """Verifica se string parece ser datetime."""
        import re
        # Padrões comuns de datetime
        patterns = [
            r'^\d{4}-\d{2}-\d{2}',  # ISO date
            r'^\d{2}/\d{2}/\d{4}',  # DD/MM/YYYY
            r'^\d{4}-\d{2}-\d{2}T',  # ISO datetime
        ]
        return any(re.match(p, value) for p in patterns)
    
    def _looks_like_email(self, value: str) -> bool:
        """Verifica se string parece ser email."""
        import re
        return bool(re.match(r'^[\w\.-]+@[\w\.-]+\.\w+$', value))
    
    def _looks_like_url(self, value: str) -> bool:
        """Verifica se string parece ser URL."""
        return value.startswith(('http://', 'https://', 'www.'))
    
    async def discover_all_resources(
        self,
        connector: Any,
        connector_type: str = "ecommerce"
    ) -> Dict[str, DiscoveredSchema]:
        """
        Descobre schemas de todos os recursos padrão de um conector.
        
        Args:
            connector: Instância do conector
            connector_type: Tipo do conector (ecommerce, bigquery)
            
        Returns:
            Dict mapeando resource_type -> DiscoveredSchema
        """
        resources = self.DEFAULT_RESOURCES.get(connector_type, [])
        
        if connector_type == "ecommerce" and hasattr(connector, 'SUPPORTED_RESOURCES'):
            resources = connector.SUPPORTED_RESOURCES
        
        results = {}
        for resource in resources:
            try:
                schema = await self.discover_schema(connector, resource)
                results[resource] = schema
            except Exception as e:
                logger.error(f"Erro ao descobrir schema de {resource}: {e}")
                results[resource] = DiscoveredSchema(
                    resource_type=resource,
                    columns=[],
                    metadata={"error": str(e)}
                )
        
        return results
    
    def flatten_columns(self, columns: List[str]) -> List[str]:
        """
        Achata lista de colunas removendo notação de objetos aninhados.
        Útil para criar mapeamento mais simples.
        
        Args:
            columns: Lista de colunas (pode incluir notação de ponto)
            
        Returns:
            Lista de colunas achatadas (último nível apenas)
        """
        flattened = []
        for col in columns:
            # Remove marcadores de array e pega último nível
            clean = col.replace('[]', '')
            parts = clean.split('.')
            leaf = parts[-1]
            if leaf not in flattened:
                flattened.append(leaf)
        return flattened


# Instância global
schema_discovery = SchemaDiscoveryService()
