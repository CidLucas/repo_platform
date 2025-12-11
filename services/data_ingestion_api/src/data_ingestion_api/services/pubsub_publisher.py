from data_ingestion_worker.schemas.ingestion_job import IngestionJob  # Reutiliza o schema do Worker
from google.cloud import pubsub_v1

# Define o tópico do Pub/Sub que o Worker irá consumir (Padrão Vizu)
INGESTION_TOPIC = "vizu-data-ingestion-jobs"
# Você pode obter o ID do projeto de uma variável de ambiente, se necessário.

class PubSubPublisher:
    """
    Serviço agnóstico responsável por publicar mensagens no Google Pub/Sub.
    Garante que a API não contenha código hardcodeado do Pub/Sub.
    """
    def __init__(self):
        # A Vizu usa o padrão de autenticação de ambiente (ADC)
        self.publisher = pubsub_v1.PublisherClient()
        self.topic_path = self.publisher.topic_path(
            # O ID do projeto deve vir de uma variável de ambiente (Agnosticismo)
            "seu-projeto-gcp-vizu",
            INGESTION_TOPIC
        )

    def publish_ingestion_job(self, job_data: IngestionJob) -> str:
        """
        Serializa o Job de Ingestão e o publica no Pub/Sub.
        """
        # 1. Serializa o objeto Pydantic para JSON (formato do Pub/Sub)
        data_json = job_data.model_dump_json() # Usando model_dump_json do Pydantic v2
        data_bytes = data_json.encode("utf-8")

        # 2. Publica a mensagem
        future = self.publisher.publish(self.topic_path, data_bytes)

        # Bloqueia a API até que a mensagem seja confirmada (Garantia de entrega)
        return future.result()

# Instância Singleton para Injeção de Dependência
pubsub_publisher = PubSubPublisher()
