"""
Serviço de Ingestão para Conectores de E-commerce.

Este serviço é responsável por:
1. Extrair dados de plataformas de e-commerce (Shopify, VTEX, Loja Integrada)
2. Transformar os dados para o schema canônico
3. Carregar no banco de dados de destino
"""

import logging
import pandas as pd
from typing import Dict, Any, Optional

from data_ingestion_api.connectors import (
    ShopifyConnector,
    VTEXConnector,
    LojaIntegradaConnector,
    EcommerceBaseConnector,
)
from data_ingestion_worker.services.db_writer_service import DBWriterService
from data_ingestion_worker.core.schema_mapping import (
    get_platform_mapping,
    get_platform_resources,
    transform_ecommerce_data,
)

logger = logging.getLogger(__name__)


class EcommerceIngestionService:
    """
    Serviço agnóstico para ingestão de dados de e-commerce.
    
    Princípios:
    - Agnosticismo: funciona com qualquer conector de e-commerce
    - Injeção de dependência: recebe connector e writer externos
    - Transformação: aplica mapeamento de schema canônico
    """
    
    def __init__(
        self, 
        connector: EcommerceBaseConnector, 
        writer: DBWriterService,
        platform: str
    ):
        """
        Inicializa o serviço com dependências injetadas.
        
        Args:
            connector: Instância de um conector de e-commerce
            writer: Instância de um serviço de escrita
            platform: Nome da plataforma (SHOPIFY, VTEX, LOJA_INTEGRADA)
        """
        self.connector = connector
        self.writer = writer
        self.platform = platform.upper()
        logger.info(f"EcommerceIngestionService inicializado para {self.platform}")
    
    async def run_job(
        self, 
        job_id: str, 
        client_id: str,
        resources: Optional[list] = None
    ):
        """
        Executa o pipeline completo de ingestão para e-commerce.
        
        Args:
            job_id: ID único do job
            client_id: ID do cliente Vizu
            resources: Lista de recursos para extrair (ou None para todos)
        """
        logger.info(f"Iniciando job {job_id} para cliente {client_id} ({self.platform})")
        
        # Se não especificou recursos, pega todos disponíveis
        if resources is None:
            resources = get_platform_resources(self.platform)
        
        total_records = 0
        
        async with self.connector:
            for resource in resources:
                try:
                    records = await self._process_resource(job_id, resource)
                    total_records += records
                except Exception as e:
                    logger.error(f"Erro ao processar {resource}: {e}")
                    # Continua com os próximos recursos
                    continue
        
        logger.info(f"Job {job_id} concluído. Total: {total_records} registros processados.")
        return total_records
    
    async def _process_resource(self, job_id: str, resource: str) -> int:
        """
        Processa um recurso específico (products, orders, etc.).
        """
        logger.info(f"[{job_id}] Extraindo {resource} de {self.platform}...")
        
        # 1. EXTRACT - Busca dados da API de e-commerce
        raw_data = await self._extract_resource(resource)
        
        if not raw_data:
            logger.warning(f"[{job_id}] Nenhum dado encontrado para {resource}")
            return 0
        
        logger.info(f"[{job_id}] Extraídos {len(raw_data)} registros de {resource}")
        
        # 2. TRANSFORM - Aplica mapeamento de schema
        mapping = get_platform_mapping(self.platform, resource)
        transformed_data = transform_ecommerce_data(raw_data, self.platform, resource)
        
        # Converte para DataFrame para compatibilidade com o writer
        df = pd.DataFrame(transformed_data)
        logger.info(f"[{job_id}] Dados transformados. Colunas: {df.columns.tolist()}")
        
        # 3. LOAD - Escreve no banco de destino
        # O nome da tabela segue o padrão: {platform}_{resource}
        table_name = f"ecommerce_{self.platform.lower()}_{resource}"
        await self.writer.load(df, table_name=table_name)
        
        return len(raw_data)
    
    async def _extract_resource(self, resource: str) -> list:
        """
        Extrai dados de um recurso usando o método apropriado do conector.
        """
        # Mapeamento de recursos para métodos do conector
        method_map = {
            "products": self.connector.get_products,
            "orders": self.connector.get_orders,
            "customers": self.connector.get_customers,
            "inventory": self.connector.get_inventory,
        }
        
        method = method_map.get(resource)
        if not method:
            logger.warning(f"Recurso {resource} não suportado pelo conector")
            return []
        
        return await method()
    
    async def run_single_resource(
        self, 
        job_id: str, 
        client_id: str,
        resource: str,
        limit: Optional[int] = None
    ) -> int:
        """
        Executa ingestão para um único recurso com limite opcional.
        Útil para testes e previews.
        """
        logger.info(f"Iniciando extração única de {resource} para {client_id}")
        
        async with self.connector:
            raw_data = await self._extract_resource(resource)
            
            if limit and len(raw_data) > limit:
                raw_data = raw_data[:limit]
            
            if not raw_data:
                return 0
            
            # Transform
            transformed = transform_ecommerce_data(raw_data, self.platform, resource)
            df = pd.DataFrame(transformed)
            
            # Load
            table_name = f"ecommerce_{self.platform.lower()}_{resource}"
            await self.writer.load(df, table_name=table_name)
            
            return len(raw_data)
