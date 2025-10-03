# src/atendente_api/core/schemas.py

import uuid
from datetime import datetime
from typing import Any, Dict, List

# Importa o BaseSchema da nossa biblioteca de modelos compartilhados
from vizu_shared_models.core import BaseSchema
# --- CORREÇÃO APLICADA AQUI ---
# Importa o modelo Pydantic para as credenciais
from vizu_shared_models.credencial_servico_externo import CredencialServicoExternoBase


class VizuClientContext(BaseSchema):
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

    # Lista de credenciais já decifradas
    # Usamos o modelo Pydantic 'CredencialServicoExternoBase' para a tipagem
    credenciais: List[CredencialServicoExternoBase] = []