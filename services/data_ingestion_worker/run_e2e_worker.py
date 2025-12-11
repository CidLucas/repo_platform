"""
Script de Teste E2E e Integração para o data_ingestion_worker.

Este script unifica dois modos de teste controlados pela variável de ambiente E2E_MODE:

1. E2E_MODE="FULL" (Padrão):
   - Executa um teste End-to-End completo.
   - Simula um evento Pub/Sub e chama o entrypoint real do worker (`pubsub_ingestion_worker`).
   - O worker irá se conectar ao BigQuery real e escrever no banco de dados PostgreSQL
     real (definido em DATABASE_URL).
   - USO: poetry run python run_e2e_worker.py

2. E2E_MODE="STUB" (ou "INTEGRATION"):
   - Executa um teste de Integração focado na lógica do serviço.
   - Chama o `IngestionService` diretamente.
   - Conecta-se ao BigQuery real para extrair dados.
   - Substitui (injeta) o DBWriterService por um `DBWriterServiceStub`.
   - Valida a extração (BQ) e transformação (Pandas), mas NÃO escreve no banco.
   - USO: E2E_MODE=STUB poetry run python run_e2e_worker.py
"""

import asyncio
import base64
import json
import logging
import os

from data_ingestion_api.connectors.bigquery_connector import BigQueryConnector
from dotenv import load_dotenv
from google.cloud import bigquery

# --- Imports para o Modo FULL (Entrypoint Real) ---
from data_ingestion_worker.core.worker_function import pubsub_ingestion_worker

# --- Imports para o Modo STUB (Injeção de Dependência) ---
from data_ingestion_worker.services.ingestion_service import IngestionService
from data_ingestion_worker.services.stubs.db_writer_stub import DBWriterServiceStub

# Configura o logging para vermos os INFOs de ambos os modos
logging.basicConfig(level=logging.INFO)

# Carrega variáveis de ambiente (ex: GOOGLE_APPLICATION_CREDENTIALS, DATABASE_URL)
load_dotenv()


# --- Configuração Centralizada do Job de Teste ---
CLIENTE_CREDENTIAL_ID = "e2e-test-client"
CLIENTE_TARGET_TABLE = "pm_dados_faturamento_cliente_x" # (Será ignorado no futuro pela lógica de schema_mapping)
JOB_ID = "e2e-test-job-999"

# 1. Simula o Payload do IngestionJob (o contrato Vizu)
job_payload = {
    "client_id": CLIENTE_CREDENTIAL_ID,
    "target_resource": CLIENTE_TARGET_TABLE,
    "job_id": JOB_ID,
    "chunk_size": 1000  # O chunk_size do seu log original era 1000
}

# 2. Simula a Mensagem Pub/Sub (Formato base64)
pubsub_event = {
    "data": base64.b64encode(json.dumps(job_payload).encode("utf-8")).decode("utf-8"),
    "attributes": {},
    "messageId": f"pubsub-e2e-{JOB_ID}"
}


async def main_integration_test():
    """
    Executa o teste de INTEGRAÇÃO (Modo STUB).
    Chama o IngestionService diretamente, injetando o DBWriterServiceStub.
    Valida o fluxo BQ -> Transform -> Service, sem tocar no DB.
    """
    print(f"--- INICIANDO TESTE DE INTEGRAÇÃO (MODO STUB): {JOB_ID} ---")

   # 1a. Instancia o cliente BigQuery real
    # (Ele usará automaticamente o GOOGLE_APPLICATION_CREDENTIALS do .env)
    logging.info("Inicializando cliente Google BigQuery...")
    google_bq_client = bigquery.Client()
    logging.info("Cliente Google BigQuery inicializado.")

    # 1b. Inicializar conector real
    bq_connector = BigQueryConnector(client=google_bq_client)

    # 2. Injetar o STUB
    db_writer_stub = DBWriterServiceStub()

    # 3. Injetar a dependência no serviço
    #    (Princípio do Agnosticismo: o serviço aceita qualquer 'writer')
    ingestion_service = IngestionService(
        connector=bq_connector,
        writer=db_writer_stub
    )

    # 4. Executar o serviço diretamente
    await ingestion_service.run_job(
        job_id=job_payload["job_id"],
        client_id=job_payload["client_id"]
    )

    print(f"\n✅ SUCESSO (Integração): Job {JOB_ID} concluído com STUB.")


def main_e2e_full_test():
    """
    Executa o teste E2E COMPLETO (Modo FULL).
    Chama o worker Pub/Sub, que usará o DBWriterService real.
    Valida o fluxo completo: PubSub -> BQ -> Transform -> DB Real.
    """
    print(f"--- INICIANDO TESTE E2E COMPLETO (MODO FULL): {JOB_ID} ---")

    try:
        # Executa a função do Worker diretamente, simulando o ambiente Cloud Function
        # Esta função é síncrona, mas orquestra chamadas assíncronas internas.
        pubsub_ingestion_worker(pubsub_event, context=None)

        print("\n✅ SUCESSO (E2E Full): Verifique seu banco de dados PostgreSQL.")

    except Exception as e:
        print("\n❌ FALHA NO FLUXO E2E: O Worker lançou uma exceção.")
        print(f"Detalhes do Erro: {e}")
        # Re-lança a exceção para que o script falhe (importante para CI/CD)
        raise


if __name__ == "__main__":
    # Decide qual teste rodar com base na variável de ambiente
    # O Padrão é "FULL" para manter o comportamento original do seu script
    test_mode = os.getenv("E2E_MODE", "FULL").upper()

    if test_mode in ("STUB", "INTEGRATION"):
        # --- MODO INTEGRAÇÃO ---
        # Precisa do asyncio.run() pois chamamos o IngestionService (async) diretamente
        asyncio.run(main_integration_test())
    else:
        # --- MODO E2E COMPLETO ---
        # Não usa asyncio.run() aqui, pois a função `pubsub_ingestion_worker`
        # (simulando a Cloud Function) já gerencia seu próprio loop de eventos.
        main_e2e_full_test()
