# src/data_ingestion_worker/core/worker_function.py

import base64
import json
import logging
import asyncio
import os
from google.cloud import bigquery
from dotenv import load_dotenv

# Imports das nossas dependências REAIS
from data_ingestion_api.connectors.bigquery_connector import BigQueryConnector
from data_ingestion_worker.services.db_writer_service import DBWriterService
from data_ingestion_worker.services.ingestion_service import IngestionService
# (Assumindo que você tenha um get_settings() para ler o .env, 
# mas os.getenv() é mais direto para o worker)

# Configuração de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- FORÇA A LEITURA DO .ENV CORRETO ---
logger.info("Forçando a leitura do .env com override=True dentro de worker_function.py")
load_dotenv(override=True)
# Adiciona um print de diagnóstico para ter certeza
print(f"DEBUG: DATABASE_URL lida em worker_function: {os.getenv('DATABASE_URL')}")
# ------------------------------------

# --- Singleton Pattern para Serverless (BOA PRÁTICA VIZU) ---
# Usamos uma variável global para "cachear" o serviço inicializado.
# Isso reutiliza o pool de conexões do DB entre as chamadas da Cloud Function.
_ingestion_service: IngestionService | None = None


def _get_ingestion_service() -> IngestionService | None:
    """
    Função de inicialização (Singleton) que atua como "Composition Root".
    
    Constrói e injeta as dependências REAIS (DB e BQ).
    """
    global _ingestion_service
    
    # Se já foi inicializado em uma chamada anterior, retorne o cache
    if _ingestion_service:
        return _ingestion_service

    try:
        logger.info("Inicializando IngestionService (Singleton)...")
        
# --- 1. Construir Dependência: DBWriterService (Real) ---
        # Lemos a URL do banco do ambiente
        db_connection_url = os.getenv("DATABASE_URL") # <--- CORRIGIDO
        
        # Verificamos a variável com o nome correto
        if not db_connection_url: # <--- CORRIGIDO
            logger.critical("Variável de ambiente DATABASE_URL não está configurada.")
            raise ValueError("DATABASE_URL não está configurada.")

        # Injetamos a variável com o nome correto
        db_writer = DBWriterService(db_url=db_connection_url) # <--- CORRETO
        
        # --- 2. Construir Dependência: BigQueryConnector (Real) ---
        logger.info("Inicializando cliente Google BigQuery...")
        # (Ele usará automaticamente o GOOGLE_APPLICATION_CREDENTIALS do .env)
        google_bq_client = bigquery.Client()
        bq_connector = BigQueryConnector(client=google_bq_client)
        
        # --- 3. Injetar Dependências (O CORAÇÃO DA MUDANÇA) ---
        _ingestion_service = IngestionService(
            connector=bq_connector, 
            writer=db_writer
        )
        
        logger.info("IngestionService (Singleton) inicializado com sucesso.")
        return _ingestion_service
        
    except Exception as e:
        # É ESTA EXCEÇÃO que gera o log "ERRO CRÍTICO"
        logger.critical(f"ERRO CRÍTICO DE INICIALIZAÇÃO DO WORKER: {e}")
        # Retorna None, e a função principal irá falhar (como vimos no log)
        return None

# --- FIM DA INICIALIZAÇÃO ---


# (IMPORTANTE)
# Inicializa o serviço globalmente QUANDO O ARQUIVO É IMPORTADO.
# A Cloud Function reutilizará a variável _ingestion_service.
_get_ingestion_service()


def pubsub_ingestion_worker(event, context):
    """
    Entrypoint da Cloud Function (ou worker Pub/Sub).
    """
    job_id = "unknown-job" # Default
    try:
        # 1. Valida a inicialização (o check que vimos falhar)
        if _ingestion_service is None:
            logger.error("Serviço de Ingestão não inicializado. Verifique os logs de inicialização.")
            raise RuntimeError("O Serviço de Ingestão não foi inicializado corretamente.")

        # 2. Parse do Payload (igual ao run_e2e_worker)
        payload_data = base64.b64decode(event['data']).decode('utf-8')
        job_payload = json.loads(payload_data)
        
        job_id = job_payload.get("job_id", "unknown-job")
        client_id = job_payload.get("client_id")

        if not client_id:
            logger.error(f"Payload do Job {job_id} inválido: 'client_id' ausente.")
            return # Acknowledge a mensagem (não re-tenta)

        logger.info(f"Worker Pub/Sub recebendo job_id: {job_id} para client_id: {client_id}")

        # 3. Executa o serviço (de forma síncrona via asyncio.run)
        # O IngestionService.run_job é 'async'
        asyncio.run(
            _ingestion_service.run_job(job_id=job_id, client_id=client_id)
        )

        logger.info(f"Worker Pub/Sub concluiu com sucesso o job_id: {job_id}")

    except Exception as e:
        logger.error(f"Erro no processamento do worker Pub/Sub para job {job_id}: {e}")
        # Re-lança a exceção para que o Pub/Sub possa tentar um 'retry'
        raise