from pydantic import BaseModel, Field


# Este é o contrato Vizu que a API de ingestão DEVE publicar no Pub/Sub.
class IngestionJob(BaseModel):
    """
    Define o trabalho de ingestão de dados, utilizando Pydantic para validação (Testabilidade).
    """

    # ID do cliente (para buscar a credencial, alinhado com o Agnóstico)
    client_id: str = Field(..., description="ID do Cliente Vizu que iniciou o job.")

    # [VIZU-REFACTOR] CORRIGIDO: O campo query agora é opcional.
    # Nossa lógica agnóstica (IngestionService) não depende mais dele.
    query: str | None = Field(
        default=None,
        description="[LEGADO] A query SQL a ser executada. (Será substituído pela lógica de mapeamento)"
    )

    target_resource: str = Field(..., description="O nome do recurso de destino (ex: tabela no Cloud SQL)")
    job_id: str = Field(..., description="ID único para este job.")
    chunk_size: int = Field(default=10000, description="Tamanho dos chunks para extração.")
