from fastapi import APIRouter, Depends, HTTPException, status
from data_ingestion_api.services.pubsub_publisher import pubsub_publisher, PubSubPublisher
from data_ingestion_worker.schemas.ingestion_job import IngestionJob # Importando o contrato

router = APIRouter()

# Defina um esquema Pydantic para o POST body que é idêntico ao IngestionJob

@router.post("/ingestion/start", status_code=status.HTTP_202_ACCEPTED)
async def start_data_ingestion(
    job_payload: IngestionJob, # A API recebe o mesmo objeto que será enviado ao Worker
    publisher: PubSubPublisher = Depends(lambda: pubsub_publisher)
):
    """
    Inicia um trabalho de ingestão de dados publicando uma mensagem no Pub/Sub.
    A extração real é feita por um Worker serverless.
    """
    try:
        # Gerar um Job ID, se o payload não o tiver (crucial para Observabilidade)
        if not job_payload.job_id:
            job_payload.job_id = str(uuid.uuid4())
            
        # 1. Publica a mensagem no Pub/Sub
        message_id = publisher.publish_ingestion_job(job_payload)

        # 2. Retorna um status HTTP 202 (Accepted) para indicar que o job foi enfileirado
        return {
            "message": "Job de ingestão enfileirado com sucesso. O processamento será assíncrono.",
            "job_id": job_payload.job_id,
            "pubsub_message_id": message_id
        }

    except Exception as e:
        # Erro de entrega no Pub/Sub (raro, mas deve ser tratado)
        print(f"ERRO AO PUBLICAR NO PUBSUB: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Falha ao enfileirar o trabalho de ingestão: {e}"
        )