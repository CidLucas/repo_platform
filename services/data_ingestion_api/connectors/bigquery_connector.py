# data_ingestion_api/connectors/bigquery_connector.py

import logging
from collections.abc import AsyncGenerator, Generator
from typing import Any

import pandas as pd

# Importamos o conector abstrato para garantir a interface Vizu
from data_ingestion_api.connectors.abstract_connector import AbstractDataConnector, ExecutionError
from google.api_core.exceptions import GoogleCloudError
from google.cloud import bigquery
from google.oauth2 import service_account

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

    def __init__(self, credentials: dict[str, Any]):
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
    async def extract_data(
        self,
        query: str,
        chunk_size: int = 10000, # <-- 1. Aceita o argumento 'chunk_size'
        client_id: str = ""      # <-- Mantém o argumento (embora não usado aqui)
    ) -> AsyncGenerator[pd.DataFrame, None]:
        """
        [VIZU-REFACTOR] Implementação assíncrona NATIVA.
        Executa a query e retorna um gerador assíncrono de DataFrames
        para suportar grandes volumes de dados (Escalabilidade).
        """
        log.info(f"BigQueryConnector (Async): Executando query, chunk_size={chunk_size}...")

        try:
            # 1. Executa a query
            # A biblioteca do BQ lida com a chamada de I/O
            query_job = self.client.query(query)

            # 2. [VIZU-REFACTOR] A 'chunk_size' é passada para 'page_size'
            # O 'to_dataframe_iterable' cria o iterador que precisamos.
            results_iterable = query_job.to_dataframe_iterable(page_size=chunk_size)

            # 3. Itera sobre os resultados em chunks (páginas)
            # O 'async for' é a forma correta de consumir este iterador
            # em um loop assíncrono, permitindo que o event loop
            # trabalhe enquanto espera o I/O da próxima página.
            async for df in results_iterable:
                if df.empty:
                    log.warning("BigQueryConnector (Async): Chunk vazio recebido, pulando.")
                    continue

                log.info(f"BigQueryConnector (Async): Yielding chunk de {len(df)} linhas.")
                yield df

        except GoogleCloudError as e:
            log.error(f"Erro na execução da query BigQuery: {e}")
            raise ExecutionError(f"Erro na extração BigQuery: {e}")
        except Exception as e:
            log.error(f"Erro inesperado no BigQueryConnector: {e}")
            # Encapsula o erro no nosso tipo padrão
            raise ExecutionError(f"Erro inesperado durante a extração: {e}")

    async def fetch_schema(self) -> list[dict[str, Any]]:
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
