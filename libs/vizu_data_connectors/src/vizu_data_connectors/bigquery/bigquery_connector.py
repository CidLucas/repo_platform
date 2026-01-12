import asyncio
import logging
from collections.abc import AsyncGenerator, Generator
from typing import Any

import pandas as pd

# [VIZU-REFACTOR] CORRIGIDO: Importa a exceção correta
from google.api_core.exceptions import GoogleAPICallError
from google.cloud import bigquery

# Importamos o conector abstrato para garantir a interface Vizu
from vizu_data_connectors.base.abstract_connector import AbstractDataConnector, ExecutionError

# [VIZU-REFACTOR] Nome do logger definido no topo do arquivo
logger = logging.getLogger(__name__)


class BigQueryConnector(AbstractDataConnector):
    """
    Implementação concreta para o BigQuery, cumprindo o contrato do conector abstrato.
    """

    def __init__(self, client: bigquery.Client):
        self._client = client
        logger.info("BigQuery client inicializado com sucesso.")

    async def close(self):
        pass

    async def validate_connection(self) -> bool:
        try:
            self._client.query("SELECT 1").result()
            return True
        except Exception as e:
            logger.warning(f"Teste de conexão BigQuery falhou: {e}")
            return False

    # --- MÉTODO ABSTRATO (extract_data) ---
    async def extract_data(
        self,
        query: str,
        chunk_size: int = 10000, # <-- 1. Aceita o 'chunk_size'
        client_id: str = ""
    ) -> AsyncGenerator[pd.DataFrame, None]:
        """
        [VIZU-REFACTOR] Implementação assíncrona.
        Executa a função de extração SÍNCRONA (baseada em 'pages')
        em uma thread separada para não bloquear o event loop.
        """
        logger.info(f"BigQueryConnector (Async): Executando query, chunk_size={chunk_size}...")

        try:
            # 2. Executa a função síncrona de I/O em um executor de thread
            # Passamos o 'chunk_size' (embora o 'pages' o ignore)
            sinc_generator = await asyncio.to_thread(
                self._execute_query_to_dataframe_iterator,
                query,
                chunk_size # Passa o argumento adiante
            )

            # 3. Itera sobre o gerador síncrono e entrega (yield) os chunks
            # para o loop 'async for' do IngestionService.
            for chunk in sinc_generator:
                if chunk.empty:
                    logger.warning("BigQueryConnector (Async): Chunk vazio recebido, pulando.")
                    continue
                logger.info(f"BigQueryConnector (Async): Yielding chunk de {len(chunk)} linhas.")
                yield chunk

        except GoogleAPICallError as e:
            logger.error(f"Erro na execução da query BigQuery: {e}")
            raise ExecutionError(f"Erro na extração BigQuery: {e}")
        except Exception as e:
            logger.error(f"Erro inesperado no BigQueryConnector: {e}")
            raise ExecutionError(f"Erro inesperado durante a extração: {e}")

    async def fetch_schema(self) -> list[dict[str, Any]]:
        return [{"table": "exemplo_tabela", "columns": ["id", "nome"]}]

    def get_connection_string(self) -> str:
        project_id = self._client.project
        return f"bigquery://gcp-project/{project_id}"

    # --- MÉTODOS DE TRABALHO INTERNO (SÍNCRONOS) ---

    # [VIZU-REFACTOR] Esta é a sua lógica de paginação, agora chamada pela 'extract_data'
    def _execute_query_to_dataframe_iterator(
        self,
        sql_query: str,
        chunk_size: int # Aceita o argumento (mesmo que não o use)
    ) -> Generator[pd.DataFrame, None, None]:
        """
        Executa a consulta no BigQuery e retorna um ITERADOR/GERADOR de DataFrames
        em chunks, usando o padrão de paginação do BigQuery.
        """
        try:
            # (chunk_size é ignorado aqui, pois 'results.pages' gerencia o paging)
            logger.info(f"BigQueryConnector (Sync Thread): Iniciando extração (chunk_size={chunk_size}): {sql_query[:50]}...")

            query_job = self._client.query(sql_query)

            # .result() é SÍNCRONO (bloqueante) - por isso está em uma thread
            results = query_job.result()

            column_names = [field.name for field in results.schema]

            # Iterate through result pages and yield DataFrames
            for page in results.pages:
                # Extract data from page rows
                data = [list(row.values()) for row in page]

                if not data:
                    logger.warning("Empty page received from BigQuery, skipping.")
                    continue

                # Create DataFrame chunk
                dataframe_chunk = pd.DataFrame(data, columns=column_names)

                logger.info(f"BigQueryConnector (Sync): Yielding chunk de {len(dataframe_chunk)} linhas.")
                yield dataframe_chunk

        except GoogleAPICallError as e:
            logger.error(f"Google API error during BigQuery extraction: {e}")
            raise ExecutionError(f"BigQuery API error: {e}")
        except Exception as e:
            logger.error(f"Unexpected error in BigQuery extraction: {e}")
            raise ExecutionError(f"BigQuery extraction failed: {e}")
