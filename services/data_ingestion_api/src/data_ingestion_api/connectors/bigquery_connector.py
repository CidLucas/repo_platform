# data_ingestion_api/connectors/bigquery_connector.py

from typing import Dict, Any, List, Generator
from google.cloud import bigquery
from google.oauth2 import service_account
import pandas as pd
import logging
import asyncio
# Importamos o conector abstrato para garantir a interface Vizu
from data_ingestion_api.connectors.abstract_connector import AbstractDataConnector

logger = logging.getLogger(__name__)

# Definição de exceções personalizadas para o conector
class ConnectionError(Exception):
    pass

class ExecutionError(Exception):
    pass


class BigQueryConnector(AbstractDataConnector):
    """
    Implementação concreta para o BigQuery, cumprindo o contrato do conector abstrato.
    """
    
    def __init__(self, credentials: Dict[str, Any]):
        """
        Inicializa o cliente BigQuery usando a Service Account Key injetada.
        """
        try:
            self._credentials_info = credentials
            
            self._gcp_credentials = service_account.Credentials.from_service_account_info(
                self._credentials_info
            )
            
            self._client = bigquery.Client(
                credentials=self._gcp_credentials,
                project=self._credentials_info.get('project_id')
            )
            logger.info("BigQuery client inicializado com sucesso.")

        except Exception as e:
            logger.error(f"Falha na inicialização do BigQuery Connector: {e}")
            raise ConnectionError(f"Falha ao conectar ao BigQuery: {e}")

    # --- MÉTODOS ABSTRATOS REQUERIDOS (Todos devem ser ASYNC) ---

    async def validate_connection(self) -> bool:
        """
        Implementação do método de validação de conexão (obrigatório).
        Reutiliza a lógica de teste de conexão existente.
        """
        try:
            # Query mínima para testar a validade da credencial e conexão
            self._client.query("SELECT 1").result()
            return True
        except Exception as e:
            logger.warning(f"Teste de conexão BigQuery falhou: {e}")
            return False

    # --- MÉTODO ABSTRATO (extract_data) ---
    async def extract_data(self, query: str, client_id: str = "") -> Generator[pd.DataFrame, None, None]:
        """
        [MODIFICADO] Implementação assíncrona que retorna um GERADOR (Iterator) de DataFrames
        para suportar grandes volumes de dados (Escalabilidade).
        """
        """
        [Melhorado] Implementação assíncrona que executa a lógica de I/O em uma 
        thread separada para não bloquear o event loop (Escalabilidade/Agnosticismo).
        """
        # Executa a função síncrona de I/O em um executor de thread
        sinc_generator = await asyncio.to_thread(
            self._execute_query_to_dataframe_iterator, 
            query
        )
        
        # Iteramos sobre o resultado síncrono, que já foi executado no background
        for chunk in sinc_generator:
            yield chunk

    async def fetch_schema(self) -> List[Dict[str, Any]]:
        """
        Busca e retorna o schema (tabelas, colunas, tipos) (obrigatório).
        (Mock simples para cumprir a interface).
        """
        return [{"table": "exemplo_tabela", "columns": ["id", "nome"]}]

    def get_connection_string(self) -> str:
        """
        Gera a string de conexão segura (sem expor credenciais em logs) (obrigatório).
        """
        project_id = self._credentials_info.get('project_id', 'unknown')
        return f"bigquery://gcp-project/{project_id}"

    # --- MÉTODOS DE TRABALHO INTERNO (SÍNCRONOS) ---
    
    def _execute_query_to_dataframe_iterator(self, sql_query: str) -> Generator[pd.DataFrame, None, None]:
        """
        [CORREÇÃO FINAL APLICADA] Executa a consulta no BigQuery e retorna um ITERADOR/GERADOR de DataFrames
        em chunks, usando o padrão de paginação do BigQuery e conversão manual para DataFrame.
        """
        try:
            logger.info(f"Iniciando extração em chunks no BigQuery: {sql_query[:50]}...")
    
            # 1. Executa a query
            query_job = self._client.query(sql_query)
            
            # 2. Obtém o iterador de resultados e espera a conclusão do job.
            # Retorna um RowIterator que gerencia a paginação.
            results = query_job.result()
            
            # 3. Extrai os nomes das colunas uma vez (para consistência do DataFrame)
            column_names = [field.name for field in results.schema]
            
            # 4. Itera sobre as PÁGINAS (chunks de resultados)
            for page in results.pages:
                # 'page' é um iterable de Row objetos. O objeto Page não tem to_dataframe().
                
                # Converte o chunk de linhas (page) para uma lista de tuplas de valores.
                data = [row.values() for row in page] 
                
                # 5. Cria o DataFrame usando os dados do chunk e os nomes das colunas
                # Este é o passo que estava faltando: a conversão explícita.
                dataframe_chunk = pd.DataFrame(data, columns=column_names)
                
                # 6. Entrega o chunk
                yield dataframe_chunk
            
            logger.info("Extração em chunks finalizada.")
            
        except Exception as e:
            # Garante que a exceção original seja logada e re-lançada
            logger.error(f"Erro ao executar extração em chunks: {e}")
            # Certifique-se de que a exceção 'ExecutionError' está definida (deve ser em abstract_connector.py ou similar)
            raise ExecutionError(f"Erro na extração BigQuery: {e}")