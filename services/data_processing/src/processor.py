# services/data_processing/processor.py

import logging
from typing import Dict, Any
import pandas as pd

# Importar ferramentas do monorepo (usaremos mock por enquanto)
# No futuro, vizu_db_connector, vizu_secret_manager_client
from vizu_db_connector.models.credencial_servico_externo import CredencialServicoExterno
# Importamos o conector real do outro serviço
from data_ingestion_api.connectors.bigquery_connector import BigQueryConnector 

logger = logging.getLogger(__name__)

# MOCK TEMPORÁRIO PARA DESBLOQUEAR O WORKER
class VizuDBConnector:
    """Simulação para satisfazer a injeção de dependência e os testes do Worker."""

    # O Worker chama insert_dataframe no método _load_data
    async def insert_dataframe(self, df):
        pass

    # O Worker chamará essa função no futuro para buscar a chave do SM
    async def get_secret_manager_id_and_type(self, id_credencial: str):
        # Simula buscar a referência no DB
        return "vizu-prod-secret-id-gcp-mock-123", "BIGQUERY" 


# TODO: Classe deve ser injetada via DI para maior testabilidade
class DataProcessor:
    """
    Worker assíncrono responsável por buscar dados, transformá-los 
    e carregá-los no destino final (ex: base vetorial, Cloud SQL).
    """

    def __init__(self, db_connector: Any, secret_manager: Any):
        # DI: Injetamos as dependências de infraestrutura
        self.db_connector = db_connector
        self.secret_manager = secret_manager
        
    async def process_ingestion(self, cliente_vizu_id: str, id_credencial: str) -> bool:
        """
        Fluxo principal de Extração, Transformação e Carga (ETL/ELT).
        """
        logger.info(f"Iniciando processamento para Cliente: {cliente_vizu_id}, Credencial: {id_credencial}")
        
        # 1. Busca Segredo: O Worker precisa do JSON da Service Account
        try:
            # Assumimos que esta função existe no vizu_secret_manager_client
            # Ela busca o ID da credencial (referência) no DB
            # E usa o secret_manager_id para buscar o JSON real no GCP Secret Manager.
            creds_json = await self._fetch_real_credentials(id_credencial)
            
        except Exception as e:
            logger.error(f"Falha ao buscar credenciais para {id_credencial}: {e}")
            return False # Falha Crítica
            
        # 2. Extração: Conecta-se ao BigQuery e extrai os dados em Chunks
        try:
            connector = BigQueryConnector(credentials=creds_json)
            query = "SELECT order_id, customer_name, total_sales FROM my_dataset.sales_table"
            
            # CHAVE DA ESCALABILIDADE: Itera sobre o gerador de chunks
            chunk_count = 0
            
            # O extract_data agora retorna um gerador!
            async for raw_data_chunk in connector.extract_data(query): 
                
                # 3. Transformação em Chunks: Lógica de negócio Vizu
                transformed_chunk = self._transform_data(raw_data_chunk)
                
                # 4. Carga: Salva o resultado (Carga Incremental)
                await self._load_data(transformed_chunk)
                
                chunk_count += 1
                logger.info(f"Chunk {chunk_count} processado. {len(transformed_chunk)} linhas carregadas.")

            logger.info(f"Processamento concluído. Total de {chunk_count} chunks processados.")
            
        except Exception as e:
            logger.error(f"Falha na Extração/Conexão BigQuery: {e}")
            return False

        # 3. Transformação: Lógica de negócio Vizu
        transformed_df = self._transform_data(raw_data_df)
        
        # 4. Carga: Salva o resultado (ex: no banco vetorial Qdrant ou no Cloud SQL)
        await self._load_data(transformed_df)
        
        logger.info(f"Processamento concluído com sucesso para Cliente: {cliente_vizu_id}")
        return True

    # Métodos Auxiliares
    async def _fetch_real_credentials(self, id_credencial: str) -> Dict[str, Any]:
        """ Simula a busca do Secret Manager, retornando o JSON da Service Account. """
        # Lógica real: 
        # 1. self.db_connector.get_secret_manager_id(id_credencial)
        # 2. self.secret_manager.get_secret_value(secret_manager_id)
        
        # Mock do JSON (para teste)
        return {
            "type": "service_account",
            "project_id": "vizu-test-project",
            "private_key_id": "mock-key-id",
            "private_key": "-----BEGIN PRIVATE KEY-----MOCK_KEY-----END PRIVATE KEY-----\n",
            "client_email": "mock-connector@gcp.iam.gserviceaccount.com",
            # ... (outros campos) ...
        }

    def _transform_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """ Aplica regras de negócio (limpeza, normalização, etc.). """
        logger.info("Executando transformação de dados...")
        # Ex: Renomear colunas, calcular margem, etc.
        return df.rename(columns={'total_sales': 'valor_venda'})

    async def _load_data(self, df: pd.DataFrame):
        """ Salva o DataFrame final no destino Vizu (ex: Cloud SQL, Qdrant). """
        logger.info(f"Carregando {len(df)} linhas na base de dados Vizu.")
        # Lógica real: Insert no vizu_db_connector ou upsert no Qdrant
        await self.db_connector.insert_dataframe(df) # Simulação

# Exceção personalizada para o Worker
class ProcessingError(Exception):
    pass