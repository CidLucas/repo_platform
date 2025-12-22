import logging

# Reutilização Vizu: Importando o conector da lib compartilhada
from vizu_data_connectors.bigquery import BigQueryConnector

# Import do nosso módulo de mapeamento "simples e na mão"
from data_ingestion_worker.core import schema_mapping

# Import do nosso DB Writer (Modularização)
# [CORREÇÃO] Corrigido o typo 'DBWriterServic'
from data_ingestion_worker.services.db_writer_service import DBWriterService

# Configuração de logging
logger = logging.getLogger(__name__)


class IngestionService:
    """
    Serviço agnóstico responsável por orquestrar o pipeline E-T-L.
    
    Recebe dependências (connector, writer) e aplica as regras
    de transformação definidas externamente (schema_mapping).
    """

    def __init__(self, connector: BigQueryConnector, writer: DBWriterService):
        """
        Inicializa o serviço com dependências injetadas.
        
        Args:
            connector: Instância de um conector de extração (ex: BigQueryConnector).
            writer: Instância de um serviço de escrita (ex: DBWriterService ou DBWriterServiceStub).
        """
        self.connector = connector
        self.writer = writer
        logger.info("IngestionService inicializado com conectores injetados.")

    async def run_job(self, job_id: str, client_id: str):
        """
        Executa o pipeline completo (E-T-L) para um job.
        """
        logger.info(f"Iniciando execução do job_id: {job_id} para client_id: {client_id}")

        try:
            # === 1. BUSCAR MAPEAMENTO (DE FORMA AGNÓSTICA) ===
            logger.info(f"Carregando mapeamento de schema para client_id: {client_id}")

            # Pede as regras de mapeamento ao módulo de configuração
            mapping = schema_mapping.get_schema_mapping(client_id)

            # Pede as colunas de origem para construir a query
            source_columns = schema_mapping.get_source_columns(client_id)

            # [RECOMENDAÇÃO FUTURA]: A tabela também deve vir do schema_mapping
            table_name = "`analytics-big-query-242119.dataform.products_invoices`"

            # === 2. CONSTRUIR QUERY (DE FORMA AGNÓSTICA) ===
            query = (
                f"SELECT {', '.join(source_columns)} "
                f"FROM {table_name} "
                # Ordena pela primeira coluna (ex: data) para garantir consistência
                f"ORDER BY {source_columns[0]}"
            )
            logger.info(f"Query dinâmica construída: {query[:100]}...")

            # === 3. EXTRAIR (Extract) ===
            total_rows = 0
            # O conector (real) é chamado
            async for chunk_df in self.connector.extract_data(query):
                total_rows += len(chunk_df)
                logger.info(f"Processando chunk de {len(chunk_df)} linhas...")

                # 'chunk_df' tem colunas de origem: ['createdat_product', 'totalprice_product', ...]

                # === 4. TRANSFORMAR (Transform) ===
                # Aplicamos o mapeamento "simples" que buscamos no passo 1
                transformed_df = chunk_df.rename(columns=mapping)

                # 'transformed_df' tem colunas de destino: ['invoice_date', 'invoice_amount', ...]

                logger.info(f"Chunk transformado. Colunas: {transformed_df.columns.tolist()}")

                # === 5. CARREGAR (Load) ===
                # O writer (Stub ou Real, dependendo do E2E_MODE) é chamado
                await self.writer.load(transformed_df)

            logger.info(f"Sucesso no Job: {job_id}. Total de {total_rows} linhas processadas.")

        except Exception as e:
            logger.error(f"Erro fatal no Job {job_id}: {e}")
            # Idealmente, atualizar o status do Job para 'FAILED' no DB de controle
            raise
