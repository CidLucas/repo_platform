import uuid
from typing import Any

from vizu_models.credencial_servico_externo import CredencialServicoExternoBase

from .cliente_vizu import ClienteVizuBase


class VizuClientContext(ClienteVizuBase):
    """
    Modelo Pydantic que agrega todas as informações de contexto necessárias
    para a operação do agente.

    PHASE 1: Dynamic Tool Allocation
    - enabled_tools: Lista dinâmica de ferramentas habilitadas (substitui 3 booleans)
    - tier: Tier do cliente determina acesso baseline
    """

    # Informações de Identificação do Cliente
    id: uuid.UUID
    api_key: str
    nome_empresa: str

    # PHASE 1: Dynamic Tool Allocation - New enabled_tools list
    enabled_tools: list[str] = []

    # Configurações de Negócio para o Agente
    prompt_base: str | None
    horario_funcionamento: dict[str, Any] | None

    # Configurações de Negócio atuais
    collection_rag: str | None

    # Lista de credenciais já decifradas
    # Usamos o modelo Pydantic 'CredencialServicoExternoBase' para a tipagem
    credenciais: list[CredencialServicoExternoBase] = []

    def get_enabled_tools_list(self) -> list[str]:
        """Return the enabled tools list (authoritative field).

        This model no longer relies on legacy boolean flags; callers
        should use `enabled_tools` directly or call this helper.
        """
        return list(self.enabled_tools or [])
