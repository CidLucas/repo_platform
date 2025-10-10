# data_ingestion_api/connectors/bigquery_connector.py

from typing import Dict, Any, List
from google.cloud import bigquery
from google.oauth2 import service_account
import pandas as pd 
import logging

# Importamos o conector abstrato para garantir a interface Vizu
from connectors.abstract_connector import AbstractDataConnector

logger = logging.getLogger(__name__)

class BigQueryConnector(AbstractDataConnector):
    """
    Implementação concreta para o BigQuery.
    Utiliza as credenciais de Service Account Keys (JSON).
    """
    
    def __init__(self, credentials: Dict[str, Any]):
        """
        Inicializa o conector com as credenciais (obtidas do Secret Manager).
        """
        try:
            # Assumimos que 'credentials' é o JSON da Service Account Key (dict)
            self._credentials_info = credentials
            
            # Cria credenciais baseadas na service account info
            self._gcp_credentials = service_account.Credentials.from_service_account_info(
                self._credentials_info
            )
            
            # Inicializa o cliente BigQuery
            self._client = bigquery.Client(
                credentials=self._gcp_credentials,
                project=self._credentials_info.get('project_id')
            )
            logger.info("BigQuery client inicializado com sucesso.")

        except Exception as e:
            logger.error(f"Falha na inicialização do BigQuery Connector: {e}")
            raise ConnectionError(f"Falha ao conectar ao BigQuery: {e}")

    def test_connection(self) -> bool:
        """
        Método de teste de conexão. Executa uma query simples e leve.
        """
        try:
            # Query mínima para testar a validade da credencial e conexão
            self._client.query("SELECT 1").result()
            return True
        except Exception as e:
            logger.warning(f"Teste de conexão BigQuery falhou: {e}")
            return False

    def execute_query_to_pandas(self, sql_query: str) -> pd.DataFrame:
        """
        Executa uma consulta SQL no BigQuery e retorna o resultado como um DataFrame.
        """
        try:
            logger.info(f"Executando query no BigQuery: {sql_query[:50]}...")

            # Configura a query para retornar o resultado de forma eficiente
            query_job = self._client.query(sql_query)

            # Baixa o resultado para um DataFrame Pandas
            dataframe = query_job.to_dataframe()

            logger.info(f"Query BigQuery executada. {len(dataframe)} linhas retornadas.")
            return dataframe

        except Exception as e:
            logger.error(f"Erro ao executar query no BigQuery: {e}")
            raise ExecutionError(f"Erro na query BigQuery: {e}")

# Definição de exceções personalizadas para o conector (Modularização e Observabilidade)
class ConnectionError(Exception):
    pass

class ExecutionError(Exception):
    pass