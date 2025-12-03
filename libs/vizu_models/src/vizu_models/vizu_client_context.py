import uuid
from typing import Any, Dict, List
from vizu_models.credencial_servico_externo import CredencialServicoExternoBase
from .cliente_vizu import ClienteVizuBase


class VizuClientContext(ClienteVizuBase):
    """
    Modelo Pydantic que agrega todas as informações de contexto necessárias
    para a operação do agente.
    """

    # Informações de Identificação do Cliente
    id: uuid.UUID
    api_key: str
    nome_empresa: str

    # Configurações de Negócio para o Agente
    prompt_base: str | None
    horario_funcionamento: Dict[str, Any] | None
    ferramenta_rag_habilitada: bool
    ferramenta_sql_habilitada: bool
    collection_rag: str | None

    # Lista de credenciais já decifradas
    # Usamos o modelo Pydantic 'CredencialServicoExternoBase' para a tipagem
    credenciais: List[CredencialServicoExternoBase] = []
